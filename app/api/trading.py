"""交易接口：下单、撤单、我的委托。"""
from ..db import get_conn, many, one
from ..http import Forbidden, NotFound, Request, RequestError
from ..services import engine
from ..services.audit import log


def _guard(user: dict) -> None:
    if user.get("status") not in (None, "active"):
        raise Forbidden("账号已被冻结")


def create_order(req: Request):
    b = req.json()
    mid = int(req.params["id"])
    oid = int(b.get("outcome_id") or 0)
    if not oid:
        raise RequestError(400, "缺少 outcome_id")
    side = (b.get("side") or "").lower()
    order_type = (b.get("order_type") or "limit").lower()
    qty = int(b["qty"]) if b.get("qty") else None
    price = int(b["price_cents"]) if b.get("price_cents") else None
    budget = int(b["amount_cents"]) if b.get("amount_cents") else None
    try:
        result = engine.place_order(req.user, mid, oid, side, qty=qty, price_cents=price,
                                   order_type=order_type, budget_cents=budget,
                                   max_slippage_bps=int(b.get("max_slippage_bps") or 500))
    except engine.TradeError as e:
        raise RequestError(e.status, e.message, e.code)
    with get_conn() as conn:
        log(conn, req.user["user_id"], "trade.order", str(mid),
            {"outcome_id": oid, "side": side, "type": order_type, "qty": qty,
             "price_cents": price, "filled": result["filled_qty"]}, req.ip)
    return result


def cancel_order(req: Request):
    oid = int(req.params["id"])
    try:
        result = engine.cancel_order(req.user, oid)
    except engine.TradeError as e:
        raise RequestError(e.status, e.message, e.code)
    with get_conn() as conn:
        log(conn, req.user["user_id"], "trade.cancel", str(oid), None, req.ip)
    return result


def my_orders(req: Request):
    status = req.q("status", "open")
    with get_conn() as conn:
        where = "AND o.status=?" if status != "all" else ""
        params = (req.user["user_id"], status) if where else (req.user["user_id"],)
        rows = many(conn, f"""SELECT o.*, m.question, m.emoji, oc.name AS outcome_name,
                                     m.id AS market_id
                              FROM orders o JOIN markets m ON m.id=o.market_id
                              JOIN outcomes oc ON oc.id=o.outcome_id
                              WHERE o.user_id=? {where} ORDER BY o.id DESC LIMIT 100""", params)
    return {"items": rows, "total": len(rows)}


def my_trades(req: Request):
    with get_conn() as conn:
        rows = many(conn, """SELECT t.*, m.question, oc.name AS outcome_name,
                                    CASE WHEN t.buyer_id=? THEN 'buy' ELSE 'sell' END AS my_side,
                                    (SELECT handle FROM users WHERE id = CASE WHEN t.buyer_id=? THEN t.seller_id
                                                                              ELSE t.buyer_id END) AS counterparty
                             FROM trades t JOIN markets m ON m.id=t.market_id
                             JOIN outcomes oc ON oc.id=t.outcome_id
                             WHERE t.buyer_id=? OR t.seller_id=?
                             ORDER BY t.id DESC LIMIT 100""",
                    (req.user["user_id"], req.user["user_id"], req.user["user_id"],
                     req.user["user_id"]))
    return {"items": rows, "total": len(rows)}


def order_detail(req: Request):
    oid = int(req.params["id"])
    with get_conn() as conn:
        row = one(conn, "SELECT * FROM orders WHERE id=?", (oid,))
        if not row:
            raise NotFound("订单")
        if int(row["user_id"]) != req.user["user_id"] and req.user["role"] != "admin":
            raise Forbidden("只能查看自己的订单")
        fills = many(conn, "SELECT * FROM trades WHERE buy_order_id=? OR sell_order_id=? ORDER BY id",
                     (oid, oid))
    return {**row, "fills": fills}


def register_routes(r):
    r.post("/api/markets/<int:id>/orders", create_order)
    r.delete("/api/orders/<int:id>", cancel_order)
    r.get("/api/orders", my_orders)
    r.get("/api/orders/<int:id>", order_detail)
    r.get("/api/my/trades", my_trades)
