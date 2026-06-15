#!/usr/bin/env python3
"""启动 Web 可视化面板。"""

from __future__ import annotations

import argparse

import uvicorn

from smart_stock.web.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="启动智能炒股 Web 面板")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--demo", action="store_true", help="使用演示数据")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")
    args = parser.parse_args()

    app = create_app(demo=args.demo)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
