"""回测与 AI 解读测试。"""

from fastapi.testclient import TestClient

from smart_stock.backtest import run_backtest
from smart_stock.llm_insight import generate_insight
from smart_stock.news import fetch_stock_news
from smart_stock.serializers import backtest_to_dict
from smart_stock.web.app import create_app


def test_run_backtest_demo():
    result = run_backtest("600519", days=120, demo=True)
    payload = backtest_to_dict(result)
    assert payload["code"] == "600519"
    assert len(payload["equity_curve"]) > 0
    assert "total_return_pct" in payload


def test_generate_insight_demo():
    payload = generate_insight("600519", demo=True)
    assert payload["code"] == "600519"
    assert payload["mode"] == "demo"
    assert "技术面结论" in payload["content"]
    assert payload["news"]


def test_fetch_demo_news():
    items = fetch_stock_news("600519", demo=True)
    assert items
    assert items[0].title


def test_api_backtest_demo():
    client = TestClient(create_app(demo=True))
    response = client.get("/api/backtest/600519", params={"days": 120, "capital": 100000})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "600519"
    assert payload["equity_curve"]


def test_api_insight_demo():
    client = TestClient(create_app(demo=True))
    response = client.get("/api/insight/600519", params={"days": 120})
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "demo"
    assert payload["content"]
