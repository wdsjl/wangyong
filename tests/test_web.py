"""Web API 测试。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from smart_stock import database as db
from smart_stock.web.app import create_app


@pytest.fixture
def client(tmp_path: Path):
    db.reset_db_cache()
    test_client = TestClient(create_app(demo=True, db_path=tmp_path / "web_test.db"))
    yield test_client
    db.reset_db_cache()
    db.set_db_path(None)


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "智能炒股" in response.text


def test_api_config(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["demo"] is True
    assert "database" in payload


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_api_search_demo(client):
    response = client.get("/api/search", params={"keyword": "茅台"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["items"][0]["code"] == "600519"


def test_api_analyze_demo(client):
    response = client.get("/api/analyze/600519", params={"days": 120})
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["code"] == "600519"
    assert len(payload["chart"]["dates"]) == 120
    assert "signal" in payload["analysis"]
    for field in ("open", "high", "low", "close"):
        assert field in payload["chart"]
        assert len(payload["chart"][field]) == 120
    assert "buy_markers" in payload["chart"]
    assert "sell_markers" in payload["chart"]


def test_api_batch_demo(client):
    response = client.get("/api/batch", params={"codes": "600519,000001"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    assert "alerts" in payload


def test_api_compare_demo(client):
    response = client.get("/api/compare", params={"codes": "600519,000001,300750", "days": 60})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["series"]) == 3
    assert payload["series"][0]["values"][0] == 100


def test_api_watchlist_crud(client):
    put_response = client.put("/api/watchlist", json={"codes": ["000815", "600519"]})
    assert put_response.status_code == 200
    assert put_response.json()["codes"] == ["000815", "600519"]

    get_response = client.get("/api/watchlist")
    assert get_response.status_code == 200
    assert get_response.json()["codes"] == ["000815", "600519"]


def test_api_monitor_settings(client):
    response = client.put(
        "/api/monitor-settings",
        json={"monitor_enabled": False, "interval_sec": 120, "notify_enabled": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["monitor_enabled"] is False
    assert payload["interval_sec"] == 120

    get_response = client.get("/api/monitor-settings")
    assert get_response.json()["notify_enabled"] is True
