"""市场浏览接口：列表、详情、盘口、报价、K 线数据、平台统计。"""
from ..config import config
from ..db import get_conn, many, one
from ..http import NotFound, Request, RequestError
from ..services import engine, markets as svc


def _market_or_404(market_id: int) -> dict:
    with get_conn() as conn:
        m = one(conn, "SELECT * FROM markets WHERE id=?", (market_id,))
    if not m:
        raise NotFound("市场")
    return m


def list_markets(req: Request):
    return svc.list_markets(
        category=req.q("category"), status=req.q("status", "open"),
        q=(req.q("q") or "").strip() or None, sort=req.q("sort", "hot"),
        limit=max(1, min(200, req.q_int("limit", 60))))


def get_market(req: Request):
    mid = int(req.params["id"])
    try:
        return svc.market_detail(mid)
    except ValueError:
        raise NotFound("市场")


def get_market_by_slug(req: Request):
    try:
        return svc.market_detail(slug=req.params["slug"])
    except ValueError:
        raise NotFound("市场")


def history(req: Request):
    mid = int(req.params["id"])
    oid = req.q_int("outcome_id", 0) or None
    try:
        return svc.price_history(mid, oid, max(20, min(1000, req.q_int("limit", 400))),
                                 range_key=req.q("range", "all") or "all")
    except ValueError:
        raise NotFound("市场")


def orderbook(req: Request):
    mid = int(req.params["id"])
    oid = req.q_int("outcome_id", 0)
    if not oid:
        detail = svc.market_detail(mid)
        oid = detail["outcomes"][0]["id"]
    try:
        return engine.book_view(mid, oid)
    except engine.TradeError as e:
        raise RequestError(e.status, e.message, e.code)


def quote(req: Request):
    mid = int(req.params["id"])
    b = req.json()
    oid = int(b.get("outcome_id") or 0)
    side = (b.get("side") or "buy").lower()
    if not oid:
        raise RequestError(400, "缺少 outcome_id")
    try:
        return engine.quote(mid, oid, side,
                            qty=int(b["qty"]) if b.get("qty") else None,
                            budget_cents=int(b["amount_cents"]) if b.get("amount_cents") else None,
                            limit_cents=int(b["price_cents"]) if b.get("price_cents") else None,
                            slippage_bps=int(b.get("max_slippage_bps") or 500))
    except engine.TradeError as e:
        raise RequestError(e.status, e.message, e.code)


def categories(req: Request):
    with get_conn() as conn:
        rows = many(conn, """SELECT category, COUNT(*) AS n, SUM(volume_cents) AS vol
                             FROM markets WHERE status='open' GROUP BY category
                             ORDER BY vol DESC""")
    return {"items": rows, "all": svc.CATEGORIES}


def stats(req: Request):
    return svc.platform_stats()


def leaderboard(req: Request):
    return svc.leaderboard(max(1, min(100, req.q_int("limit", 20))))


def register_routes(r):
    r.get("/api/markets", list_markets, auth=False)
    r.get("/api/markets/categories", categories, auth=False)
    r.get("/api/markets/stats", stats, auth=False)
    r.get("/api/leaderboard", leaderboard, auth=False)
    r.get("/api/markets/<int:id>", get_market, auth=False)
    r.get("/api/markets/<int:id>/history", history, auth=False)
    r.get("/api/markets/<int:id>/book", orderbook, auth=False)
    r.post("/api/markets/<int:id>/quote", quote, auth=False)
    r.get("/api/m/<slug>", get_market_by_slug, auth=False)
