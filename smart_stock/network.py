"""网络请求辅助。"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Callable

PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

NO_PROXY_KEYS = ("NO_PROXY", "no_proxy")
DISABLED_PROXIES = {"http": None, "https": None}


@contextmanager
def without_system_proxy():
    """临时禁用系统与环境代理，供 AKShare / requests 直连行情源。

    除清除环境变量外，还会：
    - 将 requests.Session 设为 trust_env=False，避免读取 Windows 注册表代理
    - 屏蔽 urllib 的 getproxies，防止系统级代理注入
    """
    saved_env = {key: os.environ.pop(key) for key in PROXY_ENV_KEYS if key in os.environ}
    saved_no_proxy = {key: os.environ[key] for key in NO_PROXY_KEYS if key in os.environ}
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"

    patches: list[tuple[Any, str, Any]] = []
    try:
        import requests
        import urllib.request

        original_session_init = requests.Session.__init__

        def patched_session_init(self: requests.Session, *args: Any, **kwargs: Any) -> None:
            original_session_init(self, *args, **kwargs)
            self.trust_env = False
            self.proxies.update(DISABLED_PROXIES)

        requests.Session.__init__ = patched_session_init  # type: ignore[method-assign]
        patches.append((requests.Session, "__init__", original_session_init))

        original_request = requests.api.request

        def patched_request(method: str, url: str, **kwargs: Any) -> requests.Response:
            kwargs.setdefault("proxies", DISABLED_PROXIES.copy())
            with requests.Session() as session:
                session.trust_env = False
                return session.request(method=method, url=url, **kwargs)

        requests.api.request = patched_request  # type: ignore[assignment]
        requests.request = patched_request  # type: ignore[assignment]
        patches.append((requests.api, "request", original_request))
        patches.append((requests, "request", original_request))

        for name in ("getproxies", "getproxies_environment"):
            if hasattr(urllib.request, name):
                original: Callable[..., dict[str, str]] = getattr(urllib.request, name)

                def empty_proxies(
                    *_args: Any,
                    _original: Callable[..., dict[str, str]] = original,
                    **_kwargs: Any,
                ) -> dict[str, str]:
                    return {}

                setattr(urllib.request, name, empty_proxies)
                patches.append((urllib.request, name, original))

        yield
    finally:
        for target, attr, original in reversed(patches):
            setattr(target, attr, original)

        os.environ.update(saved_env)
        for key in NO_PROXY_KEYS:
            if key in saved_no_proxy:
                os.environ[key] = saved_no_proxy[key]
            else:
                os.environ.pop(key, None)


def format_fetch_error(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "proxy" in lowered or "proxyerror" in type(exc).__name__.lower():
        return (
            "行情拉取失败：检测到本机代理不可用（环境变量或 Windows 系统代理）。"
            "请依次尝试：\n"
            "1) 关闭 Clash/V2Ray 等软件的「系统代理」；\n"
            "2) Windows 设置 → 网络和 Internet → 代理 → 关闭「使用代理服务器」；\n"
            "3) 更新到最新代码后重试（已自动绕过 requests 系统代理）；\n"
            "4) 暂时使用 --demo 参数加载本地演示数据。"
        )
    return f"行情拉取失败: {message}"
