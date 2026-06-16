"""网络诊断测试。"""

from unittest.mock import patch

from smart_stock.network import diagnose_network


@patch("smart_stock.network.direct_http_get_json")
def test_diagnose_network_success(mock_get_json):
    mock_get_json.return_value = {"data": {"klines": ["a", "b", "c"]}}
    lines = diagnose_network("000815")
    assert any("成功" in line for line in lines)


@patch("smart_stock.network.direct_http_get_json", side_effect=ConnectionError("proxy down"))
def test_diagnose_network_failure(mock_get_json):
    lines = diagnose_network("000815")
    assert any("失败" in line for line in lines)
