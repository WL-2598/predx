"""审计日志：交易系统里，谁在什么时候下了什么单必须有据可查。"""
from ..db import insert, jdumps, now


def log(conn, user_id, action: str, target: str | None = None,
        meta: dict | None = None, ip: str = "") -> None:
    try:
        insert(conn, "audit_logs", {
            "user_id": user_id, "action": action, "target": target,
            "meta": jdumps(meta) if meta else None, "ip": ip, "created_at": now(),
        })
    except Exception:
        pass
