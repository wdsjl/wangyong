#!/usr/bin/env python3
"""启动 Web 可视化面板。"""

from __future__ import annotations

import argparse
import socket
import sys

import uvicorn

from smart_stock.web.app import create_app


def ensure_port_available(host: str, port: int) -> None:
    """启动前检测端口，避免 uvicorn 静默失败。"""
    check_host = "127.0.0.1" if host in {"0.0.0.0", ""} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((check_host, port))
        except OSError as exc:
            in_use = exc.errno in {48, 98} or getattr(exc, "winerror", None) == 10048
            if not in_use:
                raise
            raise SystemExit(
                f"\n端口 {port} 已被占用，Web 服务无法启动。\n\n"
                f"请尝试：\n"
                f"  1. 关闭之前未退出的 web_main.py 窗口\n"
                f"  2. Windows 查看占用：netstat -ano | findstr :{port}\n"
                f"     结束进程：taskkill /PID <进程号> /F\n"
                f"  3. 换端口：python web_main.py --port 8001\n"
                f"  4. 浏览器访问：http://127.0.0.1:8001\n"
            ) from exc


def print_startup_banner(host: str, port: int) -> None:
    local_url = f"http://127.0.0.1:{port}"
    print("\n智能炒股 Web 面板")
    print(f"  本机访问：{local_url}")
    if host == "0.0.0.0":
        print(f"  局域网访问：http://<你的IP>:{port}")
    print("  按 Ctrl+C 停止服务\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="启动智能炒股 Web 面板")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--demo", action="store_true", help="使用演示数据")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite 数据库路径（默认 data/smart_stock.db，也可用环境变量 SMART_STOCK_DB）",
    )
    args = parser.parse_args()

    if args.reload:
        print("提示：--reload 模式下端口占用检测已跳过", file=sys.stderr)
    else:
        ensure_port_available(args.host, args.port)

    app = create_app(demo=args.demo, db_path=args.db)
    print_startup_banner(args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
