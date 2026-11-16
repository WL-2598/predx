"""LMSR（Logarithmic Market Scoring Rule）做市商定价。

为什么选 LMSR 而不是纯订单簿：
  · 纯订单簿在冷启动市场里根本没人挂单，价格是空的 —— 客户第一眼就流失
  · LMSR 保证任何时候都有对手方、价格永远落在 (0,1)、且有解析解
  · 数学公开可审计：成本函数 C(q) = b·ln(Σ exp(q_i/b))，边际价格 = softmax(q/b)

代价：做市商承担最大亏损 b·ln(n)（有界），所以 b 必须按市场深度设定。

单位约定：
  · q_i   —— 已卖出的第 i 个结果的「份」数（浮点，内部状态）
  · b     —— 流动性深度（份），越大价格越稳
  · 价格用「分」表示：1 分 = 1% 概率
  · 1 份合约到期兑付 100 分
"""
from __future__ import annotations

import math

from ..config import config


def prices(q: list[float], b: float) -> list[float]:
    """边际价格（概率），返回归一化后的概率列表。"""
    if b <= 0:
        raise ValueError("流动性 b 必须为正")
    m = max(qi / b for qi in q)
    exps = [math.exp(qi / b - m) for qi in q]
    total = sum(exps)
    return [e / total for e in exps]


def prices_cents(q: list[float], b: float) -> list[int]:
    """价格转成整数分，且保证每个结果 ≥1 分、总和为 100 分。"""
    ps = prices(q, b)
    raw = [p * 100 for p in ps]
    cents = [max(config.PRICE_MIN, min(config.PRICE_MAX, int(round(r)))) for r in raw]
    # 调整总和到 100（多的从最大项扣，少的加给最大项）
    diff = 100 - sum(cents)
    if diff:
        idx = max(range(len(cents)), key=lambda i: cents[i])
        cents[idx] = max(config.PRICE_MIN, min(config.PRICE_MAX, cents[idx] + diff))
    return cents


def cost(q: list[float], b: float) -> float:
    """成本函数 C(q) = b·ln(Σ exp(q_i/b))，单位：份（×100 = 分）。"""
    m = max(qi / b for qi in q)
    return b * (m + math.log(sum(math.exp(qi / b - m) for qi in q)))


def trade_cost(q: list[float], b: float, outcome_idx: int, delta: float) -> float:
    """买入 delta 份（delta<0 表示卖出）需要支付的成本，单位：份。"""
    after = list(q)
    after[outcome_idx] += delta
    return cost(after, b) - cost(q, b)


def trade_cost_cents(q: list[float], b: float, idx: int, delta: float, ceil_buy: bool = True) -> int:
    """成本换算成整数分。买入向上取整、卖出向下取整，防止套利整数残留。"""
    c = trade_cost(q, b, idx, delta) * 100.0
    return int(math.ceil(c - 1e-9)) if ceil_buy else int(math.floor(c + 1e-9))


def max_buy_qty(q: list[float], b: float, idx: int, budget_cents: int) -> int:
    """预算内最多能买多少份（二分，LMSR 单调）。"""
    if budget_cents <= 0:
        return 0
    lo, hi = 0, 1
    # 先把上限指数扩张到预算不足为止
    while trade_cost_cents(q, b, idx, hi) <= budget_cents and hi < 10 ** 9:
        hi *= 2
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if trade_cost_cents(q, b, idx, mid) <= budget_cents:
            lo = mid
        else:
            hi = mid - 1
    return lo


def max_loss(q: list[float], b: float) -> float:
    """做市商在该市场的最坏亏损（份）。用于风控与展示。"""
    return b * math.log(len(q))


def implied_probability_label(price_cents: int) -> str:
    return f"{price_cents}%"
