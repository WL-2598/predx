"""市场（事件）服务：上架、筛选、序列化、持仓与排行榜。"""
from __future__ import annotations

import math
import re
import time

from ..config import config
from ..db import get_conn, insert, jdumps, many, now, one, transaction
from . import engine, lmsr

CATEGORIES = ["政治", "加密", "宏观", "科技", "体育", "娱乐", "社会", "综合"]


def slugify(question: str, suffix: str | None = None) -> str:
    base = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fa5]+", "-", question).strip("-").lower()
    base = base[:60] or "market"
    return f"{base}-{suffix}" if suffix else base


def _q_from_probs(probs: list[float], b: float) -> list[float]:
    """把目标概率换算成 LMSR 状态向量（价格 = softmax(q/b)）。"""
    total = sum(probs)
    probs = [p / total for p in probs]
    return [b * math.log(max(p, 1e-4)) for p in probs]


def create_market(user_id: int | None, question: str, outcomes: list[str], *,
                  description: str = "", rules: str = "", category: str = "综合",
                  closes_at: str | None = None, resolve_by: str | None = None,
                  source_url: str | None = None, emoji: str = "🎯",
                  liquidity_b: float | None = None, probs: list[float] | None = None,
                  featured: int = 0) -> dict:
    question = (question or "").strip()
    if len(question) < 6:
        raise ValueError("问题描述至少 6 个字")
    outcomes = [o.strip() for o in outcomes if o and o.strip()]
    if len(outcomes) < 2:
        raise ValueError("至少需要 2 个结果")
    if len(outcomes) > 8:
        raise ValueError("最多支持 8 个结果")
    b = float(liquidity_b or config.DEFAULT_LMSR_B)
    probs = probs or [1.0 / len(outcomes)] * len(outcomes)
    if len(probs) != len(outcomes):
        raise ValueError("概率数组长度必须与结果数一致")
    q = _q_from_probs(probs, b)
    market_type = "binary" if len(outcomes) == 2 else "multi"

    with transaction() as conn:
        slug_base = slugify(question)
        slug = slug_base
        n = 1
        while one(conn, "SELECT id FROM markets WHERE slug=?", (slug,)):
            n += 1
            slug = f"{slug_base}-{n}"
        mid = insert(conn, "markets", {
            "slug": slug, "question": question, "description": description, "rules": rules,
            "category": category, "market_type": market_type, "status": "open", "emoji": emoji,
            "closes_at": closes_at, "resolve_by": resolve_by, "source_url": source_url,
            "liquidity_b": b, "fee_bps": config.TAKER_FEE_BPS, "volume_cents": 0,
            "trades_count": 0, "featured": featured, "created_by": user_id,
            "created_at": now(),
        })
        cents = lmsr.prices_cents(q, b)
        for i, name in enumerate(outcomes):
            insert(conn, "outcomes", {
                "market_id": mid, "seq": i, "name": name, "lmsr_q": q[i],
                "shares_outstanding": 0, "last_price_cents": cents[i],
                "prev_price_cents": cents[i], "is_winner": 0,
            })
            oid = one(conn, "SELECT id FROM outcomes WHERE market_id=? AND seq=?", (mid, i))["id"]
            insert(conn, "price_points", {"market_id": mid, "outcome_id": oid,
                                          "price_cents": cents[i], "ts": now()})
    return {"id": mid, "slug": slug, "prices": cents}


# ------------------------------------------------------------------ 序列化
def _trend(conn, market_id: int, outcome_id: int, current: int) -> dict:
    """24 小时涨跌：取 24 小时前最近一个价格点。"""
    row = one(conn, """SELECT price_cents FROM price_points
                       WHERE outcome_id=? AND ts <= datetime('now','localtime','-1 day')
                       ORDER BY id DESC LIMIT 1""", (outcome_id,))
    if not row:
        row = one(conn, "SELECT price_cents FROM price_points WHERE outcome_id=? ORDER BY id ASC LIMIT 1",
                  (outcome_id,))
    base = int(row["price_cents"]) if row else current
    return {"base_cents": base, "delta_cents": current - base}


def serialize_market(m: dict, outs: list[dict], *, detail: bool = False,
                     prices: list[int] | None = None, conn=None) -> dict:
    ps = prices or [int(o["last_price_cents"]) for o in outs]
    out = {
        "id": m["id"], "slug": m["slug"], "question": m["question"],
        "category": m["category"], "market_type": m["market_type"], "status": m["status"],
        "emoji": m["emoji"], "closes_at": m["closes_at"], "resolve_by": m["resolve_by"],
        "volume_cents": m["volume_cents"], "trades_count": m["trades_count"],
        "featured": bool(m["featured"]), "created_at": m["created_at"],
        "liquidity": round(m["liquidity_b"] * math.log(len(outs)) / 100, 2),
        "outcomes": [{
            "id": o["id"], "name": o["name"], "price_cents": p,
            "probability": round(p / 100, 4),
            "shares_outstanding": o["shares_outstanding"],
            "is_winner": bool(o["is_winner"]),
        } for o, p in zip(outs, ps)],
    }
    if m["status"] == "resolved":
        out["resolution"] = {"outcome_id": m["resolution_outcome_id"],
                             "note": m["resolution_note"], "resolved_at": m["resolved_at"]}
    if detail:
        out.update({
            "description": m["description"], "rules": m["rules"],
            "source_url": m["source_url"], "fee_bps": m["fee_bps"],
            "liquidity_b": m["liquidity_b"], "closed_at": m["closed_at"],
            "top_holders": [],
        })
    return out


def list_markets(category: str | None = None, status: str | None = "open",
                 q: str | None = None, sort: str = "hot", limit: int = 60) -> dict:
    with get_conn() as conn:
        where, params = [], []
        if status and status != "all":
            where.append("m.status=?")
            params.append(status)
        if category and category not in ("all", "全部"):
            where.append("m.category=?")
            params.append(category)
        if q:
            where.append("(m.question LIKE ? OR m.description LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        order = {
            "hot": "m.featured DESC, m.volume_cents DESC",
            "new": "m.id DESC",
            "closing": "COALESCE(m.closes_at,'9999') ASC",
            "trending": "m.trades_count DESC",
        }.get(sort, "m.volume_cents DESC")
        rows = many(conn, f"SELECT * FROM markets m {clause} ORDER BY {order} LIMIT ?",
                    (*params, limit))
        if not rows:
            return {"items": [], "total": 0, "categories": CATEGORIES}
        ids = [r["id"] for r in rows]
        ph = ",".join("?" * len(ids))
        outs = many(conn, f"SELECT * FROM outcomes WHERE market_id IN ({ph}) ORDER BY market_id, seq",
                    tuple(ids))
    by_market: dict[int, list] = {}
    for o in outs:
        by_market.setdefault(o["market_id"], []).append(o)

    # 每张卡片下面那条迷你走势：取该市场第一个结果的最近 24 个价格点
    sparks: dict[int, list[int]] = {}
    trends: dict[int, dict] = {}
    with get_conn() as conn:
        for m in rows:
            o_list = by_market.get(m["id"], [])
            if not o_list:
                continue
            first = o_list[0]
            pts = many(conn, """SELECT price_cents FROM price_points WHERE outcome_id=?
                                ORDER BY id DESC LIMIT 24""", (first["id"],))
            sparks[m["id"]] = [p["price_cents"] for p in reversed(pts)]
            trends[m["id"]] = _trend(conn, m["id"], first["id"], int(first["last_price_cents"]))

    # 每个市场的参与交易人数（买卖双方去重）
    ids_sql = ",".join("?" * len(rows))
    with get_conn() as conn:
        trader_rows = many(conn, f"""
            SELECT market_id, COUNT(DISTINCT uid) AS n FROM (
                SELECT market_id, buyer_id AS uid FROM trades
                 WHERE market_id IN ({ids_sql}) AND buyer_id IS NOT NULL
                UNION
                SELECT market_id, seller_id AS uid FROM trades
                 WHERE market_id IN ({ids_sql}) AND seller_id IS NOT NULL
            ) GROUP BY market_id""", tuple([r["id"] for r in rows] * 2))
    traders = {r["market_id"]: r["n"] for r in trader_rows}

    items = []
    for m in rows:
        o_list = by_market.get(m["id"], [])
        item = serialize_market(m, o_list)
        item["spark"] = sparks.get(m["id"], [])
        item["trend"] = trends.get(m["id"], {"base_cents": 0, "delta_cents": 0})
        item["traders_count"] = traders.get(m["id"], 0)
        items.append(item)
    return {"items": items, "total": len(items), "categories": CATEGORIES}


def market_detail(market_id: int | None = None, slug: str | None = None) -> dict:
    with get_conn() as conn:
        m = one(conn, "SELECT * FROM markets WHERE id=?", (market_id,)) if market_id else \
            one(conn, "SELECT * FROM markets WHERE slug=?", (slug,))
        if not m:
            raise ValueError("市场不存在")
        outs = many(conn, "SELECT * FROM outcomes WHERE market_id=? ORDER BY seq", (m["id"],))
        trades = many(conn, """SELECT t.*, o.name AS outcome_name,
                                      ub.handle AS buyer_handle, us.handle AS seller_handle
                               FROM trades t
                               LEFT JOIN outcomes o ON o.id=t.outcome_id
                               LEFT JOIN users ub ON ub.id=t.buyer_id
                               LEFT JOIN users us ON us.id=t.seller_id
                               WHERE t.market_id=? ORDER BY t.id DESC LIMIT 30""", (m["id"],))
        ccount = one(conn, "SELECT COUNT(*) AS n FROM comments WHERE market_id=?", (m["id"],))
        tcount = one(conn, """SELECT COUNT(DISTINCT uid) AS n FROM (
                                SELECT buyer_id AS uid FROM trades WHERE market_id=? AND buyer_id IS NOT NULL
                                UNION SELECT seller_id AS uid FROM trades WHERE market_id=? AND seller_id IS NOT NULL
                              )""", (m["id"], m["id"]))
        related = many(conn, """SELECT * FROM markets WHERE category=? AND status='open' AND id<>?
                                ORDER BY volume_cents DESC LIMIT 3""", (m["category"], m["id"]))
        rel_outs = many(conn, f"SELECT * FROM outcomes WHERE market_id IN ({','.join('?'*len(related))}) "
                              "ORDER BY market_id, seq", tuple(r["id"] for r in related)) if related else []
        holders = many(conn, """SELECT p.outcome_id, p.shares, p.cost_cents, u.handle, o.name AS outcome_name
                                FROM positions p JOIN users u ON u.id=p.user_id
                                JOIN outcomes o ON o.id=p.outcome_id
                                WHERE p.market_id=? AND p.shares>0
                                ORDER BY p.shares DESC LIMIT 10""", (m["id"],))
    data = serialize_market(m, outs, detail=True)
    data["recent_trades"] = trades
    data["top_holders"] = holders
    data["books"] = {o["id"]: engine.book_view(m["id"], o["id"]) for o in outs}
    data["comments_count"] = ccount["n"] if ccount else 0
    data["traders_count"] = tcount["n"] if tcount else 0
    rel_by: dict[int, list] = {}
    for o in rel_outs:
        rel_by.setdefault(o["market_id"], []).append(o)
    data["related"] = [serialize_market(r, rel_by.get(r["id"], [])) for r in related]
    return data


RANGES = {"1h": 3600, "6h": 6 * 3600, "1d": 86400, "1w": 7 * 86400,
          "1m": 30 * 86400, "all": None}


def _resample(points: list[dict], buckets: int = 90) -> list[dict]:
    """把价格点按时间均匀重采样到 buckets 个桶（每桶取最后一个点）。

    成交驱动的数据在时间轴上疏密不均，直接连线会出现难看的锯齿；
    按时间桶聚合后曲线更像真实产品的行情图。
    """
    if len(points) <= buckets:
        return points
    out, size = [], max(1, len(points) // buckets)
    for i in range(0, len(points), size):
        chunk = points[i:i + size]
        out.append(chunk[-1])
    return out


def price_history(market_id: int, outcome_id: int | None = None, limit: int = 200,
                  range_key: str = "all") -> dict:
    with get_conn() as conn:
        outs = many(conn, "SELECT * FROM outcomes WHERE market_id=? ORDER BY seq", (market_id,))
        if not outs:
            raise ValueError("市场不存在")
        targets = [o for o in outs if outcome_id in (None, o["id"])]
        series, stats = {}, {}
        seconds = RANGES.get(range_key, None)
        for o in targets:
            if seconds:
                pts = many(conn, f"""SELECT price_cents, ts FROM price_points
                                     WHERE outcome_id=?
                                       AND ts >= datetime('now','localtime','-{int(seconds)} seconds')
                                     ORDER BY id""", (o["id"],))
            else:
                pts = many(conn, """SELECT price_cents, ts FROM price_points
                                    WHERE outcome_id=? ORDER BY id""", (o["id"],))
            if not pts:      # 区间内没有点（例如新市场）→ 退化到全量
                pts = many(conn, """SELECT price_cents, ts FROM price_points
                                    WHERE outcome_id=? ORDER BY id DESC LIMIT ?""",
                           (o["id"], limit))
                pts = list(reversed(pts))
            pts = _resample(pts[-limit:], 90)
            series[o["id"]] = pts
            if pts:
                first, last = pts[0]["price_cents"], pts[-1]["price_cents"]
                stats[o["id"]] = {"open_cents": first, "last_cents": last,
                                  "high_cents": max(p["price_cents"] for p in pts),
                                  "low_cents": min(p["price_cents"] for p in pts),
                                  "delta_cents": last - first,
                                  "points": len(pts)}
    return {"market_id": market_id, "range": range_key, "series": series, "stats": stats}


# ------------------------------------------------------------------ 持仓与账户
def portfolio(user_id: int) -> dict:
    with get_conn() as conn:
        user = one(conn, "SELECT id,email,handle,balance_cents,role,created_at FROM users WHERE id=?",
                   (user_id,))
        if not user:
            raise ValueError("用户不存在")
        rows = many(conn, """SELECT p.*, m.question, m.status AS market_status, m.emoji,
                                    m.category, o.name AS outcome_name, o.last_price_cents,
                                    m.id AS market_id
                             FROM positions p
                             JOIN markets m ON m.id=p.market_id
                             JOIN outcomes o ON o.id=p.outcome_id
                             WHERE p.user_id=? AND (p.shares>0 OR p.locked_shares>0)
                             ORDER BY p.updated_at DESC""", (user_id,))
        prices = {}
        for r in rows:
            if r["market_id"] not in prices:
                outs = many(conn, "SELECT * FROM outcomes WHERE market_id=? ORDER BY seq",
                            (r["market_id"],))
                prices[r["market_id"]] = {o["id"]: int(o["last_price_cents"]) for o in outs}
        orders = many(conn, """SELECT o.*, m.question, oc.name AS outcome_name
                               FROM orders o JOIN markets m ON m.id=o.market_id
                               JOIN outcomes oc ON oc.id=o.outcome_id
                               WHERE o.user_id=? AND o.status='open' ORDER BY o.id DESC""", (user_id,))
        history = many(conn, """SELECT * FROM trades WHERE buyer_id=? OR seller_id=?
                                ORDER BY id DESC LIMIT 50""", (user_id, user_id))
        realized = one(conn, "SELECT COALESCE(SUM(realized_cents),0) AS n FROM positions WHERE user_id=?",
                       (user_id,))["n"]

    positions, value, cost = [], 0, 0
    for r in rows:
        cur = prices.get(r["market_id"], {}).get(r["outcome_id"], int(r["last_price_cents"]))
        shares = int(r["shares"])
        mv = shares * cur
        value += mv
        cost += int(r["cost_cents"])
        positions.append({
            "id": r["id"], "market_id": r["market_id"], "question": r["question"],
            "emoji": r["emoji"], "market_status": r["market_status"], "category": r["category"],
            "outcome_id": r["outcome_id"], "outcome_name": r["outcome_name"],
            "shares": shares, "locked_shares": int(r["locked_shares"]),
            "avg_cents": round(int(r["cost_cents"]) / shares, 2) if shares else 0,
            "price_cents": cur,
            "value_cents": mv,
            "pnl_cents": mv - int(r["cost_cents"]),
            "realized_cents": int(r["realized_cents"]),
        })
    equity = int(user["balance_cents"]) + value
    return {
        "user": dict(user), "positions": positions,
        "open_orders": orders, "recent_trades": history,
        "summary": {
            "balance_cents": int(user["balance_cents"]),
            "positions_value_cents": value,
            "equity_cents": equity,
            "cost_basis_cents": cost,
            "unrealized_cents": value - cost,
            "realized_cents": int(realized),
        },
    }


def leaderboard(limit: int = 20) -> dict:
    """排行榜：已实现盈亏 + 未实现盈亏（按当前价）。"""
    with get_conn() as conn:
        users = many(conn, "SELECT id, handle, equity_seed, balance_cents FROM users WHERE role='trader'")
        rows = many(conn, """SELECT p.user_id, p.outcome_id, p.shares, p.cost_cents, p.realized_cents,
                                    o.last_price_cents
                             FROM positions p JOIN outcomes o ON o.id=p.outcome_id""")
    agg: dict[int, dict] = {}
    for u in users:
        agg[u["id"]] = {"user_id": u["id"], "handle": u["handle"],
                        "balance_cents": int(u["balance_cents"]),
                        "seed_cents": int(u["equity_seed"]), "realized_cents": 0,
                        "unrealized_cents": 0, "positions": 0}
    for r in rows:
        slot = agg.get(int(r["user_id"]))
        if not slot:
            continue
        slot["realized_cents"] += int(r["realized_cents"])
        if int(r["shares"]) > 0:
            slot["positions"] += 1
            slot["unrealized_cents"] += int(r["shares"]) * int(r["last_price_cents"]) - int(r["cost_cents"])
    for slot in agg.values():
        slot["equity_cents"] = slot["balance_cents"] + sum(
            int(p["shares"]) * int(p["last_price_cents"])
            for p in rows if int(p["user_id"]) == slot["user_id"] and int(p["shares"]) > 0)
        slot["pnl_cents"] = slot["equity_cents"] - slot["seed_cents"] if slot["seed_cents"] else 0
        slot["roi"] = round(slot["pnl_cents"] / slot["seed_cents"], 4) if slot["seed_cents"] else 0
    items = sorted(agg.values(), key=lambda x: -x["pnl_cents"])
    return {"items": items[:limit], "total": len(items)}


def platform_stats() -> dict:
    with get_conn() as conn:
        m = one(conn, """SELECT COUNT(*) AS markets,
                                SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) AS open_markets,
                                SUM(volume_cents) AS volume, SUM(trades_count) AS trades
                         FROM markets""")
        u = one(conn, "SELECT COUNT(*) AS users, SUM(balance_cents) AS balances FROM users")
        t = one(conn, "SELECT COUNT(*) AS n FROM trades")
        open_pos = one(conn, "SELECT COUNT(*) AS n FROM positions WHERE shares>0")
        day = one(conn, """SELECT COALESCE(SUM(notional_cents),0) AS vol, COUNT(*) AS n FROM trades
                           WHERE created_at >= datetime('now','localtime','-1 day')""")
        day_users = one(conn, """SELECT COUNT(DISTINCT uid) AS n FROM (
                                   SELECT buyer_id AS uid FROM trades WHERE created_at >= datetime('now','localtime','-1 day')
                                   UNION SELECT seller_id AS uid FROM trades WHERE created_at >= datetime('now','localtime','-1 day')
                                 )""")
    return {
        "markets": m["markets"] or 0, "open_markets": m["open_markets"] or 0,
        "volume_cents": m["volume"] or 0, "trades": m["trades"] or 0,
        "users": u["users"] or 0, "open_positions": open_pos["n"] or 0,
        "balance_cents": u["balances"] or 0,
        "volume_24h_cents": day["vol"] or 0, "trades_24h": day["n"] or 0,
        "active_traders_24h": day_users["n"] or 0,
    }
