#!/usr/bin/env python3
"""PredX 运维命令行（零依赖）。

常用操作不依赖 HTTP，直接操作数据库，适合内网运维与演示准备：

    python3 manage.py init                     # 初始化/补齐演示数据
    python3 manage.py reset --yes              # 清库重建（会删除所有数据）
    python3 manage.py stats                    # 平台概览
    python3 manage.py markets --status open    # 市场列表
    python3 manage.py resolve --market 7 --outcome 13 --note "官方公告"
    python3 manage.py deposit --email demo@predx.io --amount 1000
    python3 manage.py freeze --email x@y.com --status frozen
    python3 manage.py verify                   # 系统级不变量对账
    python3 manage.py sql "SELECT id, question FROM markets LIMIT 5"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import config                       # noqa: E402
from app.db import get_conn, insert, many, migrate, now, one, transaction  # noqa: E402


def _money(cents) -> str:
    return f"${(cents or 0) / 100:,.2f}"


def cmd_init(args) -> int:
    from app.seed import bootstrap
    bootstrap()
    return 0


def cmd_reset(args) -> int:
    if not args.yes:
        print("这会删除全部数据。确认请加 --yes")
        return 1
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(config.DB_PATH) + suffix)
        if p.exists():
            p.unlink()
    applied = migrate()
    print(f"已重建数据库：{config.DB_PATH}（迁移 {applied or '无'}）")
    if not args.empty:
        from app.seed import bootstrap
        bootstrap()
    return 0


def cmd_stats(args) -> int:
    with get_conn() as conn:
        m = one(conn, """SELECT COUNT(*) n, SUM(status='open') open_n, SUM(volume_cents) vol,
                                SUM(trades_count) trades FROM markets""")
        u = one(conn, "SELECT COUNT(*) n, SUM(balance_cents) bal FROM users")
        t = one(conn, "SELECT COUNT(*) n, COALESCE(SUM(fee_cents),0) fees FROM trades")
        p = one(conn, "SELECT COUNT(*) n FROM positions WHERE shares>0")
    print(f"市场      {m['n']} 个（进行中 {m['open_n'] or 0}）")
    print(f"成交额    {_money(m['vol'])}（{m['trades'] or 0} 笔）")
    print(f"成交明细  {t['n']} 条，手续费收入 {_money(t['fees'])}")
    print(f"用户      {u['n']} 人，虚拟资金余额合计 {_money(u['bal'])}")
    print(f"未平仓    {p['n']} 个持仓")
    print(f"数据库    {config.DB_PATH}")
    return 0


def cmd_markets(args) -> int:
    with get_conn() as conn:
        where, params = "", ()
        if args.status:
            where, params = "WHERE status=?", (args.status,)
        rows = many(conn, f"""SELECT id, status, category, question, volume_cents, trades_count,
                                     closes_at FROM markets {where} ORDER BY id""", params)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    for r in rows:
        print(f"#{r['id']:>3} [{r['status']:<8}] {r['category']} | {r['question'][:44]:<44} "
              f"成交 {_money(r['volume_cents']):>12} | {r['trades_count']:>3} 笔 | 截止 {r['closes_at'] or '—'}")
    return 0


def cmd_resolve(args) -> int:
    from app.services import engine
    try:
        r = engine.resolve_market(args.market, args.outcome, args.note or "", by=None)
    except engine.TradeError as e:
        print("失败：", e.message)
        return 1
    print(f"市场 #{args.market} 已结算：赢家结果 {args.outcome}，兑付 {_money(r['paid_cents'])}，"
          f"涉及持仓 {r.get('positions_paid', r.get('positions', '—'))}")
    return 0


def cmd_reopen(args) -> int:
    with get_conn() as conn:
        m = one(conn, "SELECT id, status FROM markets WHERE id=?", (args.market,))
        if not m:
            print("市场不存在")
            return 1
        conn.execute("UPDATE markets SET status='open', closed_at=NULL WHERE id=?", (args.market,))
    print(f"市场 #{args.market} 已复牌（原状态 {m['status']}）")
    return 0


def cmd_close(args) -> int:
    with get_conn() as conn:
        conn.execute("UPDATE markets SET status='closed', closed_at=? WHERE id=?", (now(), args.market))
    print(f"市场 #{args.market} 已停盘")
    return 0


def cmd_deposit(args) -> int:
    amount = int(round(float(args.amount) * 100))
    with transaction() as conn:
        u = one(conn, "SELECT id, handle, balance_cents FROM users WHERE email=?", (args.email,))
        if not u:
            print("用户不存在：", args.email)
            return 1
        conn.execute("UPDATE users SET balance_cents=balance_cents+? WHERE id=?", (amount, u["id"]))
        bal = one(conn, "SELECT balance_cents FROM users WHERE id=?", (u["id"],))["balance_cents"]
        insert(conn, "ledger", {"user_id": u["id"], "kind": "deposit", "delta_cents": amount,
                                "balance_after_cents": bal, "market_id": None, "ref": "cli",
                                "note": "运维充值（虚拟资金）", "created_at": now()})
    print(f"{u['handle']} 充值 {_money(amount)}，余额 {_money(bal)}")
    return 0


def cmd_freeze(args) -> int:
    with transaction() as conn:
        u = one(conn, "SELECT id, handle FROM users WHERE email=?", (args.email,))
        if not u:
            print("用户不存在：", args.email)
            return 1
        conn.execute("UPDATE users SET status=? WHERE id=?", (args.status, u["id"]))
    print(f"{u['handle']} 状态改为 {args.status}")
    return 0


def cmd_verify(args) -> int:
    """对账：跑一遍系统级不变量，任何一条不成立就返回非 0。"""
    problems = []
    with get_conn() as conn:
        # 1) 每个未结算市场 Σ 价格 = 100
        for m in many(conn, "SELECT id, question FROM markets WHERE status='open'"):
            outs = many(conn, "SELECT last_price_cents FROM outcomes WHERE market_id=?", (m["id"],))
            total = sum(int(o["last_price_cents"]) for o in outs)
            if outs and total != 100:
                problems.append(f"市场 #{m['id']} 价格合计 {total} ≠ 100")
        # 2) 持仓 = 买入 − 卖出；冻结 ≤ 持仓
        for p in many(conn, """SELECT p.* FROM positions p JOIN markets m ON m.id=p.market_id
                               WHERE m.status<>'resolved' AND (p.shares>0 OR p.locked_shares>0)"""):
            bought = one(conn, "SELECT COALESCE(SUM(qty),0) q FROM trades WHERE buyer_id=? AND outcome_id=?",
                         (p["user_id"], p["outcome_id"]))["q"]
            sold = one(conn, "SELECT COALESCE(SUM(qty),0) q FROM trades WHERE seller_id=? AND outcome_id=?",
                       (p["user_id"], p["outcome_id"]))["q"]
            if bought - sold != p["shares"]:
                problems.append(f"持仓不平 user={p['user_id']} outcome={p['outcome_id']}: "
                                f"{bought}-{sold}≠{p['shares']}")
            if p["locked_shares"] > p["shares"]:
                problems.append(f"冻结超持仓 user={p['user_id']} outcome={p['outcome_id']}")
        # 3) 余额非负
        for u in many(conn, "SELECT id, handle, balance_cents FROM users WHERE balance_cents<0"):
            problems.append(f"用户 {u['handle']} 余额为负：{u['balance_cents']}")
        # 4) 每笔成交金额自洽
        bad = one(conn, """SELECT COUNT(*) n FROM trades
                           WHERE notional_cents <> price_cents * qty""")["n"]
        if bad:
            problems.append(f"{bad} 笔成交的 notional ≠ price × qty")
        # 5) 账本余额与用户余额一致（最后一条流水）
        for u in many(conn, "SELECT id, handle, balance_cents FROM users"):
            last = one(conn, """SELECT balance_after_cents FROM ledger WHERE user_id=?
                                ORDER BY id DESC LIMIT 1""", (u["id"],))
            if last and int(last["balance_after_cents"]) != int(u["balance_cents"]):
                problems.append(f"用户 {u['handle']} 余额 {u['balance_cents']} 与流水末值 "
                                f"{last['balance_after_cents']} 不一致")

    if problems:
        print(f"✗ 发现 {len(problems)} 个问题：")
        for x in problems[:40]:
            print("  ·", x)
        return 1
    print("✓ 全部不变量成立：价格合计、持仓守恒、余额非负、成交金额、流水对账")
    return 0


def cmd_sql(args) -> int:
    with get_conn() as conn:
        rows = many(conn, args.query)
    for r in rows:
        print(" | ".join("" if v is None else str(v) for v in r.values()))
    print(f"（{len(rows)} 行）")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="PredX 运维命令行")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="初始化/补齐演示数据")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("reset", help="清库重建")
    s.add_argument("--yes", action="store_true")
    s.add_argument("--empty", action="store_true", help="只建表，不灌演示数据")
    s.set_defaults(func=cmd_reset)

    s = sub.add_parser("stats", help="平台概览")
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("markets", help="市场列表")
    s.add_argument("--status", default="open")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_markets)

    s = sub.add_parser("resolve", help="结算市场")
    s.add_argument("--market", type=int, required=True)
    s.add_argument("--outcome", type=int, required=True)
    s.add_argument("--note", default="")
    s.set_defaults(func=cmd_resolve)

    s = sub.add_parser("close", help="停盘")
    s.add_argument("--market", type=int, required=True)
    s.set_defaults(func=cmd_close)

    s = sub.add_parser("reopen", help="复牌")
    s.add_argument("--market", type=int, required=True)
    s.set_defaults(func=cmd_reopen)

    s = sub.add_parser("deposit", help="给用户充值体验金（美元）")
    s.add_argument("--email", required=True)
    s.add_argument("--amount", default="1000")
    s.set_defaults(func=cmd_deposit)

    s = sub.add_parser("freeze", help="冻结/解冻用户")
    s.add_argument("--email", required=True)
    s.add_argument("--status", choices=("active", "frozen"), default="frozen")
    s.set_defaults(func=cmd_freeze)

    s = sub.add_parser("verify", help="跑一遍对账不变量")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("sql", help="执行只读 SQL")
    s.add_argument("query")
    s.set_defaults(func=cmd_sql)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
