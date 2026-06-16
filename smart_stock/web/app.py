"""FastAPI Web 应用。"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from smart_stock.service import (
    backtest_stock,
    batch_analyze,
    check_live_data_available,
    compare_stocks,
    detail_to_dict,
    get_stock_detail,
    search_stocks,
    stock_insight,
)
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

STATIC_DIR = Path(__file__).resolve().parent / "static"


class WatchlistPayload(BaseModel):
    codes: list[str] = Field(default_factory=list)


class MonitorSettingsPayload(BaseModel):
    monitor_enabled: bool = True
    interval_sec: int = Field(60, ge=15, le=3600)
    notify_enabled: bool = False


def create_app(demo: bool = False, db_path: str | Path | None = None) -> FastAPI:
    resolved_db = init_store(db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app = FastAPI(
        title="智能炒股",
        description="A 股智能分析 Web 面板",
        version="0.3.0",
        lifespan=lifespan,
    )
    app.state.demo = demo
    app.state.db_path = resolved_db
    app.state._live_ok_cache: tuple[bool, float] | None = None

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True, "demo": app.state.demo}

    @app.get("/api/config")
    async def get_config() -> dict:
        live_ok = bool(app.state.demo)
        if not app.state.demo:
            live_ok = _get_cached_live_ok(app)
        return {
            "demo": app.state.demo,
            "live_data_ok": live_ok,
            "database": str(app.state.db_path),
        }

    @app.get("/api/watchlist")
    async def api_get_watchlist() -> dict:
        return get_watchlist()

    @app.put("/api/watchlist")
    async def api_put_watchlist(payload: WatchlistPayload) -> dict:
        return put_watchlist(payload.codes)

    @app.get("/api/monitor-settings")
    async def api_get_monitor_settings() -> dict:
        return get_monitor_settings()

    @app.put("/api/monitor-settings")
    async def api_put_monitor_settings(payload: MonitorSettingsPayload) -> dict:
        return put_monitor_settings(
            monitor_enabled=payload.monitor_enabled,
            interval_sec=payload.interval_sec,
            notify_enabled=payload.notify_enabled,
        )

    @app.get("/api/alerts")
    async def api_alerts(limit: int = Query(50, ge=1, le=200)) -> dict:
        return list_alerts(limit=limit)

    @app.get("/api/search")
    async def api_search(
        keyword: str = Query(..., min_length=1),
        limit: int = Query(10, ge=1, le=50),
        demo: bool | None = None,
    ) -> dict:
        use_demo = app.state.demo if demo is None else demo
        items = search_stocks(keyword, limit=limit, demo=use_demo)
        return {"items": items, "demo": use_demo}

    @app.get("/api/analyze/{code}")
    async def api_analyze(
        code: str,
        days: int = Query(120, ge=30, le=365),
        demo: bool | None = None,
    ) -> dict:
        use_demo = app.state.demo if demo is None else demo
        try:
            detail = get_stock_detail(
                code,
                days=days,
                demo=use_demo,
                allow_fallback=not use_demo,
            )
        except Exception as exc:  # noqa: BLE001 - 统一转换为 HTTP 错误
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        payload = detail_to_dict(detail)
        payload["demo"] = use_demo or detail.data_source != "live"
        record_analysis(payload, data_source=detail.data_source)
        return payload

    @app.get("/api/batch")
    async def api_batch(
        codes: str = Query(..., description="逗号分隔的股票代码"),
        days: int = Query(120, ge=30, le=365),
        demo: bool | None = None,
        detect_changes: bool = Query(False, description="检测信号变化并写入告警历史"),
    ) -> dict:
        use_demo = app.state.demo if demo is None else demo
        code_list = [item.strip() for item in codes.split(",") if item.strip()]
        if not code_list:
            raise HTTPException(status_code=400, detail="请至少提供一个股票代码")
        items = batch_analyze(code_list, days=days, demo=use_demo, allow_fallback=not use_demo)
        alerts = record_batch(items, detect_changes=detect_changes)
        return {"items": items, "alerts": alerts, "demo": use_demo}

    @app.get("/api/compare")
    async def api_compare(
        codes: str = Query(..., description="逗号分隔的股票代码"),
        days: int = Query(120, ge=30, le=365),
        demo: bool | None = None,
    ) -> dict:
        use_demo = app.state.demo if demo is None else demo
        code_list = [item.strip() for item in codes.split(",") if item.strip()]
        if len(code_list) < 2:
            raise HTTPException(status_code=400, detail="请至少提供两只股票进行对比")
        series = compare_stocks(code_list, days=days, demo=use_demo, allow_fallback=not use_demo)
        if len(series) < 2:
            raise HTTPException(status_code=400, detail="有效股票不足，无法生成对比图")
        return {"series": series, "demo": use_demo}

    @app.get("/api/backtest/{code}")
    async def api_backtest(
        code: str,
        days: int = Query(180, ge=90, le=365),
        capital: float = Query(100000, ge=10000, le=10_000_000),
        demo: bool | None = None,
    ) -> dict:
        use_demo = app.state.demo if demo is None else demo
        try:
            payload = backtest_stock(code, days=days, demo=use_demo, initial_capital=capital)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        payload["demo"] = use_demo
        return payload

    @app.get("/api/insight/{code}")
    async def api_insight(
        code: str,
        days: int = Query(120, ge=30, le=365),
        demo: bool | None = None,
    ) -> dict:
        use_demo = app.state.demo if demo is None else demo
        try:
            payload = stock_insight(code, days=days, demo=use_demo)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        payload["demo"] = use_demo
        return payload

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def _get_cached_live_ok(app: FastAPI, ttl_seconds: float = 120.0) -> bool:
    now = time.time()
    cache = getattr(app.state, "_live_ok_cache", None)
    if cache and now - cache[1] < ttl_seconds:
        return cache[0]
    live_ok = check_live_data_available(quick=True)
    app.state._live_ok_cache = (live_ok, now)
    return live_ok
