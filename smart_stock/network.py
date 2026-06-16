"""网络请求辅助。"""

from __future__ import annotations

import os
from contextlib import contextmanager

PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


@contextmanager
def without_system_proxy():
    """临时禁用环境变量中的 HTTP 代理。

    部分用户本机配置了失效代理，会导致 AKShare 访问东方财富失败。
    """
    saved = {key: os.environ.pop(key) for key in PROXY_ENV_KEYS if key in os.environ}
    try:
        yield
    finally:
        os.environ.update(saved)


def format_fetch_error(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "proxy" in lowered or "proxyerror" in type(exc).__name__.lower():
        return (
            "行情拉取失败：检测到系统/环境代理不可用。"
            "请在 PowerShell 执行："
            " Remove-Item Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY -ErrorAction SilentlyContinue"
            " 后重试；或暂时使用 --demo。"
        )
    return f"行情拉取失败: {message}"
