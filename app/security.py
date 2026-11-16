"""安全组件：口令哈希、HS256 JWT、API Key、限流。

全部基于标准库实现，避免引入 jwt/passlib 等外部依赖。
"""
import base64
import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from typing import Any

from .config import config

# ------------------------------------------------------------------ 口令
def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("密码至少 8 位")
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, config.PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${config.PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


# ------------------------------------------------------------------ JWT
def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(txt: str) -> bytes:
    pad = "=" * (-len(txt) % 4)
    return base64.urlsafe_b64decode(txt + pad)


def sign_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now_s = int(time.time())
    body = dict(payload)
    body.setdefault("iat", now_s)
    body.setdefault("exp", now_s + config.TOKEN_TTL_SECONDS)
    seg = f"{_b64e(_jsonb(header))}.{_b64e(_jsonb(body))}"
    sig = hmac.new(config.SECRET_KEY.encode(), seg.encode(), hashlib.sha256).digest()
    return f"{seg}.{_b64e(sig)}"


def verify_jwt(token: str) -> dict[str, Any] | None:
    try:
        h, p, s = token.split(".")
    except ValueError:
        return None
    expect = hmac.new(config.SECRET_KEY.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(expect, _b64d(s)):
            return None
        payload = _json_loads(_b64d(p))
    except (ValueError, TypeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def _jsonb(obj) -> bytes:
    import json
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()


def _json_loads(raw: bytes) -> dict:
    import json
    return json.loads(raw.decode())


# ------------------------------------------------------------------ API Key
def new_api_key() -> tuple[str, str, str]:
    """返回 (明文, 前缀, 哈希)。明文只在此刻出现一次。"""
    raw = "sb_" + secrets.token_urlsafe(28)
    return raw, raw[:11], hashlib.sha256(raw.encode()).hexdigest()


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ------------------------------------------------------------------ 限流
class RateLimiter:
    """进程内滑动窗口限流。多实例部署时替换为 Redis 实现即可。"""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: int = 60) -> bool:
        if limit <= 0:
            return True
        now_s = time.time()
        with self._lock:
            bucket = [t for t in self._hits.get(key, []) if now_s - t < window]
            if len(bucket) >= limit:
                self._hits[key] = bucket
                return False
            bucket.append(now_s)
            self._hits[key] = bucket
            return True

    def sweep(self) -> None:
        now_s = time.time()
        with self._lock:
            for k in list(self._hits):
                if not [t for t in self._hits[k] if now_s - t < 60]:
                    self._hits.pop(k, None)


rate_limiter = RateLimiter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))
