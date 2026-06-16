"""东方财富直连测试。"""

from unittest.mock import patch

import pandas as pd
import pytest

from smart_stock import eastmoney
from smart_stock.data import fetch_daily_bars, search_stock
from smart_stock.network import direct_http_get_json


KLINE_PAYLOAD = {
    "data": {
        "klines": [
            "2025-06-03,11.77,11.93,12.07,11.75,145891,174404553.00,2.68,0.08,0.01,2.10",
            "2025-06-04,11.94,12.12,12.18,11.94,221464,268365265.23,2.01,1.59,0.19,3.19",
        ]
    }
}

SUGGEST_PAYLOAD = {
    "QuotationCodeTable": {
        "Data": [
            {
                "Code": "000815",
                "Name": "美利云",
                "Classify": "AStock",
            },
            {
                "Code": "000815",
                "Name": "细分食品",
                "Classify": "Index",
            },
        ]
    }
}


def test_to_secid():
    assert eastmoney.to_secid("000815") == "0.000815"
    assert eastmoney.to_secid("600519") == "1.600519"


@patch("smart_stock.eastmoney.direct_http_get_json")
def test_fetch_daily_bars_retries_shorter_window(mock_get_json):
    mock_get_json.side_effect = [
        ConnectionError("timeout on long window"),
        KLINE_PAYLOAD,
    ]
    from datetime import datetime, timedelta

    end = datetime(2026, 6, 16)
    start = end - timedelta(days=400)
    frame = eastmoney.fetch_daily_bars("000815", start, end, days=2)
    assert len(frame) == 2
    assert mock_get_json.call_count == 2


@patch("smart_stock.eastmoney.direct_http_get_json")
def test_fetch_kline_parses_rows(mock_get_json):
    mock_get_json.return_value = KLINE_PAYLOAD
    frame = eastmoney.fetch_kline("000815", "20250601", "20250615")
    assert len(frame) == 2
    assert frame.iloc[0]["收盘"] == "11.93"
    assert frame.iloc[0]["股票代码"] == "000815"


@patch("smart_stock.eastmoney.direct_http_get_json")
def test_suggest_stocks_filters_astock(mock_get_json):
    mock_get_json.return_value = SUGGEST_PAYLOAD
    frame = eastmoney.suggest_stocks("000815", limit=5)
    assert len(frame) == 1
    assert frame.iloc[0]["名称"] == "美利云"


@patch("smart_stock.data.eastmoney.fetch_daily_bars")
def test_fetch_daily_bars_uses_eastmoney_first(mock_fetch):
    mock_fetch.return_value = pd.DataFrame(
        {
            "日期": ["2025-06-03", "2025-06-04"],
            "开盘": [11.77, 11.94],
            "收盘": [11.93, 12.12],
            "最高": [12.07, 12.18],
            "最低": [11.75, 11.94],
            "成交量": [145891, 221464],
            "成交额": [174404553.0, 268365265.23],
        }
    )
    bars = fetch_daily_bars("000815", days=2, demo=False)
    assert len(bars) == 2
    assert "close" in bars.columns


@patch("smart_stock.data.eastmoney.suggest_stocks")
def test_search_stock_live(mock_suggest):
    mock_suggest.return_value = pd.DataFrame([{"代码": "600519", "名称": "贵州茅台"}])
    result = search_stock("茅台", limit=1, demo=False)
    assert result.iloc[0]["代码"] == "600519"


def test_direct_http_get_json_live():
    """联网集成测试：urllib 直连东方财富。"""
    try:
        payload = direct_http_get_json(
            eastmoney.KLINE_URL,
            params={
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "klt": "101",
                "fqt": "1",
                "secid": "0.000815",
                "beg": "20250601",
                "end": "20250610",
            },
        )
    except ConnectionError as exc:
        pytest.skip(f"东方财富接口暂不可达: {exc}")
    assert payload["data"]["klines"]
