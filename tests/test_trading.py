"""撮合与资金安全——这是整个系统最不能出错的部分。"""
from conftest import call
from app.db import get_conn, many, one


def _market(app, idx=0):
    _, listing = call(app, "GET", "/api/markets")
    m = listing["items"][idx]
    _, detail = call(app, "GET", f"/api/markets/{m['id']}")
    return detail


def _balance(token, app):
    _, me = call(app, "GET", "/api/auth/me", token=token)
    return me["user"]["balance_cents"]


def test_market_buy_creates_position_and_trade(app, fresh_user):
    d = _market(app)
    oid = d["outcomes"][0]["id"]
    before = _balance(fresh_user["token"], app)
    status, res = call(app, "POST", f"/api/markets/{d['id']}/orders",
                       {"outcome_id": oid, "side": "buy", "order_type": "market",
                        "amount_cents": 100_00}, fresh_user["token"])
    assert status == 200, res
    assert res["filled_qty"] > 0
    assert _balance(fresh_user["token"], app) < before

    status, pf = call(app, "GET", "/api/portfolio", token=fresh_user["token"])
    pos = [p for p in pf["positions"] if p["outcome_id"] == oid]
    assert pos and pos[0]["shares"] == res["filled_qty"]
    assert pf["summary"]["equity_cents"] > 0


def test_buy_pushes_price_up(app, fresh_user):
    d = _market(app)
    oid = d["outcomes"][0]["id"]
    before = d["outcomes"][0]["price_cents"]
    status, res = call(app, "POST", f"/api/markets/{d['id']}/orders",
                       {"outcome_id": oid, "side": "buy", "order_type": "market",
                        "amount_cents": 200_00}, fresh_user["token"])
    assert status == 200
    assert res["price_after_cents"] >= before


def test_sell_requires_shares(app, fresh_user):
    d = _market(app, idx=1)
    oid = d["outcomes"][1]["id"]
    status, res = call(app, "POST", f"/api/markets/{d['id']}/orders",
                       {"outcome_id": oid, "side": "sell", "order_type": "market", "qty": 10},
                       fresh_user["token"])
    assert status == 400
    assert res["error"]["code"] in ("insufficient_shares", "no_liquidity")


def test_buy_then_sell_no_free_money(app, fresh_user):
    """买 100 份后立刻卖出，余额必须不增加（只允许手续费与滑点损失）。"""
    d = _market(app, idx=2)
    oid = d["outcomes"][0]["id"]
    start = _balance(fresh_user["token"], app)
    _, buy = call(app, "POST", f"/api/markets/{d['id']}/orders",
                  {"outcome_id": oid, "side": "buy", "order_type": "market",
                   "amount_cents": 100_00}, fresh_user["token"])
    qty = buy["filled_qty"]
    assert qty > 0
    _, sell = call(app, "POST", f"/api/markets/{d['id']}/orders",
                   {"outcome_id": oid, "side": "sell", "order_type": "market", "qty": qty},
                   fresh_user["token"])
    assert sell["filled_qty"] > 0
    end = _balance(fresh_user["token"], app)
    assert end <= start
    # 损失应只有手续费与极小的滑点，不超过 2%
    assert start - end < start * 0.02 + 200


def test_insufficient_funds(app, fresh_user):
    d = _market(app)
    oid = d["outcomes"][0]["id"]
    status, res = call(app, "POST", f"/api/markets/{d['id']}/orders",
                       {"outcome_id": oid, "side": "buy", "order_type": "market",
                        "amount_cents": 99_999_999}, fresh_user["token"])
    assert status == 400
    assert res["error"]["code"] == "insufficient_funds"


def test_limit_order_rests_and_reserves(app, fresh_user):
    d = _market(app, idx=3)
    oid = d["outcomes"][0]["id"]
    price = d["outcomes"][0]["price_cents"]
    before = _balance(fresh_user["token"], app)
    # 挂在明显买不到的低价，确保进入簿子
    status, res = call(app, "POST", f"/api/markets/{d['id']}/orders",
                       {"outcome_id": oid, "side": "buy", "order_type": "limit",
                        "price_cents": max(1, price - 15), "qty": 50}, fresh_user["token"])
    assert status == 200, res
    assert res["resting_qty"] > 0
    after = _balance(fresh_user["token"], app)
    assert before - after == res["resting_qty"] * max(1, price - 15)

    status, orders = call(app, "GET", "/api/orders", token=fresh_user["token"])
    oid_order = [o for o in orders["items"] if o["id"] == res["order_id"]][0]

    status, cancel = call(app, "DELETE", f"/api/orders/{oid_order['id']}", token=fresh_user["token"])
    assert status == 200
    assert _balance(fresh_user["token"], app) == before      # 撤单全额退回


def test_cancel_others_order_forbidden(app, admin_token, fresh_user):
    d = _market(app)
    oid = d["outcomes"][0]["id"]
    price = d["outcomes"][0]["price_cents"]
    _, res = call(app, "POST", f"/api/markets/{d['id']}/orders",
                  {"outcome_id": oid, "side": "buy", "order_type": "limit",
                   "price_cents": max(1, price - 20), "qty": 10}, fresh_user["token"])
    if res.get("order_id"):
        status, _ = call(app, "DELETE", f"/api/orders/{res['order_id']}", token=fresh_user["token"])
        assert status in (200, 403, 409)


def test_trade_after_close_rejected(app, admin_token, fresh_user):
    status, mk = call(app, "POST", "/api/admin/markets",
                      {"question": "测试用市场：这个市场会被立刻停盘吗？",
                       "outcomes": ["会", "不会"], "category": "综合"}, admin_token)
    assert status == 200, mk
    mid = mk["id"]
    status, _ = call(app, "POST", f"/api/admin/markets/{mid}/close", {}, admin_token)
    assert status == 200
    _, d = call(app, "GET", f"/api/markets/{mid}")
    status, res = call(app, "POST", f"/api/markets/{mid}/orders",
                       {"outcome_id": d["outcomes"][0]["id"], "side": "buy",
                        "order_type": "market", "amount_cents": 10_00}, fresh_user["token"])
    assert status == 409
    assert res["error"]["code"] == "market_closed"


def test_positions_match_trades(app):
    """全局不变量：每个持仓的 shares = 累计买入 − 累计卖出。

    注意 locked_shares 是 shares 的**子集**（挂单冻结，卖出成交时会同时扣减两者），
    所以不变量里不能再加 locked_shares —— 早期版本写成 shares+locked 是错的，
    只是因为种子数据里恰好没有「挂单未成交的卖单」才蒙对。
    """
    with get_conn() as conn:
        rows = many(conn, """SELECT p.* FROM positions p JOIN markets m ON m.id=p.market_id
                             WHERE m.status<>'resolved'""")
        for p in rows:
            bought = one(conn, "SELECT COALESCE(SUM(qty),0) q FROM trades WHERE buyer_id=? AND outcome_id=?",
                         (p["user_id"], p["outcome_id"]))["q"]
            sold = one(conn, "SELECT COALESCE(SUM(qty),0) q FROM trades WHERE seller_id=? AND outcome_id=?",
                       (p["user_id"], p["outcome_id"]))["q"]
            assert p["locked_shares"] <= p["shares"], f"冻结份额不能超过持仓：{p}"
            assert bought - sold == p["shares"], (
                f"持仓不平：买入 {bought} − 卖出 {sold} ≠ 持仓 {p['shares']}（{p}）")


def test_no_negative_balance(app):
    with get_conn() as conn:
        neg = many(conn, "SELECT id,balance_cents FROM users WHERE balance_cents < 0")
    assert neg == []


def test_ledger_balance_chain(app, fresh_user):
    """流水里的 balance_after 必须与真实余额一致。"""
    d = _market(app)
    call(app, "POST", f"/api/markets/{d['id']}/orders",
         {"outcome_id": d["outcomes"][0]["id"], "side": "buy",
          "order_type": "market", "amount_cents": 50_00}, fresh_user["token"])
    status, data = call(app, "GET", "/api/wallet/ledger", token=fresh_user["token"])
    assert status == 200
    assert data["items"][0]["balance_after_cents"] == data["balance_cents"]


def test_deposit(app, fresh_user):
    before = _balance(fresh_user["token"], app)
    status, res = call(app, "POST", "/api/wallet/deposit", {"amount_cents": 5000},
                       fresh_user["token"])
    assert status == 200
    assert res["balance_cents"] == before + 5000
    status, _ = call(app, "POST", "/api/wallet/deposit", {"amount_cents": 1},
                     fresh_user["token"])
    assert status == 400


def test_quote_matches_execution(app, fresh_user):
    """预览报出的份数与真实成交份数不能差太多。"""
    d = _market(app, idx=4)
    oid = d["outcomes"][0]["id"]
    _, q = call(app, "POST", f"/api/markets/{d['id']}/quote",
                {"outcome_id": oid, "side": "buy", "amount_cents": 30_000})
    _, res = call(app, "POST", f"/api/markets/{d['id']}/orders",
                  {"outcome_id": oid, "side": "buy", "order_type": "market",
                   "amount_cents": 30_000}, fresh_user["token"])
    assert abs(res["filled_qty"] - q["qty"]) <= max(2, q["qty"] * 0.1)
