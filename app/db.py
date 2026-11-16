"""数据库访问层：连接管理 + 迁移 + 仓储工具。

交易系统对一致性的要求比普通 CRUD 高：撮合必须在一个事务里完成
（扣钱、记账、成交、持仓、行情快照要么全成要么全不成）。因此这里
提供 transaction() 上下文，并且所有撮合入口都必须经过它。
"""
import sqlite3
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from .config import config

_APP_DIR = Path(__file__).resolve().parent
MIGRATIONS = [("0001_init", _APP_DIR / "schema.sql")]


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(
        str(config.DB_PATH),
        timeout=30,
        check_same_thread=False,
        isolation_level=None,          # 自己控制事务
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 8000")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction():
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()


def migrate() -> list[str]:
    """按顺序应用未执行的迁移，返回本次应用的版本列表。"""
    applied = []
    with get_conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        done = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
        for version, sql_path in MIGRATIONS:
            if version in done:
                continue
            sql = Path(sql_path).read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES(?,?)", (version, now())
            )
            applied.append(version)
    return applied


# ------------------------------------------------------------------ 仓储工具
def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


def one(conn, sql: str, params: tuple = ()) -> dict | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def many(conn, sql: str, params: tuple = ()) -> list[dict]:
    return rows_to_dicts(conn.execute(sql, params).fetchall())


def insert(conn, table: str, data: dict[str, Any]) -> int:
    cols = ", ".join(data.keys())
    ph = ", ".join("?" for _ in data)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph})", tuple(data.values()))
    return int(cur.lastrowid)


def update(conn, table: str, row_id: int, data: dict[str, Any]) -> None:
    if not data:
        return
    sets = ", ".join(f"{k}=?" for k in data)
    conn.execute(f"UPDATE {table} SET {sets} WHERE id=?", (*data.values(), row_id))


def jloads(value, default=None):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def jdumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def get_setting(conn, key: str, default: str | None = None) -> str | None:
    r = one(conn, "SELECT value FROM settings WHERE key=?", (key,))
    return r["value"] if r else default


def set_setting(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
