"""服务层测试。"""

from smart_stock.service import detail_to_dict, get_stock_detail


def test_get_stock_detail_demo():
    detail = get_stock_detail("600519", demo=True, days=90)
    payload = detail_to_dict(detail)

    assert payload["analysis"]["code"] == "600519"
    assert len(payload["chart"]["close"]) == 90
    assert payload["chart"]["ma5"][-1] is not None
