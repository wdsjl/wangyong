"""网络代理辅助测试。"""

import os

from smart_stock.network import without_system_proxy


def test_without_system_proxy_clears_env():
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:9999"
    with without_system_proxy():
        assert "HTTP_PROXY" not in os.environ
    assert os.environ.get("HTTP_PROXY") == "http://127.0.0.1:9999"
    del os.environ["HTTP_PROXY"]
