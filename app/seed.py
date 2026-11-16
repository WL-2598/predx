"""首次启动初始化：建表 → 建用户 → 上架市场 → 模拟交易历史。

模拟交易是**真的走撮合引擎**（不是往表里塞假数据），所以：
  · 每个市场的价格、成交量、持仓、盈亏都是引擎算出来的
  · 排行榜、K 线、成交明细互相自洽
唯一的"假"是时间戳：为了让 K 线有 7 天历史，事后把成交时间重新分配。
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from .config import config
from .db import get_conn, insert, many, now, one, transaction
from .security import hash_password
from .services import engine, markets as svc

DEMO_USERS = [
    ("admin@predx.io", "admin1234", "运营管理员", "admin", 50_000_00),
    ("demo@predx.io", "demo1234", "演示交易员", "trader", 10_000_00),
    ("creator@predx.io", "creator1234", "市场创建者", "creator", 5_000_00),
]

BOTS = [
    ("bot_zhang@predx.io", "链上老张"),
    ("bot_may@predx.io", "宏观阿May"),
    ("bot_zhou@predx.io", "摸鱼周"),
    ("bot_lee@predx.io", "李工看产线"),
    ("bot_yuki@predx.io", "Yuki.eth"),
    ("bot_chen@predx.io", "陈半仙"),
]

# 问题、分类、结果、初始概率、emoji、结算规则
MARKETS = [
    dict(question="2026 年底前，美联储会再降息至少 50 个基点吗？",
         category="宏观", emoji="🏦", outcomes=["会", "不会"], probs=[0.62, 0.38], featured=True,
         description="以 FOMC 会后声明与联邦基金目标利率区间为准。累计降幅达到 50bp 即判「会」。",
         rules="以 2026-12-31 前最后一次 FOMC 决议为准。", days=26, b=1500),
    dict(question="比特币会在 2026 年内突破 15 万美元吗？",
         category="加密", emoji="₿", outcomes=["会", "不会"], probs=[0.41, 0.59], featured=True,
         description="以 Coinbase 现货 BTC-USD 收盘价为准，任意一天收盘 ≥ $150,000 即判「会」。",
         rules="UTC 日收盘价，取 2026-01-01 至 2026-12-31。", days=46, b=2000),
    dict(question="英伟达 2026 财年全年营收会超过 2000 亿美元吗？",
         category="科技", emoji="🖥️", outcomes=["会", "不会"], probs=[0.55, 0.45],
         description="以 NVIDIA 官方财年财报（10-K）公布数字为准。",
         rules="以公司正式财报为准，不含市场一致预期。", days=88, b=1200),
    dict(question="2026 年底前，中国会出台全国性 AI 大模型备案简化政策吗？",
         category="科技", emoji="🤖", outcomes=["会", "不会"], probs=[0.28, 0.72],
         description="以工信部/网信办公开发布的正式文件为准（征求意见稿不算）。",
         rules="需为正式生效文件。", days=45, b=900),
    dict(question="2026 年 iPhone 出货量会同比下滑吗？",
         category="科技", emoji="📱", outcomes=["会", "不会"], probs=[0.34, 0.66],
         description="以 IDC 或 Counterpoint 全年出货量报告为准，取两家均值。",
         rules="任一家发布全年数据后 7 日内结算。", days=60, b=800),
    dict(question="下一届世界杯冠军会来自欧洲吗？",
         category="体育", emoji="⚽", outcomes=["会", "不会"], probs=[0.58, 0.42],
         description="以 FIFA 官方决赛结果为准。",
         rules="决赛终场（含加时/点球）结果。", days=120, b=1000),
    dict(question="2026 年 NBA 总决赛 MVP 会是内线球员吗？",
         category="体育", emoji="🏀", outcomes=["会", "不会"], probs=[0.22, 0.78],
         description="内线球员定义：常规赛 70% 以上出场时间打 4/5 号位。",
         rules="以联盟官方 FMVP 评选结果为准。", days=70, b=600),
    dict(question="2026 年内，会有一家千亿美元市值公司宣布把总部迁出美国吗？",
         category="政治", emoji="🏛️", outcomes=["会", "不会"], probs=[0.09, 0.91],
         description="以公司官方公告为准；市值按公告日前 20 日均值计算。",
         rules="需为正式公告并说明迁址计划。", days=47, b=700),
    dict(question="2026 年全年，中国新能源车渗透率会超过 60% 吗？",
         category="宏观", emoji="🚗", outcomes=["会", "不会"], probs=[0.47, 0.53],
         description="以中汽协（CAAM）全年新能源销量占比数据为准。",
         rules="以 CAAM 年度数据为准。", days=46, b=1100),
    dict(question="下一部票房破 40 亿人民币的国产电影会在 2026 年出现吗？",
         category="娱乐", emoji="🎬", outcomes=["会", "不会"], probs=[0.36, 0.64],
         description="以国家电影专资办/猫眼专业版票房数据为准。",
         rules="含合拍片，需为国产主出品。", days=46, b=500),
    dict(question="2026 年内，会有省级行政区全面放开限购吗？",
         category="社会", emoji="🏙️", outcomes=["会", "不会"], probs=[0.31, 0.69],
         description="以省级政府或住建部门正式文件为准。",
         rules="需覆盖全省范围。", days=46, b=600),
    dict(question="2026 年，OpenAI 会发布开源权重模型吗？",
         category="科技", emoji="🧠", outcomes=["会", "不会"], probs=[0.18, 0.82],
         description="开源权重指可在 Hugging Face 等平台自由下载的权重文件。",
         rules="以官方发布为准，API 开放不算。", days=46, b=1300),
    dict(question="2026 年第三季度，美国 CPI 同比会低于 2.5% 吗？",
         category="宏观", emoji="📉", outcomes=["会", "不会"], probs=[0.44, 0.56],
         description="以 BLS 公布的季度内三个月 CPI 同比数据为准，取最低月份。",
         rules="任一月份低于 2.5% 即判「会」。", days=30, b=900),
    dict(question="2026 年内，以太坊 ETF 会获批质押功能吗？",
         category="加密", emoji="🔷", outcomes=["会", "不会"], probs=[0.52, 0.48],
         description="以 SEC 正式批准文件为准。",
         rules="需包含质押收益分配条款。", days=46, b=1000),
    dict(question="谁会成为 2026 年最受欢迎的 AI 编程助手？",
         category="科技", emoji="⌨️", outcomes=["Claude Code", "Cursor", "GitHub Copilot", "其他"],
         probs=[0.34, 0.30, 0.24, 0.12],
         description="以 Stack Overflow 年度开发者调查使用占比为准。",
         rules="以调查正式发布数据为准。", days=90, b=1400),
    dict(question="2026 年底，全球市值最高的公司会是？",
         category="科技", emoji="🏆", outcomes=["英伟达", "苹果", "微软", "其他"],
         probs=[0.34, 0.27, 0.25, 0.14], featured=True,
         description="以 2026 年最后一个交易日收盘市值排序为准，单位美元。",
         rules="以各交易所同一时点收盘价 × 总股本计算，取最高者为胜。", days=46, b=1400),
    dict(question="2026 年内，哪家央行会最先降息？",
         category="宏观", emoji="🌐", outcomes=["美联储", "欧洲央行", "中国人民银行", "日本央行"],
         probs=[0.42, 0.30, 0.22, 0.06],
         description="以各央行首次下调政策利率的日期为准，同日则并列时按幅度取大者。",
         rules="以官方议息会议公告为准。", days=80, b=1200),
    dict(question="2026 年内，会出现首例「AI 生成内容不受版权保护」的生效判决吗？",
         category="科技", emoji="⚖️", outcomes=["会", "不会"], probs=[0.37, 0.63],
         description="需为二审或终审生效判决，且裁判文书明确 AI 纯生成内容不构成作品。",
         rules="以中国裁判文书网/美国 PACER 公开文书为准。", days=110, b=900),
]

RESOLVED = [
    dict(question="2026 年 10 月，比特币会收在 10 万美元以上吗？",
         category="加密", emoji="📈", outcomes=["会", "不会"], probs=[0.35, 0.65],
         description="Coinbase BTC-USD，2026-10-31 UTC 收盘价。",
         rules="收盘价 ≥ $100,000 判「会」。", days=-16, b=1200, winner=1),
    dict(question="2026 年 11 月的 FOMC 会议会降息吗？",
         category="宏观", emoji="🏛️", outcomes=["会", "不会"], probs=[0.4, 0.6],
         description="以 2026 年 11 月 FOMC 声明为准。",
         rules="目标区间下调 25bp 及以上判「会」。", days=-6, b=1000, winner=1),
    dict(question="2026 年 11 月，特斯拉会公布新的平价车型吗？",
         category="科技", emoji="🚙", outcomes=["会", "不会"], probs=[0.3, 0.7],
         description="以特斯拉官方发布会或新闻稿为准。",
         rules="需公布价格与量产时间。", days=-3, b=800, winner=0),
]


def _ts(days_from_now: float) -> str:
    return (datetime.now() + timedelta(days=days_from_now)).strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ 用户
def seed_users() -> dict:
    out = {"users": 0, "bots": 0}
    with get_conn() as conn:
        for email, pwd, handle, role, balance in DEMO_USERS:
            if one(conn, "SELECT id FROM users WHERE email=?", (email,)):
                continue
            insert(conn, "users", {
                "email": email, "handle": handle, "password_hash": hash_password(pwd),
                "role": role, "status": "active", "balance_cents": balance,
                "equity_seed": balance, "created_at": now(),
            })
            out["users"] += 1
        for email, handle in BOTS:
            if one(conn, "SELECT id FROM users WHERE email=?", (email,)):
                continue
            insert(conn, "users", {
                "email": email, "handle": handle,
                "password_hash": hash_password("bot12345678"),
                "role": "trader", "status": "active", "balance_cents": 5_000_00,
                "equity_seed": 5_000_00, "created_at": now(),
            })
            out["bots"] += 1
    return out


def _uid(email: str) -> int:
    with get_conn() as conn:
        return int(one(conn, "SELECT id FROM users WHERE email=?", (email,))["id"])


# ------------------------------------------------------------------ 市场
def seed_markets() -> dict:
    out = {"open": 0, "resolved": 0}
    with get_conn() as conn:
        exists = one(conn, "SELECT COUNT(*) AS n FROM markets")["n"]
    if exists:
        return out
    admin_id = _uid("admin@predx.io")

    for spec in MARKETS:
        res = svc.create_market(
            admin_id, spec["question"], spec["outcomes"],
            description=spec.get("description", ""), rules=spec.get("rules", ""),
            category=spec["category"], closes_at=_ts(spec["days"]),
            resolve_by=_ts(spec["days"] + 3), emoji=spec["emoji"],
            liquidity_b=spec["b"], probs=spec["probs"],
            featured=1 if spec.get("featured") else 0,
            source_url="https://example.com/settlement-source")
        out["open"] += 1

    for spec in RESOLVED:
        res = svc.create_market(
            admin_id, spec["question"], spec["outcomes"],
            description=spec.get("description", ""), rules=spec.get("rules", ""),
            category=spec["category"], closes_at=_ts(spec["days"]),
            resolve_by=_ts(spec["days"] + 2), emoji=spec["emoji"],
            liquidity_b=spec["b"], probs=spec["probs"])
        with get_conn() as conn:
            outs = many(conn, "SELECT * FROM outcomes WHERE market_id=? ORDER BY seq", (res["id"],))
        out.setdefault("pending", []).append((res["id"], outs[spec["winner"]]["id"]))
        out["resolved"] += 1
    return out


# ------------------------------------------------------------------ 模拟交易
def one_fresh_price(outcome_id: int) -> int:
    with get_conn() as conn:
        row = one(conn, "SELECT last_price_cents FROM outcomes WHERE id=?", (outcome_id,))
    return int(row["last_price_cents"]) if row else 50


def simulate_trading(rounds: int = 6) -> dict:
    rnd = random.Random(20261115)
    bot_ids = [_uid(e) for e, _ in BOTS] + [_uid("demo@predx.io")]
    with get_conn() as conn:
        markets = many(conn, "SELECT * FROM markets WHERE status='open' ORDER BY id")
    trades = 0
    for m in markets:
        with get_conn() as conn:
            outs = many(conn, "SELECT * FROM outcomes WHERE market_id=? ORDER BY seq", (m["id"],))
        # 每个结果的「锚定价」= 开盘时的第一个价格点；机器人围绕锚定价均值回归，
        # 这样演示数据既有两边成交，价格又不会被单边打到 1¢/99¢（那是很差的观感）。
        with get_conn() as conn:
            anchors = {}
            for o in outs:
                row = one(conn, """SELECT price_cents FROM price_points WHERE outcome_id=?
                                   ORDER BY id ASC LIMIT 1""", (o["id"],))
                anchors[o["id"]] = int(row["price_cents"]) if row else int(o["last_price_cents"])

        for _ in range(rounds):
            for uid in rnd.sample(bot_ids, k=rnd.randint(2, 4)):
                o = rnd.choice(outs)
                cur = int(one_fresh_price(o["id"]))
                anchor = anchors[o["id"]]
                user = {"user_id": uid, "role": "trader"}
                try:
                    if cur < anchor - 2 and rnd.random() < 0.72:
                        engine.place_order(user, m["id"], o["id"], "buy", order_type="market",
                                           budget_cents=rnd.choice([8_000, 15_000, 25_000]),
                                           max_slippage_bps=300)
                    elif cur > anchor + 2 and rnd.random() < 0.72:
                        engine.place_order(user, m["id"], o["id"], "sell", order_type="market",
                                           qty=rnd.randint(10, 70), max_slippage_bps=300)
                    else:
                        # 锚定区间内的小额双边成交，制造真实的盘口活跃度
                        if rnd.random() < 0.55:
                            engine.place_order(user, m["id"], o["id"], "buy", order_type="market",
                                               budget_cents=rnd.choice([5_000, 10_000, 20_000]),
                                               max_slippage_bps=300)
                        else:
                            engine.place_order(user, m["id"], o["id"], "sell", order_type="market",
                                               qty=rnd.randint(5, 40), max_slippage_bps=300)
                    trades += 1
                except engine.TradeError:
                    continue
    return {"trades": trades}


def _restamp_history() -> None:
    """把成交与价格点的时间铺到过去 7 天，让 K 线看起来像真的。"""
    with get_conn() as conn:
        markets = many(conn, "SELECT id, created_at FROM markets")
        for m in markets:
            trades = many(conn, "SELECT id FROM trades WHERE market_id=? ORDER BY id", (m["id"],))
            if not trades:
                continue
            base = datetime.now() - timedelta(days=7)
            span = timedelta(days=6, hours=20)
            step = span / max(1, len(trades))
            for i, t in enumerate(trades):
                conn.execute("UPDATE trades SET created_at=? WHERE id=?",
                             ((base + step * i).strftime("%Y-%m-%d %H:%M:%S"), t["id"]))
            points = many(conn, "SELECT id FROM price_points WHERE market_id=? ORDER BY id",
                          (m["id"],))
            if points:
                step_p = span / max(1, len(points))
                for i, p in enumerate(points):
                    conn.execute("UPDATE price_points SET ts=? WHERE id=?",
                                 ((base + step_p * i).strftime("%Y-%m-%d %H:%M:%S"), p["id"]))
            conn.execute("UPDATE markets SET created_at=? WHERE id=?",
                         ((base - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), m["id"]))


def _restamp_ledger() -> int:
    """把资金流水的时间按成交节奏重新铺开，让「现金余额变化」曲线有意义。"""
    moved = 0
    with get_conn() as conn:
        users = many(conn, "SELECT id FROM users")
    for u in users:
        with get_conn() as conn:
            rows = many(conn, "SELECT id FROM ledger WHERE user_id=? ORDER BY id", (u["id"],))
        if len(rows) < 2:
            continue
        base = datetime.now() - timedelta(days=7)
        step = timedelta(days=6, hours=20) / max(1, len(rows))
        with get_conn() as conn:
            for i, r in enumerate(rows):
                conn.execute("UPDATE ledger SET created_at=? WHERE id=?",
                             ((base + step * i).strftime("%Y-%m-%d %H:%M:%S"), r["id"]))
                moved += 1
    return moved


def seed_comments() -> int:
    samples = [
        "这个市场的深度不错，$500 才滑 1 分。",
        "我站「不会」，理由是时间窗口太紧。",
        "刚看了眼做市的报价，价差 2 分，算合理。",
        "提醒一下，结算规则里「正式文件」这条很关键，别拿征求意见稿来说事。",
        "已建仓，等着看。",
    ]
    rnd = random.Random(7)
    bot_ids = [_uid(e) for e, _ in BOTS]
    made = 0
    with get_conn() as conn:
        markets = many(conn, "SELECT id FROM markets WHERE status='open' ORDER BY id LIMIT 8")
        for m in markets:
            for text in rnd.sample(samples, k=rnd.randint(1, 3)):
                insert(conn, "comments", {
                    "market_id": m["id"], "user_id": rnd.choice(bot_ids), "body": text,
                    "parent_id": None, "created_at": _ts(-rnd.randint(1, 60) / 24),
                })
                made += 1
    return made


def bootstrap(verbose: bool = True) -> dict:
    from .db import migrate
    applied = migrate()
    u = seed_users()
    m = seed_markets()
    sim = {"trades": 0}
    with get_conn() as conn:
        n_trades = one(conn, "SELECT COUNT(*) AS n FROM trades")["n"]
    if not n_trades:
        sim = simulate_trading()
        _restamp_history()
        _restamp_ledger()
        for mid, win in (m.get("pending") or []):
            try:
                engine.resolve_market(mid, win, "按公开来源结算（演示数据）")
            except engine.TradeError:
                pass
        c = seed_comments()
    else:
        c = 0
        for mid, win in (m.get("pending") or []):
            try:
                engine.resolve_market(mid, win, "按公开来源结算（演示数据）")
            except engine.TradeError:
                pass

    info = {"migrations": applied, **u, **{k: v for k, v in m.items() if k != "pending"},
            **sim, "comments": c}
    if verbose:
        print(f"  · 迁移：{applied or '已是最新'}")
        print(f"  · 用户：新增 {u['users']} 个演示账号、{u['bots']} 个模拟交易员")
        print(f"  · 市场：上架 {m['open']} 个进行中 + {m['resolved']} 个已结算")
        print(f"  · 撮合：模拟成交 {sim['trades']} 笔，评论 {c} 条")
    return info
