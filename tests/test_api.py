"""HTTP 接口与权限"""
from conftest import call


def test_health_open(app):
    status, data = call(app, "GET", "/api/markets/stats")
    assert status == 200
    assert data["markets"] >= 5
    assert data["open_markets"] >= 3


def test_register_login_me(app, fresh_user):
    assert fresh_user["user"]["balance_cents"] == 10_000_00
    status, me = call(app, "GET", "/api/auth/me", token=fresh_user["token"])
    assert status == 200
    assert me["user"]["handle"] == "测试员"
    assert me["stats"]["open_positions"] == 0


def test_duplicate_email_rejected(app, fresh_user):
    status, _ = call(app, "POST", "/api/auth/register",
                     {"email": fresh_user["email"], "password": "pass12345"})
    assert status == 409


def test_weak_password_rejected(app):
    status, _ = call(app, "POST", "/api/auth/register",
                     {"email": "weak@test.io", "password": "123"})
    assert status == 400


def test_bad_login(app):
    status, data = call(app, "POST", "/api/auth/login",
                        {"email": "demo@predx.io", "password": "wrong"})
    assert status == 401


def test_protected_requires_token(app):
    status, _ = call(app, "GET", "/api/portfolio")
    assert status == 401


def test_markets_list_and_filter(app):
    status, data = call(app, "GET", "/api/markets")
    assert status == 200 and data["total"] >= 5
    for m in data["items"]:
        assert len(m["outcomes"]) >= 2
        assert sum(o["price_cents"] for o in m["outcomes"]) == 100
    status, crypto = call(app, "GET", "/api/markets", query={"category": "加密"})
    assert status == 200
    assert all(m["category"] == "加密" for m in crypto["items"])


def test_markets_search(app):
    status, data = call(app, "GET", "/api/markets", query={"q": "降息"})
    assert status == 200
    assert data["total"] >= 1


def test_market_detail_has_books(app):
    _, listing = call(app, "GET", "/api/markets")
    mid = listing["items"][0]["id"]
    status, d = call(app, "GET", f"/api/markets/{mid}")
    assert status == 200
    assert d["books"]
    first = d["outcomes"][0]["id"]
    book = d["books"][str(first)]
    assert book["asks"] and book["bids"]
    assert book["best_ask_cents"] > book["best_bid_cents"]


def test_market_404(app):
    status, _ = call(app, "GET", "/api/markets/999999")
    assert status == 404


def test_history_series(app):
    _, listing = call(app, "GET", "/api/markets")
    mid = listing["items"][0]["id"]
    status, data = call(app, "GET", f"/api/markets/{mid}/history")
    assert status == 200
    assert data["series"]
    pts = next(iter(data["series"].values()))
    assert len(pts) >= 2
    assert all(0 <= p["price_cents"] <= 100 for p in pts)


def test_quote_buy(app):
    _, listing = call(app, "GET", "/api/markets")
    mid = listing["items"][0]["id"]
    _, d = call(app, "GET", f"/api/markets/{mid}")
    oid = d["outcomes"][0]["id"]
    status, q = call(app, "POST", f"/api/markets/{mid}/quote",
                     {"outcome_id": oid, "side": "buy", "amount_cents": 50_000})
    assert status == 200
    assert q["qty"] > 0
    assert q["fee_cents"] >= 1
    assert q["payout_if_win_cents"] == q["qty"] * 100
    assert q["price_after_cents"] >= q["mid_cents"]


def test_leaderboard(app):
    status, data = call(app, "GET", "/api/leaderboard")
    assert status == 200 and data["items"]
    pnls = [i["pnl_cents"] for i in data["items"]]
    assert pnls == sorted(pnls, reverse=True)


def test_change_password(app, fresh_user):
    status, _ = call(app, "POST", "/api/auth/change-password",
                     {"old_password": "pass12345", "new_password": "newpass12345"},
                     fresh_user["token"])
    assert status == 200
    status, _ = call(app, "POST", "/api/auth/login",
                     {"email": fresh_user["email"], "password": "newpass12345"})
    assert status == 200


def test_book_is_tight_around_mid(app):
    """盘口必须围绕中间价：买一 < 中间价 < 卖一，且价差合理。"""
    _, listing = call(app, "GET", "/api/markets")
    mid_id = listing["items"][0]["id"]
    _, d = call(app, "GET", f"/api/markets/{mid_id}")
    for o in d["outcomes"]:
        b = d["books"][str(o["id"])]
        # mid 是取整后的价格，允许 ±1.5 分的容差
        assert 0 < b["best_bid_cents"] < b["best_ask_cents"] < 100
        assert b["best_bid_cents"] <= b["mid_cents"] + 1.5
        assert b["best_ask_cents"] >= b["mid_cents"] - 1.5
        assert b["spread_cents"] < 12
        assert b["asks"] and b["bids"]
        # 卖价逐档递增、买价逐档递减
        asks = [a["price_cents"] for a in b["asks"] if a["src"] == "amm"]
        bids = [x["price_cents"] for x in b["bids"] if x["src"] == "amm"]
        assert asks == sorted(asks) and bids == sorted(bids, reverse=True)
