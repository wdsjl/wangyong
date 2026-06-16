"""数据库持久化服务。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smart_stock import database as db


def init_store(db_path: str | Path | None = None) -> Path:
    path = db.set_db_path(db_path)
    return db.init_db(path)


def get_watchlist() -> dict[str, Any]:
    codes = db.list_watchlist_codes()
    return {"codes": codes}


def put_watchlist(codes: list[str]) -> dict[str, Any]:
    saved = db.replace_watchlist(codes)
    return {"codes": saved}


def get_monitor_settings() -> dict[str, Any]:
    settings = db.get_monitor_settings()
    return {
        "monitor_enabled": settings.monitor_enabled,
        "interval_sec": settings.interval_sec,
        "notify_enabled": settings.notify_enabled,
        "updated_at": settings.updated_at,
    }


def put_monitor_settings(
    *,
    monitor_enabled: bool,
    interval_sec: int,
    notify_enabled: bool,
) -> dict[str, Any]:
    settings = db.save_monitor_settings(
        monitor_enabled=monitor_enabled,
        interval_sec=interval_sec,
        notify_enabled=notify_enabled,
    )
    return {
        "monitor_enabled": settings.monitor_enabled,
        "interval_sec": settings.interval_sec,
        "notify_enabled": settings.notify_enabled,
        "updated_at": settings.updated_at,
    }


def record_batch(items: list[dict[str, Any]], *, detect_changes: bool = False) -> list[dict[str, Any]]:
    return db.record_batch_analysis(items, detect_changes=detect_changes)


def list_alerts(limit: int = 50) -> dict[str, Any]:
    alerts = db.list_signal_alerts(limit=limit)
    return {
        "items": [
            {
                "id": alert.id,
                "code": alert.code,
                "name": alert.name,
                "from": alert.from_signal,
                "to": alert.to_signal,
                "score": alert.score,
                "created_at": alert.created_at,
            }
            for alert in alerts
        ]
    }


def record_analysis(payload: dict[str, Any], *, data_source: str = "live") -> None:
    db.save_analysis_history(payload, data_source=data_source)
