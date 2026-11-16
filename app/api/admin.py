"""管理端：上架市场、停盘、结算、用户管理、审计。"""
from ..config import config
from ..db import get_conn, insert, many, now, one, update
from ..http import Forbidden, NotFound, Request, RequestError
from ..services import engine, markets as svc
from ..services.audit import log

ADMIN_ROLES = ("admin", "creator")


def _require_admin(req: Request) -> None:
    if req.user["role"] not in ADMIN_ROLES:
        raise Forbidden("需要管理员或市场创建者权限")


def create_market(req: Request):
    _require_admin(req)
    b = req.json()
    try:
        result = svc.create_market(
            req.user["user_id"], b.get("question") or "",
            b.get("outcomes") or [],
            description=b.get("description") or "",
            rules=b.get("rules") or "",
            category=b.get("category") or "综合",
            closes_at=b.get("closes_at"), resolve_by=b.get("resolve_by"),
            source_url=b.get("source_url"), emoji=b.get("emoji") or "🎯",
            liquidity_b=float(b["liquidity_b"]) if b.get("liquidity_b") else None,
            probs=[float(x) for x in b["probs"]] if b.get("probs") else None,
            featured=1 if b.get("featured") else 0)
    except ValueError as e:
        raise RequestError(400, str(e))
    with get_conn() as conn:
        log(conn, req.user["user_id"], "market.create", str(result["id"]),
            {"question": b.get("question")}, req.ip)
    return result


def close_market(req: Request):
    _require_admin(req)
    mid = int(req.params["id"])
    with get_conn() as conn:
        m = one(conn, "SELECT * FROM markets WHERE id=?", (mid,))
        if not m:
            raise NotFound("市场")
        if m["status"] != "open":
            raise RequestError(409, "只有进行中的市场可以停盘", "bad_status")
        update(conn, "markets", mid, {"status": "closed", "closed_at": now()})
        log(conn, req.user["user_id"], "market.close", str(mid), None, req.ip)
    return {"ok": True, "status": "closed"}


def reopen_market(req: Request):
    _require_admin(req)
    mid = int(req.params["id"])
    with get_conn() as conn:
        m = one(conn, "SELECT * FROM markets WHERE id=?", (mid,))
        if not m:
            raise NotFound("市场")
        if m["status"] != "closed":
            raise RequestError(409, "只有已停盘的市场可以重新开盘", "bad_status")
        update(conn, "markets", mid, {"status": "open", "closed_at": None})
    return {"ok": True, "status": "open"}


def resolve_market(req: Request):
    _require_admin(req)
    mid = int(req.params["id"])
    b = req.json()
    winner = int(b.get("outcome_id") or 0)
    if not winner:
        raise RequestError(400, "必须指定胜出结果 outcome_id")
    try:
        result = engine.resolve_market(mid, winner, b.get("note") or "",
                                       by=req.user["user_id"])
    except engine.TradeError as e:
        raise RequestError(e.status, e.message, e.code)
    with get_conn() as conn:
        log(conn, req.user["user_id"], "market.resolve", str(mid),
            {"winner": winner, "paid_cents": result["paid_cents"]}, req.ip)
    return result


def list_users(req: Request):
    _require_admin(req)
    with get_conn() as conn:
        rows = many(conn, """SELECT id,email,handle,role,status,balance_cents,equity_seed,
                                    created_at,last_login_at
                             FROM users ORDER BY id LIMIT 200""")
    return {"items": rows, "total": len(rows)}


def freeze_user(req: Request):
    _require_admin(req)
    uid = int(req.params["id"])
    b = req.json()
    status = b.get("status") or "frozen"
    if status not in ("active", "frozen"):
        raise RequestError(400, "状态不合法")
    with get_conn() as conn:
        if not one(conn, "SELECT id FROM users WHERE id=?", (uid,)):
            raise NotFound("用户")
        update(conn, "users", uid, {"status": status})
        log(conn, req.user["user_id"], "user.status", str(uid), {"status": status}, req.ip)
    return {"ok": True, "status": status}


def audit(req: Request):
    _require_admin(req)
    with get_conn() as conn:
        rows = many(conn, "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?",
                    (max(1, min(500, req.q_int("limit", 100))),))
    return {"items": rows, "total": len(rows)}


def admin_stats(req: Request):
    _require_admin(req)
    stats = svc.platform_stats()
    with get_conn() as conn:
        fees = one(conn, "SELECT COALESCE(SUM(fee_cents),0) AS f FROM trades")["f"]
        recent = many(conn, """SELECT t.*, m.question FROM trades t JOIN markets m ON m.id=t.market_id
                               ORDER BY t.id DESC LIMIT 20""")
        by_cat = many(conn, """SELECT category, COUNT(*) n, SUM(volume_cents) v FROM markets
                               GROUP BY category ORDER BY v DESC""")
        daily = many(conn, """SELECT substr(created_at,1,10) d, COUNT(*) n, SUM(notional_cents) v
                              FROM trades GROUP BY d ORDER BY d DESC LIMIT 14""")
    return {**stats, "fees_cents": fees, "recent_trades": recent,
            "by_category": by_cat, "daily": list(reversed(daily))}


def register_routes(r):
    r.post("/api/admin/markets", create_market)
    r.post("/api/admin/markets/<int:id>/close", close_market)
    r.post("/api/admin/markets/<int:id>/reopen", reopen_market)
    r.post("/api/admin/markets/<int:id>/resolve", resolve_market)
    r.get("/api/admin/users", list_users)
    r.post("/api/admin/users/<int:id>/status", freeze_user)
    r.get("/api/admin/audit", audit)
    r.get("/api/admin/stats", admin_stats)
