"""社区：评论与关注列表。"""
from ..db import get_conn, insert, many, now, one
from ..http import Forbidden, NotFound, Request, RequestError


def list_comments(req: Request):
    mid = int(req.params["id"])
    with get_conn() as conn:
        rows = many(conn, """SELECT c.*, u.handle FROM comments c JOIN users u ON u.id=c.user_id
                             WHERE c.market_id=? ORDER BY c.id DESC LIMIT 100""", (mid,))
    return {"items": rows, "total": len(rows)}


def post_comment(req: Request):
    mid = int(req.params["id"])
    body = (req.json().get("body") or "").strip()
    if len(body) < 2:
        raise RequestError(400, "评论至少 2 个字")
    if len(body) > 500:
        raise RequestError(400, "评论最多 500 字")
    with get_conn() as conn:
        if not one(conn, "SELECT id FROM markets WHERE id=?", (mid,)):
            raise NotFound("市场")
        cid = insert(conn, "comments", {"market_id": mid, "user_id": req.user["user_id"],
                                        "body": body, "parent_id": None, "created_at": now()})
    return {"id": cid}


def watch(req: Request):
    mid = int(req.params["id"])
    with get_conn() as conn:
        exists = one(conn, "SELECT 1 FROM watchlist WHERE user_id=? AND market_id=?",
                     (req.user["user_id"], mid))
        if exists:
            conn.execute("DELETE FROM watchlist WHERE user_id=? AND market_id=?",
                         (req.user["user_id"], mid))
            return {"watching": False}
        insert(conn, "watchlist", {"user_id": req.user["user_id"], "market_id": mid,
                                   "created_at": now()})
    return {"watching": True}


def my_watchlist(req: Request):
    from ..services import markets as svc
    with get_conn() as conn:
        rows = many(conn, """SELECT m.* FROM watchlist w JOIN markets m ON m.id=w.market_id
                             WHERE w.user_id=? ORDER BY w.created_at DESC""",
                    (req.user["user_id"],))
        ids = [r["id"] for r in rows]
        outs = many(conn, f"SELECT * FROM outcomes WHERE market_id IN ({','.join('?'*len(ids))}) "
                          "ORDER BY market_id, seq", tuple(ids)) if ids else []
    by: dict[int, list] = {}
    for o in outs:
        by.setdefault(o["market_id"], []).append(o)
    return {"items": [svc.serialize_market(m, by.get(m["id"], [])) for m in rows]}


def register_routes(r):
    r.get("/api/markets/<int:id>/comments", list_comments, auth=False)
    r.post("/api/markets/<int:id>/comments", post_comment)
    r.post("/api/markets/<int:id>/watch", watch)
    r.get("/api/watchlist", my_watchlist)
