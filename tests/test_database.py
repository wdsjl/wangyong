"""本地数据库测试。"""

from pathlib import Path

import pytest

from smart_stock import database as db
from smart_stock.store import (
    get_monitor_settings,
    get_watchlist,
    init_store,
    list_alerts,
    put_monitor_settings,
    put_watchlist,
    record_analysis,
    record_batch,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db.reset_db_cache()
    path = tmp_path / "test.db"
    init_store(path)
    yield path
    db.reset_db_cache()
    db.set_db_path(None)


def test_init_creates_schema(temp_db: Path):
    assert temp_db.exists()
    with db.get_connection(temp_db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert "watchlist" in tables
    assert "analysis_history" in tables


def test_watchlist_roundtrip(temp_db: Path):
    saved = put_watchlist(["000815", "600519", "000815"])
    assert saved["codes"] == ["000815", "600519"]
    assert get_watchlist()["codes"] == ["000815", "600519"]


def test_monitor_settings_roundtrip(temp_db: Path):
    payload = put_monitor_settings(
        monitor_enabled=False,
        interval_sec=120,
        notify_enabled=True,
    )
    assert payload["monitor_enabled"] is False
    assert payload["interval_sec"] == 120
    assert get_monitor_settings()["notify_enabled"] is True


def test_batch_records_alerts(temp_db: Path):
    items = [
        {
            "code": "000815",
            "name": "美利云",
            "score": 0.5,
            "signal": {"value": "观望", "key": "HOLD"},
        }
    ]
    record_batch(items, detect_changes=False)

    changed_items = [
        {
            "code": "000815",
            "name": "美利云",
            "score": 1.2,
            "signal": {"value": "买入", "key": "BUY"},
        }
    ]
    alerts = record_batch(changed_items, detect_changes=True)
    assert len(alerts) == 1
    assert alerts[0]["from"] == "观望"
    assert alerts[0]["to"] == "买入"

    history = list_alerts(limit=10)
    assert len(history["items"]) == 1


def test_analysis_history_saved(temp_db: Path):
    payload = {
        "analysis": {
            "code": "600519",
            "name": "贵州茅台",
            "latest_price": 1500.0,
            "score": 0.8,
            "signal": {"value": "买入", "key": "BUY"},
        }
    }
    record_analysis(payload, data_source="demo")
    with db.get_connection(temp_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()[0]
    assert count == 1
