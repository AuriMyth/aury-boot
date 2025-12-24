from __future__ import annotations

from collections.abc import Callable
from typing import Any

from starlette.requests import Request

try:  # pragma: no cover
    from sqladmin.authentication import AuthenticationBackend as _SQLAdminAuthenticationBackend
except Exception:  # pragma: no cover
    _SQLAdminAuthenticationBackend = None


def _require_sqladmin():
    try:
        from sqladmin.authentication import AuthenticationBackend
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "未安装 sqladmin。请先安装: uv add \"aury-boot[admin]\" 或 uv add sqladmin"
        ) from exc


def _get_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


class BasicAdminAuthBackend(_SQLAdminAuthenticationBackend or object):
    """SQLAdmin 登录页 + session 的最简用户名/密码认证（推荐默认）。"""

    def __init__(self, *, username: str, password: str, secret_key: str, session_key: str = "aury_admin") -> None:
        _require_sqladmin()
        # 若 sqladmin 不存在，此类的 base 会是 object，这里会提前抛错，避免静默不兼容
        super().__init__(secret_key=secret_key)  # type: ignore[misc]
        self._username = username
        self._password = password
        self._session_key = session_key

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", "")).strip()
        if username == self._username and password == self._password:
            request.session.update({self._session_key: True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get(self._session_key))


class BearerWhitelistAdminAuthBackend(_SQLAdminAuthenticationBackend or object):
    """Bearer 白名单认证。

    支持两种方式：
    - Authorization: Bearer <token>（适合反向代理注入/自动化）
    - 登录页输入 token（用户名任意，password/token 字段均可）
    """

    def __init__(
        self,
        *,
        tokens: list[str],
        secret_key: str,
        session_key: str = "aury_admin_token",
    ) -> None:
        _require_sqladmin()
        super().__init__(secret_key=secret_key)  # type: ignore[misc]
        self._tokens = {t.strip() for t in tokens if t and t.strip()}
        self._session_key = session_key

    async def login(self, request: Request) -> bool:
        form = await request.form()
        # 兼容不同表单字段：优先 token，其次 password
        token = str(form.get("token") or form.get("password") or "").strip()
        if token and token in self._tokens:
            request.session.update({self._session_key: token})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        header_token = _get_bearer_token(request)
        if header_token and header_token in self._tokens:
            return True
        session_token = request.session.get(self._session_key)
        return bool(session_token and session_token in self._tokens)


def wrap_authenticate(
    *,
    secret_key: str,
    authenticate: Callable[[Request], Any],
    session_key: str = "aury_admin",
):
    """将一个 authenticate(request) 可调用对象包装为 SQLAdmin AuthenticationBackend。

    用于让用户以最小成本自定义（不必继承 SQLAdmin 类）。
    """
    _require_sqladmin()
    from sqladmin.authentication import AuthenticationBackend

    class _Wrapped(AuthenticationBackend):
        async def login(self, request: Request) -> bool:
            # 默认不提供登录页逻辑；用户可自己实现更复杂版本
            return False

        async def logout(self, request: Request) -> bool:
            request.session.pop(session_key, None)
            return True

        async def authenticate(self, request: Request) -> bool:
            result = authenticate(request)
            if hasattr(result, "__await__"):
                result = await result
            return bool(result)

    return _Wrapped(secret_key=secret_key)


