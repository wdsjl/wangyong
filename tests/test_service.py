"""服务层测试。"""

from smart_stock.service import compare_stocks, detail_to_dict, get_stock_detail


def test_get_stock_detail_demo():
    detail = get_stock_detail("600519", demo=True, days=90)
    payload = detail_to_dict(detail)

    assert payload["analysis"]["code"] == "600519"
    assert len(payload["chart"]["close"]) == 90
    assert payload["chart"]["ma5"][-1] is not None


def test_compare_stocks_demo():
    series = compare_stocks(["600519", "000001"], days=60, demo=True)
    assert len(series) == 2
    assert all(len(item["values"]) == 60 for item in series)
    assert series[0]["values"][0] == 100
