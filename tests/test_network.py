"""网络代理辅助测试。"""

import os

import requests

from smart_stock.network import format_fetch_error, without_system_proxy


def test_without_system_proxy_clears_env():
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:9999"
    with without_system_proxy():
        assert "HTTP_PROXY" not in os.environ
        assert os.environ.get("NO_PROXY") == "*"
    assert os.environ.get("HTTP_PROXY") == "http://127.0.0.1:9999"
    del os.environ["HTTP_PROXY"]


def test_without_system_proxy_disables_requests_session_proxy():
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:9999"
    with without_system_proxy():
        session = requests.Session()
        assert session.trust_env is False
        assert session.proxies.get("http") is None
        assert session.proxies.get("https") is None
    del os.environ["HTTP_PROXY"]


def test_without_system_proxy_blocks_urllib_getproxies():
    with without_system_proxy():
        import urllib.request

        assert urllib.request.getproxies() == {}


def test_format_fetch_error_proxy_hint():
    message = format_fetch_error(Exception("ProxyError: Unable to connect to proxy"))
    assert "系统代理" in message
    assert "--demo" in message
