"""测试夹具：临时库 + 直接调用分发层（不起网络，跑得快）"""
import json
import os
import tempfile

import pytest

TMP = tempfile.mkdtemp(prefix="predx-test-")
os.environ.setdefault("PX_DB_PATH", os.path.join(TMP, "test.db"))
os.environ.setdefault("PX_SECRET_KEY", "test-secret-key")
os.environ.setdefault("PX_ALLOW_REGISTRATION", "1")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.http import Request, RequestError      # noqa: E402
from app.main import build_app                  # noqa: E402
from app.seed import bootstrap                  # noqa: E402


@pytest.fixture(scope="session")
def app():
    bootstrap(verbose=False)
    return build_app()


def call(app, method, path, body=None, token=None, query=None):
    q = {k: [str(v)] for k, v in (query or {}).items()}
    req = Request(method=method, path=path, query=q, headers={},
                  body=json.dumps(body).encode() if body is not None else b"", ip="127.0.0.1")
    if token:
        req.headers["authorization"] = "Bearer " + token
    try:
        resp = app.dispatch(req)
        if resp.content_type.startswith("application/json"):
            return resp.status, json.loads(resp.body)
        return resp.status, resp
    except RequestError as e:
        return e.status, {"error": {"code": e.code, "message": e.message}}


def _login(app, email, pwd):
    status, data = call(app, "POST", "/api/auth/login", {"email": email, "password": pwd})
    assert status == 200, data
    return data["token"]


@pytest.fixture(scope="session")
def demo_token(app):
    return _login(app, "demo@predx.io", "demo1234")


@pytest.fixture(scope="session")
def admin_token(app):
    return _login(app, "admin@predx.io", "admin1234")


@pytest.fixture()
def fresh_user(app):
    """每个测试独立的新用户（$10,000 体验金），互不干扰。"""
    import uuid
    email = f"t{uuid.uuid4().hex[:8]}@test.io"
    status, data = call(app, "POST", "/api/auth/register",
                        {"email": email, "password": "pass12345", "handle": "测试员"})
    assert status == 200, data
    data["email"] = email
    return data
