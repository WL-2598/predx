"""认证与账户：注册即送体验金（虚拟资金）。"""
from ..config import config
from ..db import get_conn, insert, many, now, one, update
from ..http import Request, RequestError, Unauthorized
from ..security import hash_password, sign_jwt, valid_email, verify_password
from ..services.audit import log


def public_user(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "handle": u["handle"], "role": u["role"],
            "status": u["status"], "balance_cents": u["balance_cents"],
            "created_at": u["created_at"], "last_login_at": u["last_login_at"]}


def login(req: Request):
    body = req.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        raise RequestError(400, "邮箱和密码不能为空")
    with get_conn() as conn:
        user = one(conn, "SELECT * FROM users WHERE email=?", (email,))
        if not user or not verify_password(password, user["password_hash"]):
            log(conn, user["id"] if user else None, "auth.login_failed", email, None, req.ip)
            raise Unauthorized("邮箱或密码不正确")
        if user["status"] != "active":
            raise RequestError(403, "账号已被冻结", "account_frozen")
        update(conn, "users", user["id"], {"last_login_at": now()})
        log(conn, user["id"], "auth.login", email, None, req.ip)
    token = sign_jwt({"sub": user["id"], "role": user["role"], "email": email})
    return {"token": token, "user": public_user(user)}


def register(req: Request):
    if not config.ALLOW_REGISTRATION:
        raise RequestError(403, "管理员已关闭自助注册", "registration_disabled")
    body = req.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    handle = (body.get("handle") or email.split("@")[0] or "交易员").strip()[:24]
    if not valid_email(email):
        raise RequestError(400, "邮箱格式不正确", "invalid_email")
    if len(password) < 8:
        raise RequestError(400, "密码至少 8 位", "weak_password")
    with get_conn() as conn:
        if one(conn, "SELECT id FROM users WHERE email=?", (email,)):
            raise RequestError(409, "该邮箱已注册", "email_exists")
        bonus = config.SIGNUP_BONUS_CENTS
        uid = insert(conn, "users", {
            "email": email, "handle": handle, "password_hash": hash_password(password),
            "role": "trader", "status": "active", "balance_cents": bonus,
            "equity_seed": bonus, "created_at": now(),
        })
        insert(conn, "ledger", {"user_id": uid, "kind": "signup", "delta_cents": bonus,
                                "balance_after_cents": bonus, "market_id": None, "ref": None,
                                "note": "注册体验金", "created_at": now()})
        log(conn, uid, "auth.register", email, {"handle": handle}, req.ip)
        user = one(conn, "SELECT * FROM users WHERE id=?", (uid,))
    token = sign_jwt({"sub": uid, "role": "trader", "email": email})
    return {"token": token, "user": public_user(user)}


def me(req: Request):
    with get_conn() as conn:
        user = one(conn, "SELECT * FROM users WHERE id=?", (req.user["user_id"],))
        if not user:
            raise Unauthorized()
        pos = one(conn, "SELECT COUNT(*) AS n, COALESCE(SUM(shares),0) AS s FROM positions "
                        "WHERE user_id=? AND shares>0", (user["id"],))
        orders = one(conn, "SELECT COUNT(*) AS n FROM orders WHERE user_id=? AND status='open'",
                     (user["id"],))
    return {"user": public_user(user),
            "stats": {"open_positions": pos["n"], "shares": pos["s"],
                      "open_orders": orders["n"]}}


def change_password(req: Request):
    body = req.json()
    old, new = body.get("old_password") or "", body.get("new_password") or ""
    if len(new) < 8:
        raise RequestError(400, "新密码至少 8 位", "weak_password")
    with get_conn() as conn:
        user = one(conn, "SELECT * FROM users WHERE id=?", (req.user["user_id"],))
        if not verify_password(old, user["password_hash"]):
            raise RequestError(400, "原密码不正确", "bad_password")
        update(conn, "users", user["id"], {"password_hash": hash_password(new)})
        log(conn, user["id"], "auth.change_password", user["email"], None, req.ip)
    return {"ok": True}


def register_routes(r):
    r.post("/api/auth/login", login, auth=False)
    r.post("/api/auth/register", register, auth=False)
    r.get("/api/auth/me", me)
    r.post("/api/auth/change-password", change_password)
