"""市场生命周期：上架 → 停盘 → 结算 → 兑付"""
from conftest import call
from app.db import get_conn, one


def _new_market(app, admin_token, question="测试市场：会用这个市场验证结算逻辑吗？",
                outcomes=("会", "不会"), probs=None):
    body = {"question": question, "outcomes": list(outcomes), "category": "综合"}
    if probs:
        body["probs"] = probs
    status, mk = call(app, "POST", "/api/admin/markets", body, admin_token)
    assert status == 200, mk
    return mk


def test_permission_required(app, demo_token):
    status, _ = call(app, "POST", "/api/admin/markets",
                     {"question": "普通用户不能上架市场吗？", "outcomes": ["会", "不会"]},
                     demo_token)
    assert status == 403


def test_create_market_sets_initial_price(app, admin_token):
    mk = _new_market(app, admin_token, "初始概率测试：这个市场初始 70/30 吗？",
                     probs=[0.7, 0.3])
    _, d = call(app, "GET", f"/api/markets/{mk['id']}")
    prices = [o["price_cents"] for o in d["outcomes"]]
    assert abs(prices[0] - 70) <= 2 and sum(prices) == 100


def test_create_market_validation(app, admin_token):
    status, _ = call(app, "POST", "/api/admin/markets",
                     {"question": "短", "outcomes": ["会", "不会"]}, admin_token)
    assert status == 400
    status, _ = call(app, "POST", "/api/admin/markets",
                     {"question": "只有一个结果的市场应该被拒绝吗？", "outcomes": ["会"]},
                     admin_token)
    assert status == 400


def test_resolve_pays_winner(app, admin_token, fresh_user):
    mk = _new_market(app, admin_token, "结算兑付测试：赢家能拿到每份 1 美元吗？")
    _, d = call(app, "GET", f"/api/markets/{mk['id']}")
    oid = d["outcomes"][0]["id"]
    _, res = call(app, "POST", f"/api/markets/{mk['id']}/orders",
                  {"outcome_id": oid, "side": "buy", "order_type": "market",
                   "amount_cents": 50_00}, fresh_user["token"])
    shares = res["filled_qty"]
    assert shares > 0
    before = call(app, "GET", "/api/auth/me", token=fresh_user["token"])[1]["user"]["balance_cents"]

    status, pay = call(app, "POST", f"/api/admin/markets/{mk['id']}/resolve",
                       {"outcome_id": oid, "note": "按测试用例结算"}, admin_token)
    assert status == 200, pay
    assert pay["paid_cents"] >= shares * 100

    after = call(app, "GET", "/api/auth/me", token=fresh_user["token"])[1]["user"]["balance_cents"]
    assert after == before + shares * 100

    _, d2 = call(app, "GET", f"/api/markets/{mk['id']}")
    assert d2["status"] == "resolved"
    assert d2["resolution"]["outcome_id"] == oid
    assert [o["is_winner"] for o in d2["outcomes"]] == [True, False]


def test_resolve_loser_gets_nothing(app, admin_token, fresh_user):
    mk = _new_market(app, admin_token, "结算兑付测试：买错方向应该归零吗？")
    _, d = call(app, "GET", f"/api/markets/{mk['id']}")
    oid_lose = d["outcomes"][1]["id"]
    oid_win = d["outcomes"][0]["id"]
    call(app, "POST", f"/api/markets/{mk['id']}/orders",
         {"outcome_id": oid_lose, "side": "buy", "order_type": "market", "amount_cents": 30_00},
         fresh_user["token"])
    before = call(app, "GET", "/api/auth/me", token=fresh_user["token"])[1]["user"]["balance_cents"]
    call(app, "POST", f"/api/admin/markets/{mk['id']}/resolve",
         {"outcome_id": oid_win}, admin_token)
    after = call(app, "GET", "/api/auth/me", token=fresh_user["token"])[1]["user"]["balance_cents"]
    assert after == before
    _, pf = call(app, "GET", "/api/portfolio", token=fresh_user["token"])
    assert all(p["shares"] == 0 for p in pf["positions"] if p["market_id"] == mk["id"])


def test_double_resolve_rejected(app, admin_token):
    mk = _new_market(app, admin_token, "重复结算测试：同一个市场不能被结算两次吗？")
    _, d = call(app, "GET", f"/api/markets/{mk['id']}")
    oid = d["outcomes"][0]["id"]
    assert call(app, "POST", f"/api/admin/markets/{mk['id']}/resolve",
                {"outcome_id": oid}, admin_token)[0] == 200
    status, res = call(app, "POST", f"/api/admin/markets/{mk['id']}/resolve",
                       {"outcome_id": oid}, admin_token)
    assert status == 409


def test_resolve_cancels_open_orders(app, admin_token, fresh_user):
    mk = _new_market(app, admin_token, "结算撤单测试：结算时挂单要解冻吗？")
    _, d = call(app, "GET", f"/api/markets/{mk['id']}")
    oid = d["outcomes"][0]["id"]
    price = d["outcomes"][0]["price_cents"]
    before = call(app, "GET", "/api/auth/me", token=fresh_user["token"])[1]["user"]["balance_cents"]
    _, res = call(app, "POST", f"/api/markets/{mk['id']}/orders",
                  {"outcome_id": oid, "side": "buy", "order_type": "limit",
                   "price_cents": max(1, price - 25), "qty": 20}, fresh_user["token"])
    frozen = res["resting_qty"] * max(1, price - 25)
    call(app, "POST", f"/api/admin/markets/{mk['id']}/resolve",
         {"outcome_id": d["outcomes"][1]["id"]}, admin_token)
    after = call(app, "GET", "/api/auth/me", token=fresh_user["token"])[1]["user"]["balance_cents"]
    assert after >= before - 0 and abs(after - before) < frozen + 1


def test_reopen(app, admin_token):
    mk = _new_market(app, admin_token, "重新开盘测试：停盘之后还能恢复交易吗？")
    call(app, "POST", f"/api/admin/markets/{mk['id']}/close", {}, admin_token)
    status, _ = call(app, "POST", f"/api/admin/markets/{mk['id']}/reopen", {}, admin_token)
    assert status == 200
    _, d = call(app, "GET", f"/api/markets/{mk['id']}")
    assert d["status"] == "open"


def test_admin_stats(app, admin_token):
    status, data = call(app, "GET", "/api/admin/stats", token=admin_token)
    assert status == 200
    assert data["markets"] >= 5
    assert "fees_cents" in data and "recent_trades" in data


def test_audit_log(app, admin_token):
    status, data = call(app, "GET", "/api/admin/audit", token=admin_token)
    assert status == 200
    assert any(r["action"] == "market.create" for r in data["items"])


def test_freeze_user_blocks_login(app, admin_token, fresh_user):
    uid = fresh_user["user"]["id"]
    status, _ = call(app, "POST", f"/api/admin/users/{uid}/status", {"status": "frozen"}, admin_token)
    assert status == 200
    status, data = call(app, "POST", "/api/auth/login",
                        {"email": fresh_user["email"], "password": "pass12345"})
    assert status == 403
    call(app, "POST", f"/api/admin/users/{uid}/status", {"status": "active"}, admin_token)


def test_comments(app, demo_token):
    _, listing = call(app, "GET", "/api/markets")
    mid = listing["items"][0]["id"]
    status, _ = call(app, "POST", f"/api/markets/{mid}/comments", {"body": "这条评论来自测试用例"},
                     demo_token)
    assert status == 200
    _, data = call(app, "GET", f"/api/markets/{mid}/comments")
    assert any("测试用例" in c["body"] for c in data["items"])
    status, _ = call(app, "POST", f"/api/markets/{mid}/comments", {"body": "x"}, demo_token)
    assert status == 400


def test_watchlist(app, fresh_user):
    _, listing = call(app, "GET", "/api/markets")
    mid = listing["items"][0]["id"]
    status, d = call(app, "POST", f"/api/markets/{mid}/watch", {}, fresh_user["token"])
    assert status == 200 and d["watching"] is True
    _, wl = call(app, "GET", "/api/watchlist", token=fresh_user["token"])
    assert any(m["id"] == mid for m in wl["items"])
    call(app, "POST", f"/api/markets/{mid}/watch", {}, fresh_user["token"])
    _, wl2 = call(app, "GET", "/api/watchlist", token=fresh_user["token"])
    assert not any(m["id"] == mid for m in wl2["items"])
