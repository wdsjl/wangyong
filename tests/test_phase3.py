"""第三期指标与策略配置测试。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from smart_stock import database as db
from smart_stock.indicators import add_ama, enrich_indicators, latest_indicator_snapshot
from smart_stock.intraday import enrich_intraday, latest_intraday_snapshot
from smart_stock.sample_data import generate_demo_bars, generate_demo_intraday
from smart_stock.sector import fetch_sector_sentiment
from smart_stock.strategy_profile import StrategyProfile
from smart_stock.vix import compute_vix_proxy
from smart_stock.web.app import create_app


def test_phase3_ama_indicator():
    enriched = enrich_indicators(generate_demo_bars("600519", days=150))
    snapshot = latest_indicator_snapshot(enriched)
    assert snapshot.ama is not None


def test_phase3_vix_proxy():
    enriched = enrich_indicators(generate_demo_bars("000001", days=80))
    vix = compute_vix_proxy(enriched)
    assert vix.index_value is not None
    assert vix.label in {"低恐慌", "中性", "中性偏谨慎", "高恐慌"}


def test_phase3_sector_sentiment_demo():
    sector = fetch_sector_sentiment("600519", demo=True)
    assert sector.sector_name
    assert sector.sentiment_score is not None


def test_phase3_intraday_snapshot():
    bars = generate_demo_intraday("600519", period="5m", bars=48)
    enriched = enrich_intraday(bars)
    snapshot = latest_intraday_snapshot(enriched)
    assert snapshot.bar_count == 48
    assert snapshot.rsi is not None


def test_strategy_profile_roundtrip():
    profile = StrategyProfile()
    profile = StrategyProfile.from_dict(profile.to_dict())
    assert profile.strategy.buy_threshold == 0.6
    assert profile.weights.trend == 1.0


@pytest.fixture
def client(tmp_path: Path):
    db.reset_db_cache()
    test_client = TestClient(create_app(demo=True, db_path=tmp_path / "phase3.db"))
    yield test_client
    db.reset_db_cache()
    db.set_db_path(None)


def test_api_strategy_settings(client):
    put = client.put(
        "/api/strategy-settings",
        json={
            "strategy": {"buy_threshold": 0.7, "sell_threshold": -0.7},
            "weights": {"trend": 1.2, "momentum": 0.9},
            "use_ama_trend": True,
            "vix_caution_threshold": 60,
        },
    )
    assert put.status_code == 200
    payload = put.json()
    assert payload["strategy"]["buy_threshold"] == 0.7
    assert payload["weights"]["trend"] == 1.2

    get = client.get("/api/strategy-settings")
    assert get.status_code == 200
    assert get.json()["strategy"]["buy_threshold"] == 0.7


def test_api_intraday_demo(client):
    response = client.get("/api/intraday/600519", params={"period": "5m", "bars": 24})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "600519"
    assert payload["chart"]["times"]
    assert payload["snapshot"]["rsi"] is not None


def test_api_analyze_has_phase3_fields(client):
    response = client.get("/api/analyze/600519", params={"days": 90})
    assert response.status_code == 200
    monitoring = response.json()["analysis"]["monitoring"]
    assert monitoring.get("vix")
    assert monitoring.get("sector")
    assert monitoring.get("ama_signal")
    assert "ama" in response.json()["chart"]
