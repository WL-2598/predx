"""装配层：路由 + 身份解析 + 静态资源。"""
from __future__ import annotations

from . import api
from .config import config
from .db import get_conn, now, one, update
from .http import Application, Request, Router, serve
from .security import hash_api_key, verify_jwt


def resolve_principal(req: Request) -> dict | None:
    token = req.token
    if token:
        payload = verify_jwt(token)
        if not payload:
            return None
        with get_conn() as conn:
            user = one(conn, "SELECT id,email,handle,role,status FROM users WHERE id=?",
                       (payload.get("sub"),))
        if not user or user["status"] != "active":
            return None
        return {"user_id": user["id"], "email": user["email"], "handle": user["handle"],
                "role": user["role"], "status": user["status"], "via": "jwt"}

    raw = req.api_key
    if raw:
        with get_conn() as conn:
            row = one(conn, """SELECT k.*, u.email, u.handle, u.role, u.status
                               FROM api_keys k JOIN users u ON u.id=k.user_id
                               WHERE k.key_hash=? AND k.revoked=0""", (hash_api_key(raw),))
            if not row or row["status"] != "active":
                return None
            update(conn, "api_keys", row["id"], {"last_used_at": now()})
        return {"user_id": row["user_id"], "email": row["email"], "handle": row["handle"],
                "role": row["role"], "status": row["status"], "via": "api_key"}
    return None


def build_app() -> Application:
    router = Router()
    api.register_routes(router)
    app = Application(router, config.STATIC_DIR)
    app.resolve_principal = staticmethod(resolve_principal)
    return app


def create_server():
    from .seed import bootstrap
    print(f"初始化 {config.APP_NAME} v{config.VERSION} …")
    bootstrap()
    return build_app()


def run() -> None:
    app = create_server()
    serve(app, config.HOST, config.PORT)
