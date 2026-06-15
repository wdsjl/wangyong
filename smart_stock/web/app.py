"""FastAPI Web 应用。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from smart_stock.service import batch_analyze, compare_stocks, detail_to_dict, get_stock_detail, search_stocks

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(demo: bool = False) -> FastAPI:
    app = FastAPI(
        title="智能炒股",
        description="A 股智能分析 Web 面板",
        version="0.2.0",
    )
    app.state.demo = demo

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/config")
    async def get_config() -> dict[str, bool]:
        return {"demo": app.state.demo}

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
            detail = get_stock_detail(code, days=days, demo=use_demo)
        except Exception as exc:  # noqa: BLE001 - 统一转换为 HTTP 错误
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        payload = detail_to_dict(detail)
        payload["demo"] = use_demo
        return payload

    @app.get("/api/batch")
    async def api_batch(
        codes: str = Query(..., description="逗号分隔的股票代码"),
        days: int = Query(120, ge=30, le=365),
        demo: bool | None = None,
    ) -> dict:
        use_demo = app.state.demo if demo is None else demo
        code_list = [item.strip() for item in codes.split(",") if item.strip()]
        if not code_list:
            raise HTTPException(status_code=400, detail="请至少提供一个股票代码")
        items = batch_analyze(code_list, days=days, demo=use_demo)
        return {"items": items, "demo": use_demo}

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
        series = compare_stocks(code_list, days=days, demo=use_demo)
        if len(series) < 2:
            raise HTTPException(status_code=400, detail="有效股票不足，无法生成对比图")
        return {"series": series, "demo": use_demo}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
