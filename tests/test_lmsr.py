"""LMSR 数学：价格必须是概率、成本必须单调、取整不能凭空造钱。"""
import math

import pytest

from app.services import lmsr


def test_prices_sum_to_one():
    q = [0.0, 0.0]
    ps = lmsr.prices(q, 1000)
    assert abs(sum(ps) - 1.0) < 1e-9
    assert ps == [0.5, 0.5]


def test_prices_shift_with_q():
    q = [100.0, 0.0]
    ps = lmsr.prices(q, 1000)
    assert ps[0] > ps[1]
    assert abs(sum(ps) - 1.0) < 1e-9


def test_prices_cents_always_100():
    for q, b in [([0, 0], 500), ([300, -120], 800), ([0, 0, 0, 0], 1000),
                 ([50, 20, -30], 300)]:
        cents = lmsr.prices_cents(q, float(b))
        assert sum(cents) == 100, (q, b, cents)
        assert all(1 <= c <= 99 for c in cents), cents


def test_cost_is_increasing():
    q = [0.0, 0.0]
    c1 = lmsr.cost(q, 1000)
    c2 = lmsr.cost([10.0, 0.0], 1000)
    c3 = lmsr.cost([20.0, 0.0], 1000)
    assert c1 < c2 < c3


def test_buy_then_sell_roundtrip_costs_nothing():
    """同一状态下买 100 份再卖 100 份，成本应相互抵消（只差取整）。"""
    q = [0.0, 0.0]
    buy = lmsr.trade_cost_cents(q, 1000, 0, 100)
    q2 = [100.0, 0.0]
    sell = lmsr.trade_cost_cents(q2, 1000, 0, -100, ceil_buy=False)
    assert buy > 0 and sell < 0
    assert abs(buy + sell) <= 2      # 只允许整数分取整误差


def test_max_buy_qty_respects_budget():
    q = [0.0, 0.0]
    budget = 10_000           # $100
    qty = lmsr.max_buy_qty(q, 1000, 0, budget)
    assert qty > 0
    assert lmsr.trade_cost_cents(q, 1000, 0, qty) <= budget
    assert lmsr.trade_cost_cents(q, 1000, 0, qty + 1) > budget


def test_buying_pushes_price_up():
    q = [0.0, 0.0]
    p0 = lmsr.prices_cents(q, 500)[0]
    q2 = [200.0, 0.0]
    p1 = lmsr.prices_cents(q2, 500)[0]
    assert p1 > p0


def test_depth_parameter_dampens_moves():
    small_b = lmsr.prices_cents([100.0, 0.0], 200)[0]
    big_b = lmsr.prices_cents([100.0, 0.0], 5000)[0]
    assert small_b > big_b      # 深度越小，同样的成交量推价越猛


def test_bad_b_rejected():
    with pytest.raises(ValueError):
        lmsr.prices([0, 0], 0)


def test_multi_outcome_probabilities():
    q = [0.0, 0.0, 0.0, 0.0]
    cents = lmsr.prices_cents(q, 1000)
    assert sum(cents) == 100
    assert len(set(cents)) <= 2       # 均等市场，价格应几乎一致


def test_max_loss_bounded():
    assert lmsr.max_loss([0, 0], 1000) == pytest.approx(1000 * math.log(2))
