# PredX 架构与实现说明

面向要**接手或审计**这套代码的工程师。重点回答四件事：撮合怎么算、钱怎么记、账怎么对、坏账怎么防。

---

## 1. 总体结构

```
浏览器（零构建 SPA：index.html + app.js + styles.css）
        │  fetch JSON  (同源，无 CORS，无第三方 CDN)
        ▼
app/http.py  Router ── 鉴权中间件（JWT / API Key）── 限流 ── 统一错误
        ▼
app/api/*   瘦控制器：解析参数、校验权限、转调 service
        ▼
app/services/*   业务核心：lmsr（定价）· engine（撮合/结算）· markets（查询聚合）· audit（审计）
        ▼
app/db.py   连接池（每请求一个连接）+ transaction()（BEGIN IMMEDIATE）+ 迁移
        ▼
SQLite (WAL)  data/predx.db
```

设计原则：

- **控制器不写 SQL，服务层不写 HTTP。** 所有对外行为都能在服务层被直接调用与测试（`tests/` 就是这么做的，不启 HTTP）。
- **金额只用整数「分」。** 没有浮点参与记账，杜绝 0.1+0.2 类误差。
- **零第三方依赖。** 目标客户是内网/信创环境，`pip install` 常常是最大阻力；同时代码总量可控（约 6k 行，全部可读）。

---

## 2. 数据模型（12 张表）

| 表 | 作用 | 关键约束 |
|---|---|---|
| `users` | 账户 | `role ∈ trader/creator/admin`、`status ∈ active/frozen`、`balance_cents`、`equity_seed`（初始体验金，用于算 ROI） |
| `markets` | 事件 | `status ∈ open/closed/resolved`、`liquidity_b`、`fee_bps`、`resolution_outcome_id` |
| `outcomes` | 结果（每市场 2–8 个） | `lmsr_q`（LMSR 状态向量）、`last_price_cents`、`is_winner`、`UNIQUE(market_id, seq)` |
| `orders` | 委托 | `side/order_type/price_cents/qty/filled_qty/status`、`reserved_cents`（买单冻结现金） |
| `trades` | 成交（不可变明细） | 一条成交 = 一次价格发现事件；`source ∈ book/amm`、`fee_cents` |
| `positions` | 持仓 | `shares`、`locked_shares`（卖单冻结）、`cost_cents`、`realized_cents`、`UNIQUE(user_id, outcome_id)` |
| `ledger` | 资金流水（只追加） | `kind ∈ signup/deposit/trade_buy/trade_sell/settlement/fee/refund`、`balance_after_cents` |
| `price_points` | 价格时间序列 | 每次撮合后快照，驱动前端曲线 |
| `comments` / `watchlist` | 社区 | 评论、关注列表 |
| `api_keys` | 程序化交易凭证 | 只存 `key_hash`（SHA-256），可吊销 |
| `audit_logs` | 审计 | 谁在什么时候干了什么（下单、撤单、停盘、结算、冻结） |
| `settings` | 运行期开关 | key-value |

**为什么同时要 `trades` 和 `orders`**：`orders` 是意图（可撤、可部分成交），`trades` 是事实（不可变）。
两者用 `buy_order_id / sell_order_id` 关联，任何一笔成交都能追溯到双方委托。

---

## 3. 定价：LMSR 做市商

### 3.1 公式

成本函数（`n` 个结果、状态向量 `q`、深度参数 `b`）：

```
C(q) = b · ln( Σᵢ exp(qᵢ / b) )
```

边际价格 = 第 i 个结果的即时概率：

```
pᵢ = ∂C/∂qᵢ = exp(qᵢ/b) / Σⱼ exp(qⱼ/b)      ← softmax，天然 Σpᵢ = 1
```

买入 `Δ` 份结果 i 的成本 = `C(q + Δ·eᵢ) − C(q)`；卖出 `Δ` 份的成本为负值，绝对值即到手现金。

### 3.2 三个工程细节

1. **数值稳定**：实现里先减去 `max(qᵢ/b)` 再取指数，避免大 b 下的上溢。
2. **取整方向不对称**（`lmsr.prices_cents`、`engine.place_order`）：
   - 买入成本 **向上取整**（`ceil`）
   - 卖出所得 **向下取整**（`floor`）
   - 整数化后的价格向量再按余数补偿，强制 `Σ price_cents = 100`，并且每个价格夹在 `[1, 99]`。
   这样保证「同一时刻买进再卖出」不可能凭空盈利 —— 这是模拟盘里最容易出「无限刷钱漏洞」的地方，必须堵死。
3. **b 的作用**：`b` 越大，同样成交量引起的价格变化越小（深度越深）。默认 `b = 1200`，
   单笔 60 份大约推动价格 1–2 分；管理端可为每个市场上架时单独指定。

### 3.3 为什么用 LMSR 而不是纯订单簿

新市场上架即要能交易。纯订单簿需要先有做市商报双边价，否则冷启动阶段「有价无市」。
LMSR 用公式提供了**无限深度、永不消失、恒等式自洽**的报价，再由用户的限价单提供价格竞争。
代价是 `b` 参数决定的最大做市亏损有限且可预测（`lmsr.max_loss`，盘口接口里以 `amm_max_loss_cents` 暴露）。

---

## 4. 撮合引擎（`app/services/engine.py`）

### 4.1 一笔市价买单的生命周期

```
place_order(user, market, outcome, side='buy', order_type='market', budget_cents=20000)
  └─ transaction():                      ← BEGIN IMMEDIATE，全流程单事务
       1. 校验市场 open、结果存在、余额足够
       2. 价格边界：市价单取 mid ± max_slippage_bps（默认 ±5%，且至少 ±2 分）
       3. 归一化数量：买单按预算反解 qty（lmsr.max_buy_qty），并受 limit 价格约束
       4. 撮合三段：
          a) 对手限价簿：price 优 → id 时间优，逐档吃
          b) LMSR 吃单：按成本函数增量计算，费率 taker 20 bps
          c) 剩余挂单：写入 orders(status='open')，买单冻结现金、卖单冻结 locked_shares
       5. 记账：users.balance_cents、positions（shares/cost_cents/realized）、ledger、trades、price_points
       6. 刷新 outcomes.last_price_cents / prev_price_cents
  └─ COMMIT（任何一步异常 → ROLLBACK，不会出现「扣了钱没拿到份额」）
```

返回结构（前端据此弹 toast 与刷新）：

```json
{"order_id": 12, "requested_qty": 129, "filled_qty": 129, "resting_qty": 0,
 "avg_price_cents": 10.47, "notional_cents": 1350, "fills": [...], "price_after_cents": 11}
```

### 4.2 三条不变量（测试里逐条断言）

| 不变量 | 含义 | 校验位置 |
|---|---|---|
| `Σ price_cents = 100` | 所有结果的概率加起来必须是 100% | `tests/test_lmsr.py`、种子数据自检 |
| `买入 − 卖出 = shares + locked_shares` | 每份合约都有来源，不能凭空出现 | `tests/test_trading.py::test_positions_match_trades`（只看未结算市场） |
| `balances ≥ 0` 且流水末值 = 当前余额 | 资金守恒、流水可对账 | `manage.py verify` |

> `locked_shares` 是 `shares` 的**子集**（挂单冻结，成交时二者同时扣减），
> 所以「买入 − 卖出 = shares」成立，而 v1.0 的测试写成 `shares + locked_shares` 是错的 ——
> 当时种子数据里恰好没有未成交的卖单，才让这个错误测试「通过」。
> 现在由 `manage.py verify` + `tests/test_trading.py` 双重覆盖。

> 已结算市场不参与第二条：`resolve_market` 会把赢家份额兑付后清零（`shares=0`），
> 此时「持仓 = 买卖差额」自然不再成立，这是正确行为而不是 bug。

### 4.3 盘口：真实挂单 + 合成深度

`engine.book_view(market_id, outcome_id)` 把两类深度拼在一起：

- **用户挂单**：直接从 `orders` 聚合，按价格档位 `GROUP BY price_cents`
- **做市商深度**：第 k 档 = 增量成本 `[C(q + k·s) − C(q + (k−1)·s)] / s`，`s = MAKER_SIZE`

> 这里有个很容易写错的地方：`C(q + k·s) − C(q)` 是**前 k 档的累计成本**，
> 必须先换算成「每份均价」（除以 s）才是价格，不能再加上中间价。
> 早期版本就因为多加了 `mid` 导致买一卖一虚高到 23¢/2.6¢（真实应为 11.8¢/10.8¢），
> 现在由 `tests/test_api.py::test_book_is_tight_around_mid` 守住。

### 4.4 结算

```
resolve_market(market_id, winner_outcome_id)
  ├─ 撤掉该市场全部 open 订单（解冻现金与份额）
  ├─ 赢家持仓：每份兑付 100 分 → users.balance_cents，写 ledger(kind='settlement')
  ├─ 全部持仓清零（shares=0, locked_shares=0），realized_cents 保留历史盈亏
  ├─ 价格收敛为赢家 100¢ / 其余 0¢，写入最终价格点
  └─ markets.status='resolved' + resolution_outcome_id + 审计日志
```

结算不可撤销（管理端有二次确认），并且必须是事务性的：绝不能出现「赢了钱没到账」或「兑付了两次」。

---

## 5. 并发与一致性

- SQLite 打开 `WAL` + `busy_timeout=8000`，**读不阻塞写**。
- 所有写路径走 `transaction()`：`BEGIN IMMEDIATE` 立即取写锁，避免「先读后写」的升级死锁。
- `ThreadingHTTPServer` 多线程 + 每请求独立连接（`check_same_thread=False` 只是为了复用，连接不跨线程共享）。
- 撮合是**串行**的（写锁保证），因此不需要应用层锁，也天然不会双花。
- 代价：写吞吐受限于单写者（实测演示数据 175 笔成交灌入约 1 秒量级）。真要横向扩展 →
  把撮合抽成单线程内存匹配器（价格状态在内存，成交异步落库），SQLite 换 PostgreSQL。

---

## 6. 安全

| 面向 | 措施 |
|---|---|
| 口令 | PBKDF2-HMAC-SHA256，12 万轮，每用户独立 salt；`security.hash_password / verify_password` |
| 会话 | 自签 JWT（HS256），12 小时过期；密钥由 `PX_SECRET_KEY` 注入 |
| 程序化交易 | API Key 只存 SHA-256 摘要，可吊销，带 `last_used_at` |
| 越权 | 路由级 `auth=True` + 角色校验；资源级再校验（订单只能撤自己的、管理员才能结算） |
| 注入 | 全部 SQL 走参数化占位符；`manage.py sql` 只用于运维自查 |
| XSS | 前端所有动态文本经 `esc()` 转义；不拼接未转义的 HTML 属性 |
| 限流 | 每 IP 每分钟：`/api/auth/*` 20 次、其他 300 次 |
| 审计 | 下单/撤单/停盘/结算/冻结/登录失败全部落 `audit_logs` |
| 部署 | 静态资源做目录穿越检查；响应带 `X-Content-Type-Options: nosniff` |

**上线前必须做**：更换 `PX_SECRET_KEY`、关闭 `PX_ALLOW_REGISTRATION`、放在 TLS 反向代理之后、
把 `data/` 纳入备份（`make backup`）。

---

## 7. 前端（v1.1 重做）

### 7.1 结构

`app/static/` 三个文件，无构建、无外部资源：

| 文件 | 行数 | 职责 |
|---|---|---|
| `index.html` | ~110 | 顶栏骨架（品牌/导航/搜索/账户位）、移动端底栏、`#app` 挂载点、toast/弹层容器 |
| `styles.css` | ~560 | 设计令牌（颜色/圆角/阴影）+ 组件（卡片/面板/表格/阶梯盘口/柱状图/弹层）+ 4 档响应式 |
| `app.js` | ~1.9k | 图标库、API 封装、图表、6 个视图、全局事件委托、hash 路由 |

### 7.2 三个值得说的实现

**① 图标与图表全部是运行时生成的 SVG。**
没有 CDN、没有字体文件、没有图片资源。分类图标按 8 个分类着色（`CAT_META`），
行情图与迷你走势用同一套 `smoothPath()`（Catmull-Rom → 三次贝塞尔）绘制，
所以内网/离线可跑，预览 iframe 里也不会白屏。**刻意不使用 emoji 作为功能图标**——
在缺少彩色 emoji 字体的容器里会退化成方框（v1.0 正是踩了这个坑）。

**② 行情图的十字光标是纯手写命中测试。**
`priceChart()` 返回 `{ html, mount }`，`mount` 在 SVG 上监听 `mousemove`，
把鼠标的 clientX 换算成 viewBox 坐标后线性扫描最近数据点，移动虚线 + 圆点 + 读数卡片。
数据侧由 `/history?range=` 做时间桶重采样（`_resample`），避免「成交疏密不均 → 锯齿」。

**③ 单一事件委托 + 局部重渲染。**
所有交互都是 `data-act` 属性 + 一次 `document` 级 click 委托；
只有交易面板在输入时需要局部刷新（防抖 250ms 请求 `/quote` 后只改 5 个数字节点），
其余视图整块重渲染。好处是状态不会被"半更新"搞乱，代价是重渲染时要重新挂载图表（已封装在 `renderMarket` 里）。

### 7.3 报价一致性

交易面板的报价与真实下单**使用同一组参数**（含 `max_slippage_bps=500` 的价格保护），
因此「预估成交份额/均价」与实际成交一致。当预算大于当前深度能吃的量时，
面板会提示「当前深度下最多成交 N 份」，而不是假装能全部成交。

## 8. 测试策略

不启 HTTP、不 mock 数据库：`tests/conftest.py` 用临时 SQLite 文件 + 直接调用 `app.dispatch(req)`，
所以每个用例都是「真实路由 → 真实服务 → 真实 SQL」的端到端。

- **定价层**：单调性、概率和恒等、买卖对称、预算反解
- **接口层**：鉴权失败、筛选组合、盘口紧致性（买一 ≤ 中间价 ≤ 卖一）、分页上限
- **交易层**：余额不足、份额不足、部分成交、挂单冻结、撤单退款、成本与盈亏、结算兑付
- **管理端**：权限隔离（creator 不能结算）、状态机（open→closed→resolved）、审计与评论

```bash
make test     # 52 passed in ~2s
```

---

## 9. 如果要继续演进

| 方向 | 改动点 |
|---|---|
| 真实订单簿优先 | `engine.place_order` 已分三段，把第二段（LMSR）改成可配置关闭即可 |
| 定时行情采样 | 在 `main` 里加一个后台线程，定期 `refresh_prices(write_points=True)` |
| 多结果套利限制 | 增加「互补结果组合」校验（购买整组结果的成本应 ≥ 100 分） |
| 实时推送 | `http.server` 换成 SSE 输出（标准库足够），前端 `EventSource` 订阅盘口 |
| 界面深度 | 已有 `docs/UI-GUIDE.md` 作为设计基线；下一步可做 K 线蜡烛图、深浅色主题切换、自定义关注列表页 |
| 权限细分 | 把 `ADMIN_ROLES` 换成权限位表，配合 `audit_logs` 做合规报表 |
