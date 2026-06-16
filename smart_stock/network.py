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

DEFAULT_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://quote.eastmoney.com/",
}


def direct_http_get_json(
    url: str,
    params: dict[str, str] | None = None,
    timeout: float = 20.0,
    retries: int = 3,
):
    """使用 urllib 直连 HTTP，显式禁用一切代理。

    不依赖 requests，可绕过 Windows 注册表/环境变量中的失效代理。
    """
    import json
    import time
    import urllib.error
    import urllib.parse
    import urllib.request

    if params:
        query = urllib.parse.urlencode(params)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"

    request = urllib.request.Request(url, headers=DEFAULT_HTTP_HEADERS, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with opener.open(request, timeout=timeout) as response:
                payload = response.read()
            return json.loads(payload.decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(0.8 * (attempt + 1))
                continue
            break

    raise ConnectionError(str(last_error)) from last_error


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


def diagnose_network(code: str = "000815") -> list[str]:
    """检测本机网络与东方财富直连是否可用。"""
    lines: list[str] = []
    proxy_vars = [key for key in PROXY_ENV_KEYS if os.environ.get(key)]
    if proxy_vars:
        lines.append("检测到环境变量代理: " + ", ".join(proxy_vars))
    else:
        lines.append("未检测到 HTTP_PROXY / HTTPS_PROXY 等环境变量代理")

    try:
        import urllib.request

        registry_proxies = urllib.request.getproxies()
        if registry_proxies:
            lines.append("检测到系统代理(注册表): " + ", ".join(f"{k}={v}" for k, v in registry_proxies.items()))
        else:
            lines.append("未检测到系统注册表代理")
    except Exception as exc:
        lines.append(f"读取系统代理失败: {exc}")

    try:
        from smart_stock.eastmoney import to_secid

        payload = direct_http_get_json(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            params={
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "klt": "101",
                "fqt": "1",
                "secid": to_secid(code),
                "beg": "20250601",
                "end": "20250610",
            },
            retries=2,
        )
        count = len((payload.get("data") or {}).get("klines") or [])
        lines.append(f"东方财富 urllib 直连: 成功（返回 {count} 根 K 线）")
    except Exception as exc:
        lines.append(f"东方财富 urllib 直连: 失败（{exc}）")
        lines.append("若使用 Clash/V2Ray TUN 模式，请暂时关闭 TUN 或切换为「规则/全局但不劫持」后重试")

    return lines


def format_fetch_error(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if "proxy" in lowered or "proxyerror" in type(exc).__name__.lower():
        return (
            "行情拉取失败：本机代理或网络拦截了东方财富接口。"
            "请依次尝试：\n"
            "1) 关闭 Clash/V2Ray 的「系统代理」或 TUN 模式后重试；\n"
            "2) Windows 设置 → 网络和 Internet → 代理 → 关闭「使用代理服务器」；\n"
            "3) 确认已更新到最新代码（已改用 urllib 直连，不经过 requests）；\n"
            "4) 运行 python main.py check-network 查看诊断；\n"
            "5) 暂时使用 --demo 参数加载本地演示数据。"
        )
    return f"行情拉取失败: {message}"
