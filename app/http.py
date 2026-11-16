"""极简但完整的 HTTP 框架：路由（含路径参数）、鉴权、中间件、统一错误。

刻意不使用 FastAPI/Flask：零依赖 = 客户内网可部署 + 攻击面小。
全部代码约 300 行，可审计 —— 政府/国企客户很在意这一点。
"""
import json
import re
import traceback
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from .config import config
from .security import rate_limiter, verify_jwt


# ------------------------------------------------------------------ 错误
class RequestError(Exception):
    def __init__(self, status: int, message: str, code: str = "bad_request", detail=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code
        self.detail = detail


class NotFound(RequestError):
    def __init__(self, what="资源"):
        super().__init__(404, f"{what}不存在", "not_found")


class Forbidden(RequestError):
    def __init__(self, msg="无权访问"):
        super().__init__(403, msg, "forbidden")


class Unauthorized(RequestError):
    def __init__(self, msg="请先登录"):
        super().__init__(401, msg, "unauthorized")


# ------------------------------------------------------------------ 请求/响应
@dataclass
class Request:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    body: bytes
    params: dict[str, str] = field(default_factory=dict)
    user: dict | None = None
    ip: str = ""

    def json(self, required: bool = True) -> dict:
        if not self.body:
            if required:
                raise RequestError(400, "请求体不能为空", "empty_body")
            return {}
        try:
            data = json.loads(self.body)
        except ValueError:
            raise RequestError(400, "请求体不是合法 JSON", "invalid_json")
        if not isinstance(data, dict):
            raise RequestError(400, "请求体必须是 JSON 对象", "invalid_json")
        return data

    def q(self, key: str, default: str | None = None) -> str | None:
        vals = self.query.get(key)
        return vals[0] if vals else default

    def q_int(self, key: str, default: int) -> int:
        try:
            return int(self.q(key) or default)
        except (TypeError, ValueError):
            return default

    @property
    def token(self) -> str | None:
        h = self.headers.get("authorization", "")
        if h.lower().startswith("bearer "):
            return h[7:].strip()
        return None

    @property
    def api_key(self) -> str | None:
        k = self.headers.get("x-api-key")
        return k.strip() if k else None


class Response:
    def __init__(self, body: bytes, status: int = 200,
                 content_type: str = "application/json; charset=utf-8",
                 headers: dict[str, str] | None = None):
        self.body = body
        self.status = status
        self.content_type = content_type
        self.headers = headers or {}


def json_response(data: Any, status: int = 200) -> Response:
    return Response(json.dumps(data, ensure_ascii=False).encode(), status)


def file_response(data: bytes, filename: str, content_type: str) -> Response:
    from urllib.parse import quote
    return Response(
        data, 200, content_type,
        {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# ------------------------------------------------------------------ 路由器
class Router:
    def __init__(self) -> None:
        self._routes: list[tuple[str, re.Pattern, Callable, bool, tuple[str, ...]]] = []

    def add(self, method: str, pattern: str, handler: Callable,
            auth: bool = True, roles: tuple[str, ...] = ()) -> None:
        def _repl(mo):
            name = mo.group(1)
            if name.startswith("int:"):
                return f"(?P<{name[4:]}>\\d+)"
            return f"(?P<{name}>[^/]+)"
        regex = "^" + re.sub(r"<([\w:]+)>", _repl, pattern) + "$"
        self._routes.append((method.upper(), re.compile(regex), handler, auth, roles))

    def get(self, p, handler, **kw):    self.add("GET", p, handler, **kw)
    def post(self, p, handler, **kw):   self.add("POST", p, handler, **kw)
    def patch(self, p, handler, **kw):  self.add("PATCH", p, handler, **kw)
    def put(self, p, handler, **kw):    self.add("PUT", p, handler, **kw)
    def delete(self, p, handler, **kw): self.add("DELETE", p, handler, **kw)

    def match(self, method: str, path: str):
        allowed = []
        for m, rx, handler, auth, roles in self._routes:
            mo = rx.match(path)
            if mo:
                if m == method:
                    return handler, mo.groupdict(), auth, roles
                allowed.append(m)
        if allowed:
            raise RequestError(405, f"该方法不支持，可用：{', '.join(sorted(set(allowed)))}", "method_not_allowed")
        return None, None, False, ()


# ------------------------------------------------------------------ 应用
class Application:
    def __init__(self, router: Router, static_dir):
        self.router = router
        self.static_dir = static_dir

    # 由子类/装配层注入，避免循环依赖
    resolve_principal: Callable[[Request], dict | None] = staticmethod(lambda r: None)

    def dispatch(self, req: Request) -> Response:
        path = req.path
        handler, params, auth, roles = self.router.match(req.method, path)
        if handler is None:
            # ---- 静态资源 / SPA 回退（/s/<token> 这类显式路由已在上面命中）
            if req.method == "GET" and not path.startswith("/api/"):
                return self._static(path)
            raise NotFound("接口")

        req.params = params
        if auth:
            principal = self.resolve_principal(req)
            if not principal:
                raise Unauthorized()
            if roles and principal.get("role") not in roles:
                raise Forbidden(f"需要角色：{'/'.join(roles)}")
            req.user = principal
        result = handler(req)
        return result if isinstance(result, Response) else json_response(result)

    def _static(self, path: str) -> Response:
        from pathlib import Path
        rel = path.lstrip("/") or "index.html"
        if not rel.endswith(".html") and "." not in rel.split("/")[-1]:
            rel = "index.html"          # SPA 前端路由回退
        target = (self.static_dir / rel).resolve()
        if not str(target).startswith(str(self.static_dir.resolve())) or not target.is_file():
            target = self.static_dir / "index.html"
        if not target.is_file():
            raise NotFound("页面")
        ext = target.suffix.lower()
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
            ".json": "application/json; charset=utf-8",
        }.get(ext, "application/octet-stream")
        return Response(target.read_bytes(), 200, ctype)


# ------------------------------------------------------------------ HTTP Handler
def make_handler(app: Application):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"PredX/{config.VERSION}"
        protocol_version = "HTTP/1.1"

        # ---- 日志：生产环境保持安静
        def log_message(self, fmt, *args):
            if config.DEBUG:
                print(f"[{self.log_date_time_string()}] {fmt % args}")

        def _client_ip(self) -> str:
            fwd = self.headers.get("x-forwarded-for")
            if fwd:
                return fwd.split(",")[0].strip()
            return self.client_address[0] if self.client_address else "-"

        def _handle(self, method: str):
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            req = Request(
                method=method,
                path=parsed.path,
                query=parse_qs(parsed.query),
                headers={k.lower(): v for k, v in self.headers.items()},
                body=body,
                ip=self._client_ip(),
            )
            try:
                is_auth = parsed.path.startswith("/api/auth/")
                limit = config.RATE_LIMIT_AUTH if is_auth else config.RATE_LIMIT_API
                if not rate_limiter.allow(f"{req.ip}:{parsed.path}", limit):
                    raise RequestError(429, "请求过于频繁，请稍后再试", "rate_limited")

                resp = app.dispatch(req)
                self._write(resp)
            except RequestError as e:
                self._write(json_response(
                    {"error": {"code": e.code, "message": e.message, "detail": e.detail}}, e.status))
            except BrokenPipeError:
                pass
            except Exception:
                if config.DEBUG:
                    traceback.print_exc()
                self._write(json_response(
                    {"error": {"code": "internal", "message": "服务内部错误"}}, 500))

        def _write(self, resp: Response):
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.content_type)
            self.send_header("Content-Length", str(len(resp.body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "same-origin")
            for k, v in resp.headers.items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(resp.body)

        def do_GET(self):     self._handle("GET")
        def do_POST(self):    self._handle("POST")
        def do_PATCH(self):   self._handle("PATCH")
        def do_PUT(self):     self._handle("PUT")
        def do_DELETE(self):  self._handle("DELETE")
        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Allow", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler


def serve(app: Application, host: str, port: int):
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    httpd.daemon_threads = True
    print(f"{config.APP_NAME} v{config.VERSION}  →  http://{host}:{port}")
    print(f"数据库：{config.DB_PATH}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
