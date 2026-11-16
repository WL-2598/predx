"""账户资产：持仓、资金流水、充值（虚拟资金）。"""
from ..config import config
from ..db import get_conn, insert, many, now, one, transaction
from ..http import Request, RequestError
from ..services import markets as svc
from ..services.audit import log


def portfolio(req: Request):
    try:
        return svc.portfolio(req.user["user_id"])
    except ValueError:
        raise RequestError(404, "用户不存在")


def ledger(req: Request):
    with get_conn() as conn:
        rows = many(conn, "SELECT * FROM ledger WHERE user_id=? ORDER BY id DESC LIMIT ?",
                    (req.user["user_id"], max(1, min(200, req.q_int("limit", 50)))))
        user = one(conn, "SELECT balance_cents FROM users WHERE id=?", (req.user["user_id"],))
    return {"items": rows, "balance_cents": user["balance_cents"]}


def deposit(req: Request):
    """虚拟资金充值：这是演示环境，不涉及任何真实支付。"""
    b = req.json()
    amount = int(b.get("amount_cents") or 0)
    if amount < 1000:
        raise RequestError(400, "单次至少充值 $10.00")
    if amount > 10_000_000:
        raise RequestError(400, "单次最多充值 $100,000.00")
    with transaction() as conn:
        conn.execute("UPDATE users SET balance_cents=balance_cents+? WHERE id=?",
                     (amount, req.user["user_id"]))
        bal = one(conn, "SELECT balance_cents FROM users WHERE id=?", (req.user["user_id"],))
        insert(conn, "ledger", {
            "user_id": req.user["user_id"], "kind": "deposit", "delta_cents": amount,
            "balance_after_cents": bal["balance_cents"], "market_id": None, "ref": "demo",
            "note": "体验金充值（虚拟资金）", "created_at": now(),
        })
        log(conn, req.user["user_id"], "wallet.deposit", None, {"amount_cents": amount}, req.ip)
    return {"ok": True, "balance_cents": bal["balance_cents"]}


def register_routes(r):
    r.get("/api/portfolio", portfolio)
    r.get("/api/wallet/ledger", ledger)
    r.post("/api/wallet/deposit", deposit)
