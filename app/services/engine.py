"""撮合引擎：限价单簿 + LMSR 做市商 的混合模型。

撮合顺序（一笔单进来发生的事）：
  ① 先吃对手方的**限价单簿**（价格优先、同价时间优先）
  ② 剩余部分**吃做市商流动性**（LMSR，价格随成交量滑动）
  ③ 还没成交的部分**挂进簿子**（买单冻结现金、卖单冻结份额）

为什么不是纯订单簿：新市场上架时簿子是空的，用户点"买入"会失败。
为什么不是纯 AMM：AMM 无法让用户挂单赚价差，Polymarket 的专业做市商就活不了。
混合模型的代价是"用户限价单只有在价格穿越时才会成交"，这一点在文档里写清楚。

金额一律整数分。任何"取整"都朝着**不利于用户、有利于资金安全**的方向：
买入成本向上取整、卖出收入向下取整，所以系统永远不会因浮点误差产生坏账。
"""
from __future__ import annotations

import math

from ..config import config
from ..db import get_conn, insert, jdumps, many, now, one, transaction
from . import lmsr


class TradeError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


# ------------------------------------------------------------------ 行情
def market_row(conn, market_id: int) -> dict:
    m = one(conn, "SELECT * FROM markets WHERE id=?", (market_id,))
    if not m:
        raise TradeError("market_not_found", "市场不存在", 404)
    return m


def outcomes_of(conn, market_id: int) -> list[dict]:
    return many(conn, "SELECT * FROM outcomes WHERE market_id=? ORDER BY seq", (market_id,))


def q_vector(outs: list[dict]) -> list[float]:
    return [float(o["lmsr_q"]) for o in outs]


def prices_of(market: dict, outs: list[dict]) -> list[int]:
    return lmsr.prices_cents(q_vector(outs), float(market["liquidity_b"]))


def snapshot(conn, market_id: int) -> dict:
    """当前盘口：价格 + 最优买卖档 + 做市商深度。"""
    m = market_row(conn, market_id)
    outs = outcomes_of(conn, market_id)
    ps = prices_of(m, outs)
    book = {}
    for o, p in zip(outs, ps):
        asks = many(conn, """SELECT price_cents, SUM(qty-filled_qty) AS qty FROM orders
                             WHERE market_id=? AND outcome_id=? AND side='sell' AND status='open'
                             GROUP BY price_cents ORDER BY price_cents ASC LIMIT 12""",
                    (market_id, o["id"]))
        bids = many(conn, """SELECT price_cents, SUM(qty-filled_qty) AS qty FROM orders
                             WHERE market_id=? AND outcome_id=? AND side='buy' AND status='open'
                             GROUP BY price_cents ORDER BY price_cents DESC LIMIT 12""",
                    (market_id, o["id"]))
        book[o["id"]] = {"asks": asks, "bids": bids}
    return {"market_id": market_id, "prices": ps, "book": book,
            "liquidity_b": float(m["liquidity_b"])}


def refresh_prices(conn, market_id: int, write_points: bool = True) -> list[int]:
    m = market_row(conn, market_id)
    outs = outcomes_of(conn, market_id)
    ps = prices_of(m, outs)
    for o, p in zip(outs, ps):
        if int(o["last_price_cents"]) != p:
            conn.execute("UPDATE outcomes SET prev_price_cents=last_price_cents, last_price_cents=? WHERE id=?",
                         (p, o["id"]))
            if write_points:
                insert(conn, "price_points", {"market_id": market_id, "outcome_id": o["id"],
                                              "price_cents": p, "ts": now()})
    return ps


# ------------------------------------------------------------------ 资金
def _ledger(conn, user_id: int, kind: str, delta: int, market_id: int | None,
            ref: str | None, note: str | None = None) -> int:
    row = one(conn, "SELECT balance_cents FROM users WHERE id=?", (user_id,))
    after = int(row["balance_cents"])
    insert(conn, "ledger", {"user_id": user_id, "kind": kind, "delta_cents": delta,
                            "balance_after_cents": after, "market_id": market_id,
                            "ref": ref, "note": note, "created_at": now()})
    return after


def _add_balance(conn, user_id: int, delta: int, kind: str, market_id: int | None = None,
                 ref: str | None = None, note: str | None = None) -> int:
    conn.execute("UPDATE users SET balance_cents = balance_cents + ? WHERE id=?", (delta, user_id))
    return _ledger(conn, user_id, kind, delta, market_id, ref, note)


def _position(conn, user_id: int, market_id: int, outcome_id: int, create: bool = True) -> dict | None:
    row = one(conn, "SELECT * FROM positions WHERE user_id=? AND outcome_id=?",
              (user_id, outcome_id))
    if row or not create:
        return row
    insert(conn, "positions", {"user_id": user_id, "market_id": market_id, "outcome_id": outcome_id,
                               "shares": 0, "locked_shares": 0, "cost_cents": 0,
                               "realized_cents": 0, "updated_at": now()})
    return one(conn, "SELECT * FROM positions WHERE user_id=? AND outcome_id=?",
               (user_id, outcome_id))


def taker_fee(notional_cents: int, fee_bps: int) -> int:
    if fee_bps <= 0 or notional_cents <= 0:
        return 0
    return max(config.MIN_FEE_CENTS, int(notional_cents * fee_bps // 10000))


# ------------------------------------------------------------------ 报价（只读）
def _amm_max_shares(q: list[float], b: float, idx: int, limit_cents: int, is_buy: bool) -> int:
    """在限价内，做市商最多能给多少份（边际价格不越界）。"""
    def ok(delta: int) -> bool:
        after = list(q)
        after[idx] += delta if is_buy else -delta
        p = lmsr.prices_cents(after, b)[idx]
        return p <= limit_cents if is_buy else p >= limit_cents

    if not ok(1):
        return 0
    lo, hi = 1, 1
    while hi < 10 ** 7 and ok(hi):
        lo = hi
        hi *= 2
    hi = min(hi, 10 ** 7)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ok(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def _book_levels(conn, market_id: int, outcome_id: int, side: str, limit_cents: int) -> list[dict]:
    """对手方簿子：side=buy 时取对手的卖单（价低优先）。"""
    opp = "sell" if side == "buy" else "buy"
    cmp_op = "<=" if side == "buy" else ">="
    order_dir = "ASC" if side == "buy" else "DESC"
    return many(conn, f"""SELECT * FROM orders
                          WHERE market_id=? AND outcome_id=? AND side=? AND status='open'
                            AND price_cents {cmp_op} ?
                          ORDER BY price_cents {order_dir}, id ASC""",
                (market_id, outcome_id, opp, limit_cents))


def quote(market_id: int, outcome_id: int, side: str, qty: int | None = None,
          budget_cents: int | None = None, limit_cents: int | None = None,
          slippage_bps: int = 500) -> dict:
    """下单前预览：能吃多少、均价多少、滑点多少、预计费用。"""
    with get_conn() as conn:
        m = market_row(conn, market_id)
        outs = outcomes_of(conn, market_id)
        target = next((o for o in outs if o["id"] == outcome_id), None)
        if not target:
            raise TradeError("outcome_not_found", "结果不存在", 404)
        idx = outs.index(target)
        q = q_vector(outs)
        b = float(m["liquidity_b"])
        mid_cents = prices_of(m, outs)[idx]

        if limit_cents is None:
            limit_cents = min(config.PRICE_MAX, mid_cents + max(2, mid_cents * slippage_bps // 10000)) \
                if side == "buy" else max(config.PRICE_MIN, mid_cents - max(2, mid_cents * slippage_bps // 10000))

        # 簿子能成交的部分
        fills, remaining = [], qty if qty else 10 ** 9
        for od in _book_levels(conn, market_id, outcome_id, side, limit_cents):
            avail = od["qty"] - od["filled_qty"]
            if avail <= 0:
                continue
            take = min(avail, remaining)
            fills.append({"price_cents": od["price_cents"], "qty": take, "src": "book"})
            remaining -= take
            if remaining <= 0:
                break

        used_budget = sum(f["price_cents"] * f["qty"] for f in fills) if side == "buy" else 0
        amm_qty = 0
        if remaining > 0:
            if budget_cents and side == "buy":
                left_budget = max(0, budget_cents - used_budget)
                amm_qty = lmsr.max_buy_qty(q, b, idx, left_budget)
                amm_qty = min(amm_qty, _amm_max_shares(q, b, idx, limit_cents, True))
            elif qty:
                amm_qty = min(remaining, _amm_max_shares(q, b, idx, limit_cents, side == "buy"))
            else:
                amm_qty = _amm_max_shares(q, b, idx, limit_cents, side == "buy")

        amm_cost = 0
        amm_avg = None
        if amm_qty > 0:
            delta = amm_qty if side == "buy" else -amm_qty
            amm_cost = lmsr.trade_cost_cents(q, b, idx, delta, ceil_buy=(side == "buy"))
            if side == "buy":
                amm_avg = amm_cost / amm_qty
            else:
                amm_cost = abs(amm_cost)
                amm_avg = amm_cost / amm_qty

        total_qty = sum(f["qty"] for f in fills) + amm_qty
        book_cost = sum(f["price_cents"] * f["qty"] for f in fills)
        total_cost = book_cost + amm_cost
        avg = total_cost / total_qty if total_qty else 0
        notional = book_cost + amm_cost
        fee = taker_fee(notional, int(m["fee_bps"]))

        after_q = list(q)
        after_q[idx] += total_qty if side == "buy" else -total_qty
        return {
            "market_id": market_id, "outcome_id": outcome_id, "side": side,
            "mid_cents": mid_cents, "limit_cents": limit_cents,
            "levels": fills, "amm_qty": amm_qty, "amm_avg_cents": amm_avg,
            "qty": total_qty, "avg_cents": round(avg, 2), "notional_cents": notional,
            "fee_cents": fee,
            "total_cents": notional + fee if side == "buy" else notional - fee,
            "price_after_cents": lmsr.prices_cents(after_q, b)[idx],
            "payout_if_win_cents": total_qty * config.CONTRACT_PAYOUT_CENTS,
        }


# ------------------------------------------------------------------ 下单
def place_order(user: dict, market_id: int, outcome_id: int, side: str,
                qty: int | None = None, price_cents: int | None = None,
                order_type: str = "limit", budget_cents: int | None = None,
                max_slippage_bps: int = 500) -> dict:
    """下单主入口。返回成交明细 + 剩余挂单。"""
    side = (side or "").lower()
    order_type = (order_type or "limit").lower()
    if side not in ("buy", "sell"):
        raise TradeError("bad_side", "方向必须是 buy 或 sell")
    if order_type not in ("limit", "market"):
        raise TradeError("bad_type", "订单类型必须是 limit 或 market")

    with transaction() as conn:
        m = market_row(conn, market_id)
        if m["status"] != "open":
            raise TradeError("market_closed", "该市场已停止交易", 409)
        outs = outcomes_of(conn, market_id)
        target = next((o for o in outs if o["id"] == outcome_id), None)
        if not target:
            raise TradeError("outcome_not_found", "结果不存在", 404)
        idx = outs.index(target)
        q = q_vector(outs)
        b = float(m["liquidity_b"])
        mid = prices_of(m, outs)[idx]

        # ---- 限价/市价的价格边界
        if order_type == "market":
            if side == "buy":
                limit = min(config.PRICE_MAX, mid + max(2, mid * max_slippage_bps // 10000))
            else:
                limit = max(config.PRICE_MIN, mid - max(2, mid * max_slippage_bps // 10000))
        else:
            if price_cents is None:
                raise TradeError("bad_price", "限价单必须给出价格")
            limit = int(price_cents)
            if not (config.PRICE_MIN <= limit <= config.PRICE_MAX):
                raise TradeError("bad_price", f"价格必须在 {config.PRICE_MIN}–{config.PRICE_MAX} 分之间")

        bal = int(one(conn, "SELECT balance_cents FROM users WHERE id=?", (user["user_id"],))["balance_cents"])
        pos = _position(conn, user["user_id"], market_id, outcome_id, create=False)

        # ---- 卖出必须真的持有份额
        if side == "sell":
            available = int(pos["shares"] - pos["locked_shares"]) if pos else 0
            if qty and qty > available:
                raise TradeError("insufficient_shares",
                                 f"可卖份额不足（可用 {available} 份）")

        # ---- 数量/预算归一
        if order_type == "market" or qty is None:
            if side == "buy":
                budget = budget_cents if budget_cents is not None else bal
                if budget <= 0:
                    raise TradeError("insufficient_funds", "可用余额不足")
                if budget > bal:
                    raise TradeError("insufficient_funds", f"余额不足（可用 {bal} 分）")
                est = quote(market_id, outcome_id, "buy", budget_cents=budget, limit_cents=limit)
                qty = est["qty"]
                if qty <= 0:
                    raise TradeError("no_liquidity", "该价位内没有可成交的流动性", 409)
            else:
                available = int(pos["shares"] - pos["locked_shares"]) if pos else 0
                qty = qty or available
                if qty <= 0:
                    raise TradeError("insufficient_shares", "没有可卖份额")
        qty = int(qty)
        if qty < config.MIN_QTY:
            raise TradeError("bad_qty", "数量过小")
        if qty > config.MAX_QTY:
            raise TradeError("bad_qty", f"单笔最多 {config.MAX_QTY} 份")

        fee_bps = int(m["fee_bps"])
        fills: list[dict] = []
        remaining = qty

        # ================= ① 吃对手簿子 =================
        for od in _book_levels(conn, market_id, outcome_id, side, limit):
            if remaining <= 0:
                break
            avail = od["qty"] - od["filled_qty"]
            if avail <= 0:
                continue
            take = min(avail, remaining)
            price = int(od["price_cents"])
            if side == "buy":
                # 买家是 taker：支付挂单价格，冻结的差额退回
                cost = take * price
                fee = taker_fee(cost, fee_bps)
                conn.execute("UPDATE users SET balance_cents=balance_cents+? WHERE id=?",
                             (take * (limit - price), user["user_id"]))
                _add_balance(conn, user["user_id"], -cost, "trade_buy", market_id,
                             ref=f"order_match_{od['id']}")
                if fee:
                    _add_balance(conn, user["user_id"], -fee, "fee", market_id,
                                 note="吃单手续费")
                # 对手方（挂单卖家）结算
                _settle_seller(conn, od, take, price, fee_bps, market_id, outcome_id)
                buyer_id, seller_id = user["user_id"], od["user_id"]
                buy_order_id, sell_order_id = None, od["id"]
                _credit_buyer_position(conn, user["user_id"], market_id, outcome_id, take, cost + fee)
                fee_total = fee
            else:
                seller_proceeds = take * price
                fee = taker_fee(seller_proceeds, fee_bps)
                _settle_seller_fill(conn, user, pos, take, price, fee, market_id, outcome_id)
                # 对手方（挂单买家）结算
                _settle_buyer_order(conn, od, take, price, market_id, outcome_id)
                buyer_id, seller_id = od["user_id"], user["user_id"]
                buy_order_id, sell_order_id = od["id"], None
                _add_balance(conn, user["user_id"], seller_proceeds - fee, "trade_sell", market_id,
                             ref=f"order_match_{od['id']}")
                fee_total = fee

            _record_trade(conn, m, outcome_id, price, take, buyer_id, seller_id,
                          buy_order_id, sell_order_id, "buy" if side == "buy" else "sell",
                          fee_total, "book")
            conn.execute("UPDATE orders SET filled_qty=filled_qty+?, updated_at=?, "
                         "status=CASE WHEN filled_qty+? >= qty THEN 'filled' ELSE status END WHERE id=?",
                         (take, now(), take, od["id"]))
            fills.append({"price_cents": price, "qty": take, "src": "book", "counterparty_order": od["id"]})
            remaining -= take

        # ================= ② 吃做市商流动性 =================
        amm_qty = 0
        if remaining > 0:
            if side == "buy":
                if budget_cents is not None and order_type == "market":
                    left = budget_cents - sum(f["price_cents"] * f["qty"] for f in fills)
                    amm_qty = lmsr.max_buy_qty(q, b, idx, max(0, left))
                else:
                    amm_qty = remaining
                amm_qty = min(amm_qty, _amm_max_shares(q, b, idx, limit, True))
                if amm_qty > 0:
                    amm_qty = min(amm_qty, remaining) if order_type == "limit" else amm_qty
            else:
                amm_qty = min(remaining, _amm_max_shares(q, b, idx, limit, False))

            if amm_qty > 0:
                delta = amm_qty if side == "buy" else -amm_qty
                raw = lmsr.trade_cost_cents(q, b, idx, delta, ceil_buy=(side == "buy"))
                amm_cost = abs(raw)
                avg_price = amm_cost / amm_qty
                if side == "buy":
                    if amm_cost > bal:
                        raise TradeError("insufficient_funds", f"余额不足（可用 {bal} 分）")
                    fee = taker_fee(amm_cost, fee_bps)
                    _add_balance(conn, user["user_id"], -amm_cost - fee, "trade_buy", market_id,
                                 ref="amm", note="与做市商成交")
                    _credit_buyer_position(conn, user["user_id"], market_id, outcome_id, amm_qty,
                                           amm_cost + fee)
                    buyer_id, seller_id = user["user_id"], None
                    fee_total = fee
                else:
                    fee = taker_fee(amm_cost, fee_bps)
                    _settle_seller_fill(conn, user, pos, amm_qty, avg_price, fee, market_id,
                                        outcome_id, cost_override=amm_cost)
                    buyer_id, seller_id = None, user["user_id"]
                    fee_total = fee

                q[idx] += delta
                conn.execute("UPDATE outcomes SET lmsr_q=?, shares_outstanding=shares_outstanding+? WHERE id=?",
                             (q[idx], amm_qty if side == "buy" else -amm_qty, outcome_id))
                _record_trade(conn, m, outcome_id, int(round(avg_price)), amm_qty, buyer_id, seller_id,
                              None, None, "buy" if side == "buy" else "sell", fee_total, "amm")
                fills.append({"price_cents": round(avg_price, 2), "qty": amm_qty, "src": "amm"})
                remaining -= amm_qty

        # ================= ③ 剩余挂单 =================
        order_id = None
        if remaining > 0:
            if side == "buy":
                reserve = remaining * limit
                if reserve > bal - sum(f["price_cents"] * f["qty"] for f in fills):
                    # 余额不够挂满，按余额能挂多少挂多少
                    remaining = max(0, (bal - sum(f["price_cents"] * f["qty"] for f in fills)) // limit)
                    reserve = remaining * limit
                if remaining > 0:
                    _add_balance(conn, user["user_id"], -reserve, "reserve", market_id,
                                 note="限价单冻结")
            else:
                conn.execute("UPDATE positions SET locked_shares=locked_shares+?, updated_at=? "
                             "WHERE user_id=? AND outcome_id=?",
                             (remaining, now(), user["user_id"], outcome_id))
            if remaining > 0:
                order_id = insert(conn, "orders", {
                    "user_id": user["user_id"], "market_id": market_id, "outcome_id": outcome_id,
                    "side": side, "order_type": "limit", "price_cents": limit,
                    "qty": qty, "filled_qty": qty - remaining, "avg_fill_cents": 0,
                    "status": "open",
                    "reserved_cents": remaining * limit if side == "buy" else 0,
                    "taker_fee_cents": 0,
                    "created_at": now(), "updated_at": now(),
                })

        filled_qty = qty - remaining
        notional = sum(f["price_cents"] * f["qty"] for f in fills)
        avg = (notional / filled_qty) if filled_qty else 0

        # 已成交但未挂单的买单（限价高于成交价）要把差额退回
        if side == "buy" and order_type == "limit" and filled_qty > 0 and remaining == 0:
            pass  # 差额已在逐笔成交时退回

        refresh_prices(conn, market_id)
        prices_now = prices_of(market_row(conn, market_id), outcomes_of(conn, market_id))

    return {
        "market_id": market_id, "outcome_id": outcome_id, "side": side,
        "order_id": order_id, "requested_qty": qty, "filled_qty": filled_qty,
        "avg_price_cents": round(avg, 2), "notional_cents": notional,
        "resting_qty": remaining, "fills": fills,
        "price_after_cents": prices_now[idx],
    }


# ------------------------------------------------------------------ 结算辅助
def _credit_buyer_position(conn, user_id: int, market_id: int, outcome_id: int,
                          qty: int, cost_cents: int) -> None:
    _position(conn, user_id, market_id, outcome_id)
    conn.execute("""UPDATE positions SET shares=shares+?, cost_cents=cost_cents+?, updated_at=?
                    WHERE user_id=? AND outcome_id=?""",
                 (qty, cost_cents, now(), user_id, outcome_id))


def _settle_seller(conn, sell_order: dict, qty: int, price: int, fee_bps: int,
                   market_id: int, outcome_id: int) -> None:
    """挂单卖家成交：释放冻结份额、结算现金与已实现盈亏。"""
    seller_id = int(sell_order["user_id"])
    proceeds = qty * price
    fee = taker_fee(proceeds, fee_bps) if sell_order["order_type"] == "market" else 0
    pos = _position(conn, seller_id, market_id, outcome_id, create=False)
    shares = int(pos["shares"]) if pos else 0
    cost_total = int(pos["cost_cents"]) if pos else 0
    basis = (cost_total / shares) * qty if shares else 0
    conn.execute("""UPDATE positions SET shares=shares-?, locked_shares=MAX(0, locked_shares-?),
                    cost_cents=MAX(0, cost_cents-?), realized_cents=realized_cents+?, updated_at=?
                    WHERE user_id=? AND outcome_id=?""",
                 (qty, qty, int(basis), int(proceeds - basis - fee), now(), seller_id, outcome_id))
    _add_balance(conn, seller_id, proceeds - fee, "trade_sell", market_id,
                 ref=f"order_{sell_order['id']}", note="挂单成交")


def _settle_seller_fill(conn, user: dict, pos: dict | None, qty: int, price: float, fee: int,
                        market_id: int, outcome_id: int, cost_override: int | None = None) -> None:
    """自己作为卖方成交（吃对手买单或卖给做市商）。"""
    uid = user["user_id"]
    row = _position(conn, uid, market_id, outcome_id, create=False) or pos
    shares = int(row["shares"]) if row else 0
    cost_total = int(row["cost_cents"]) if row else 0
    basis = (cost_total / shares) * qty if shares else 0
    conn.execute("""UPDATE positions SET shares=shares-?, locked_shares=MAX(0, locked_shares-?),
                    cost_cents=MAX(0, cost_cents-?), realized_cents=realized_cents+?, updated_at=?
                    WHERE user_id=? AND outcome_id=?""",
                 (qty, 0, int(basis), int(qty * price - basis - fee), now(), uid, outcome_id))


def _settle_buyer_order(conn, buy_order: dict, qty: int, price: int, market_id: int,
                        outcome_id: int) -> None:
    """挂单买家成交：把冻结的差额退回，扣实际支出，加仓。"""
    buyer_id = int(buy_order["user_id"])
    refund = qty * (int(buy_order["price_cents"]) - price)
    if refund > 0:
        _add_balance(conn, buyer_id, refund, "refund", market_id,
                     ref=f"order_{buy_order['id']}", note="限价单成交价优于挂单价")
    fee = 0
    _credit_buyer_position(conn, buyer_id, market_id, outcome_id, qty, qty * price + fee)


def _record_trade(conn, m: dict, outcome_id: int, price: int, qty: int,
                  buyer_id: int | None, seller_id: int | None, buy_order_id: int | None,
                  sell_order_id: int | None, taker_side: str, fee: int, source: str) -> None:
    notional = price * qty
    insert(conn, "trades", {"market_id": m["id"], "outcome_id": outcome_id, "price_cents": price,
                            "qty": qty, "notional_cents": notional, "buyer_id": buyer_id,
                            "seller_id": seller_id, "buy_order_id": buy_order_id,
                            "sell_order_id": sell_order_id, "taker_side": taker_side,
                            "fee_cents": fee, "source": source, "created_at": now()})
    conn.execute("UPDATE markets SET volume_cents=volume_cents+?, trades_count=trades_count+1 WHERE id=?",
                 (notional, m["id"]))


# ------------------------------------------------------------------ 撤单
def cancel_order(user: dict, order_id: int) -> dict:
    with transaction() as conn:
        od = one(conn, "SELECT * FROM orders WHERE id=?", (order_id,))
        if not od:
            raise TradeError("order_not_found", "订单不存在", 404)
        if int(od["user_id"]) != user["user_id"] and user["role"] not in ("admin",):
            raise TradeError("forbidden", "只能撤自己的单", 403)
        if od["status"] != "open":
            raise TradeError("order_closed", "该订单已不在挂单状态", 409)
        remaining = od["qty"] - od["filled_qty"]
        if remaining > 0:
            if od["side"] == "buy":
                _add_balance(conn, int(od["user_id"]), remaining * int(od["price_cents"]),
                             "refund", od["market_id"], ref=f"cancel_{order_id}", note="撤单解冻")
            else:
                conn.execute("""UPDATE positions SET locked_shares=MAX(0, locked_shares-?), updated_at=?
                                WHERE user_id=? AND outcome_id=?""",
                             (remaining, now(), od["user_id"], od["outcome_id"]))
        conn.execute("UPDATE orders SET status='cancelled', updated_at=? WHERE id=?",
                     (now(), order_id))
    return {"ok": True, "order_id": order_id, "refunded_qty": remaining}


# ------------------------------------------------------------------ 结算
def resolve_market(market_id: int, winner_outcome_id: int, note: str = "", by: int | None = None) -> dict:
    with transaction() as conn:
        m = market_row(conn, market_id)
        if m["status"] == "resolved":
            raise TradeError("already_resolved", "该市场已结算", 409)
        outs = outcomes_of(conn, market_id)
        winner = next((o for o in outs if o["id"] == winner_outcome_id), None)
        if not winner:
            raise TradeError("outcome_not_found", "结果不存在", 404)

        # 撤掉所有未成交挂单并解冻
        opens = many(conn, "SELECT * FROM orders WHERE market_id=? AND status='open'", (market_id,))
        for od in opens:
            remaining = od["qty"] - od["filled_qty"]
            if remaining > 0:
                if od["side"] == "buy":
                    _add_balance(conn, int(od["user_id"]), remaining * int(od["price_cents"]),
                                 "refund", market_id, ref=f"resolve_{od['id']}", note="市场结算撤单")
                else:
                    conn.execute("""UPDATE positions SET locked_shares=MAX(0, locked_shares-?),
                                    updated_at=? WHERE user_id=? AND outcome_id=?""",
                                 (remaining, now(), od["user_id"], od["outcome_id"]))
        conn.execute("UPDATE orders SET status='cancelled', updated_at=? WHERE market_id=? AND status='open'",
                     (now(), market_id))

        # 赢家份额按 100 分兑付
        winners = many(conn, "SELECT * FROM positions WHERE market_id=? AND outcome_id=? AND shares>0",
                       (market_id, winner_outcome_id))
        paid = 0
        for p in winners:
            amount = int(p["shares"]) * config.CONTRACT_PAYOUT_CENTS
            _add_balance(conn, int(p["user_id"]), amount, "payout", market_id,
                         note=f"结算兑付 {p['shares']} 份 × $1.00")
            conn.execute("UPDATE positions SET realized_cents=realized_cents+?, cost_cents=0, "
                         "shares=0, locked_shares=0, updated_at=? WHERE id=?",
                         (amount - int(p["cost_cents"]), now(), p["id"]))
            paid += amount
        # 亏损方向清零
        conn.execute("""UPDATE positions SET shares=0, locked_shares=0, cost_cents=0, updated_at=?
                        WHERE market_id=? AND outcome_id<>?""",
                     (now(), market_id, winner_outcome_id))
        conn.execute("UPDATE outcomes SET is_winner=CASE WHEN id=? THEN 1 ELSE 0 END WHERE market_id=?",
                     (winner_outcome_id, market_id))
        conn.execute("""UPDATE markets SET status='resolved', resolved_at=?, resolution_outcome_id=?,
                        resolution_note=?, closed_at=COALESCE(closed_at, ?) WHERE id=?""",
                     (now(), winner_outcome_id, note, now(), market_id))
        # 让赢家价格收敛到 100、其余到 0
        for o in outcomes_of(conn, market_id):
            final = 100 if o["id"] == winner_outcome_id else 0
            conn.execute("UPDATE outcomes SET prev_price_cents=last_price_cents, last_price_cents=? WHERE id=?",
                         (final, o["id"]))
            insert(conn, "price_points", {"market_id": market_id, "outcome_id": o["id"],
                                          "price_cents": final, "ts": now()})
    return {"ok": True, "market_id": market_id, "winner_outcome_id": winner_outcome_id,
            "paid_cents": paid, "winner_name": winner["name"]}


# ------------------------------------------------------------------ 盘口视图
def book_view(market_id: int, outcome_id: int, levels: int | None = None,
              size: int | None = None) -> dict:
    """把「真实限价单」和「做市商合成深度」拼成一个盘口给前端。

    做市商深度由 LMSR 解析算出来：第 k 档的边际均价 = ΔC(k·s)/s。
    这样 UI 上的买一卖一、深度条都是真实可成交的量，不是画出来的假数据。
    """
    levels = levels or config.MAKER_LEVELS
    size = size or config.MAKER_SIZE
    with get_conn() as conn:
        m = market_row(conn, market_id)
        outs = outcomes_of(conn, market_id)
        target = next((o for o in outs if o["id"] == outcome_id), None)
        if not target:
            raise TradeError("outcome_not_found", "结果不存在", 404)
        idx = outs.index(target)
        q = q_vector(outs)
        b = float(m["liquidity_b"])
        mid = prices_of(m, outs)[idx]

        user_bids = many(conn, """SELECT price_cents, SUM(qty-filled_qty) AS qty FROM orders
                                  WHERE market_id=? AND outcome_id=? AND side='buy' AND status='open'
                                  GROUP BY price_cents ORDER BY price_cents DESC""",
                         (market_id, outcome_id))
        user_asks = many(conn, """SELECT price_cents, SUM(qty-filled_qty) AS qty FROM orders
                                  WHERE market_id=? AND outcome_id=? AND side='sell' AND status='open'
                                  GROUP BY price_cents ORDER BY price_cents ASC""",
                         (market_id, outcome_id))

    asks, bids = [], []
    prev_buy, prev_sell = 0.0, 0.0      # C(q) 归一为 0
    for k in range(1, levels + 1):
        cum = k * size
        # 第 k 档卖价 = 这 60 份的增量成本 / 份数（单位：分）
        buy_cost = lmsr.trade_cost(q, b, idx, cum)
        ask_cents = (buy_cost - prev_buy) * 100 / size
        prev_buy = buy_cost
        if ask_cents < 100:
            asks.append({"price_cents": round(ask_cents, 1), "qty": size, "src": "amm"})

        sell_cost = lmsr.trade_cost(q, b, idx, -cum)
        bid_cents = (prev_sell - sell_cost) * 100 / size
        prev_sell = sell_cost
        if bid_cents > 0:
            bids.append({"price_cents": round(bid_cents, 1), "qty": size, "src": "amm"})

    for a in asks:
        a["price_cents"] = min(config.PRICE_MAX, max(config.PRICE_MIN, a["price_cents"]))
    for bid in bids:
        bid["price_cents"] = min(config.PRICE_MAX, max(config.PRICE_MIN, bid["price_cents"]))

    best_ask = min([a["price_cents"] for a in asks] + [u["price_cents"] for u in user_asks],
                   default=mid)
    best_bid = max([x["price_cents"] for x in bids] + [u["price_cents"] for u in user_bids],
                   default=mid)
    return {"outcome_id": outcome_id, "mid_cents": mid,
            "asks": user_asks + asks, "bids": user_bids + bids,
            "best_ask_cents": best_ask, "best_bid_cents": best_bid,
            "spread_cents": round(best_ask - best_bid, 1),
            "amm_max_loss_cents": round(lmsr.max_loss(q, b) * 100)}
