"""Web API 测试。"""

from fastapi.testclient import TestClient

from smart_stock.web.app import create_app


def test_index_page():
    client = TestClient(create_app(demo=True))
    response = client.get("/")
    assert response.status_code == 200
    assert "智能炒股" in response.text


def test_api_config():
    client = TestClient(create_app(demo=True))
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["demo"] is True


def test_api_search_demo():
    client = TestClient(create_app(demo=True))
    response = client.get("/api/search", params={"keyword": "茅台"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["items"][0]["code"] == "600519"


def test_api_analyze_demo():
    client = TestClient(create_app(demo=True))
    response = client.get("/api/analyze/600519", params={"days": 120})
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["code"] == "600519"
    assert len(payload["chart"]["dates"]) == 120
    assert "signal" in payload["analysis"]


def test_api_batch_demo():
    client = TestClient(create_app(demo=True))
    response = client.get("/api/batch", params={"codes": "600519,000001"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
