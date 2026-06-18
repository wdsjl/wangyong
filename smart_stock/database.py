"""本地 SQLite 数据库。"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

DEFAULT_DB_DIR = Path("data")
DEFAULT_DB_NAME = "smart_stock.db"
SCHEMA_VERSION = 1

_init_lock = Lock()
_initialized_paths: set[str] = set()
_db_path_override: Path | None = None


def set_db_path(path: str | Path | None) -> Path | None:
    """设置全局数据库路径（测试或 CLI 启动时调用）。"""
    global _db_path_override
    if path is None:
        _db_path_override = None
        return None
    resolved = Path(path).expanduser().resolve()
    _db_path_override = resolved
    return resolved


def get_db_path() -> Path:
    if _db_path_override is not None:
        return _db_path_override
    env = os.environ.get("SMART_STOCK_DB")
    if env:
        return Path(env).expanduser().resolve()
    return (DEFAULT_DB_DIR / DEFAULT_DB_NAME).resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    code TEXT PRIMARY KEY,
    name TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    monitor_enabled INTEGER NOT NULL DEFAULT 1,
    interval_sec INTEGER NOT NULL DEFAULT 60,
    notify_enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signal_snapshots (
    code TEXT PRIMARY KEY,
    signal TEXT NOT NULL,
    signal_key TEXT NOT NULL,
    score REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signal_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    name TEXT,
    from_signal TEXT NOT NULL,
    to_signal TEXT NOT NULL,
    score REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    name TEXT,
    latest_price REAL,
    signal TEXT,
    signal_key TEXT,
    score REAL,
    data_source TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analysis_history_code ON analysis_history(code);
CREATE INDEX IF NOT EXISTS idx_signal_alerts_created ON signal_alerts(created_at DESC);

CREATE TABLE IF NOT EXISTS strategy_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> Path:
    path = db_path or get_db_path()
    key = str(path)
    with _init_lock:
        if key in _initialized_paths:
            return path
        with get_connection(path) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.execute(
                "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, _utc_now()),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO monitor_settings(
                    id, monitor_enabled, interval_sec, notify_enabled, updated_at
                ) VALUES (1, 1, 60, 0, ?)
                """,
                (_utc_now(),),
            )
        _initialized_paths.add(key)
    return path


def reset_db_cache() -> None:
    """清空初始化缓存（仅测试使用）。"""
    with _init_lock:
        _initialized_paths.clear()


@dataclass
class WatchlistItem:
    code: str
    name: str | None = None
    sort_order: int = 0
    added_at: str | None = None


@dataclass
class MonitorSettings:
    monitor_enabled: bool = True
    interval_sec: int = 60
    notify_enabled: bool = False
    updated_at: str | None = None


@dataclass
class SignalAlert:
    id: int
    code: str
    name: str | None
    from_signal: str
    to_signal: str
    score: float
    created_at: str


def get_strategy_settings(db_path: Path | None = None) -> dict[str, Any]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT payload_json, updated_at FROM strategy_settings WHERE id = 1"
        ).fetchone()
    if row is None:
        from smart_stock.strategy_profile import DEFAULT_STRATEGY_PROFILE

        return {**DEFAULT_STRATEGY_PROFILE.to_dict(), "updated_at": None}
    payload = json.loads(str(row["payload_json"]))
    payload["updated_at"] = row["updated_at"]
    return payload


def save_strategy_settings(payload: dict[str, Any], db_path: Path | None = None) -> dict[str, Any]:
    init_db(db_path)
    now = _utc_now()
    clean = {key: value for key, value in payload.items() if key != "updated_at"}
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO strategy_settings(id, payload_json, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (json.dumps(clean, ensure_ascii=False), now),
        )
    return {**clean, "updated_at": now}


def list_watchlist_codes(db_path: Path | None = None) -> list[str]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT code FROM watchlist ORDER BY sort_order ASC, added_at ASC"
        ).fetchall()
    return [str(row["code"]) for row in rows]


def replace_watchlist(codes: list[str], db_path: Path | None = None) -> list[str]:
    init_db(db_path)
    normalized = []
    seen: set[str] = set()
    for code in codes:
        digits = "".join(ch for ch in str(code) if ch.isdigit())
        if not digits or digits in seen:
            continue
        seen.add(digits)
        normalized.append(digits)

    now = _utc_now()
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM watchlist")
        for index, code in enumerate(normalized):
            conn.execute(
                """
                INSERT INTO watchlist(code, name, sort_order, added_at)
                VALUES (?, NULL, ?, ?)
                """,
                (code, index, now),
            )
    return normalized


def get_monitor_settings(db_path: Path | None = None) -> MonitorSettings:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT monitor_enabled, interval_sec, notify_enabled, updated_at
            FROM monitor_settings WHERE id = 1
            """
        ).fetchone()
    if row is None:
        return MonitorSettings()
    return MonitorSettings(
        monitor_enabled=bool(row["monitor_enabled"]),
        interval_sec=int(row["interval_sec"]),
        notify_enabled=bool(row["notify_enabled"]),
        updated_at=str(row["updated_at"]),
    )


def save_monitor_settings(
    *,
    monitor_enabled: bool,
    interval_sec: int,
    notify_enabled: bool,
    db_path: Path | None = None,
) -> MonitorSettings:
    init_db(db_path)
    now = _utc_now()
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO monitor_settings(id, monitor_enabled, interval_sec, notify_enabled, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                monitor_enabled = excluded.monitor_enabled,
                interval_sec = excluded.interval_sec,
                notify_enabled = excluded.notify_enabled,
                updated_at = excluded.updated_at
            """,
            (int(monitor_enabled), interval_sec, int(notify_enabled), now),
        )
    return MonitorSettings(
        monitor_enabled=monitor_enabled,
        interval_sec=interval_sec,
        notify_enabled=notify_enabled,
        updated_at=now,
    )


def _load_signal_snapshots(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        "SELECT code, signal, signal_key, score, updated_at FROM signal_snapshots"
    ).fetchall()
    return {
        str(row["code"]): {
            "signal": row["signal"],
            "signal_key": row["signal_key"],
            "score": float(row["score"]),
            "updated_at": row["updated_at"],
        }
        for row in rows
    }


def record_batch_analysis(
    items: list[dict[str, Any]],
    *,
    detect_changes: bool = False,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """保存批量分析结果，更新信号快照，并按需记录告警。"""
    init_db(db_path)
    alerts: list[dict[str, Any]] = []
    now = _utc_now()

    with get_connection(db_path) as conn:
        previous = _load_signal_snapshots(conn) if detect_changes else {}

        for item in items:
            code = str(item.get("code", ""))
            if not code:
                continue
            signal = item.get("signal") or {}
            signal_value = str(signal.get("value", ""))
            signal_key = str(signal.get("key", ""))
            score = float(item.get("score", 0))
            name = item.get("name")

            if detect_changes:
                prev = previous.get(code)
                if prev and prev["signal"] != signal_value:
                    conn.execute(
                        """
                        INSERT INTO signal_alerts(
                            code, name, from_signal, to_signal, score, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (code, name, prev["signal"], signal_value, score, now),
                    )
                    alerts.append(
                        {
                            "code": code,
                            "name": name,
                            "from": prev["signal"],
                            "to": signal_value,
                            "score": score,
                        }
                    )

            conn.execute(
                """
                INSERT INTO signal_snapshots(code, signal, signal_key, score, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    signal = excluded.signal,
                    signal_key = excluded.signal_key,
                    score = excluded.score,
                    updated_at = excluded.updated_at
                """,
                (code, signal_value, signal_key, score, now),
            )

    return alerts


def list_signal_alerts(limit: int = 50, db_path: Path | None = None) -> list[SignalAlert]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, code, name, from_signal, to_signal, score, created_at
            FROM signal_alerts
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(limit, 200)),),
        ).fetchall()
    return [
        SignalAlert(
            id=int(row["id"]),
            code=str(row["code"]),
            name=row["name"],
            from_signal=str(row["from_signal"]),
            to_signal=str(row["to_signal"]),
            score=float(row["score"]),
            created_at=str(row["created_at"]),
        )
        for row in rows
    ]


def save_analysis_history(
    payload: dict[str, Any],
    *,
    data_source: str = "live",
    db_path: Path | None = None,
) -> int:
    init_db(db_path)
    analysis = payload.get("analysis") or {}
    signal = analysis.get("signal") or {}
    now = _utc_now()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO analysis_history(
                code, name, latest_price, signal, signal_key, score, data_source, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis.get("code"),
                analysis.get("name"),
                analysis.get("latest_price"),
                signal.get("value"),
                signal.get("key"),
                analysis.get("score"),
                data_source,
                json.dumps(payload, ensure_ascii=False),
                now,
            ),
        )
        return int(cursor.lastrowid)


def get_signal_snapshots(db_path: Path | None = None) -> dict[str, dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        return _load_signal_snapshots(conn)
