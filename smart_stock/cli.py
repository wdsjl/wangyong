"""命令行入口。"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from smart_stock.analyzer import analyze_many, analyze_stock, search_stock
from smart_stock.models import AnalysisResult, Signal

console = Console()


SIGNAL_STYLE = {
    Signal.STRONG_BUY: "bold green",
    Signal.BUY: "green",
    Signal.HOLD: "yellow",
    Signal.SELL: "red",
    Signal.STRONG_SELL: "bold red",
}


def render_analysis(result: AnalysisResult) -> None:
    """渲染单只股票分析结果。"""
    style = SIGNAL_STYLE.get(result.signal, "white")
    header = (
        f"[bold]{result.name} ({result.code})[/bold]\n"
        f"最新价: [cyan]{result.latest_price:.2f}[/cyan]  "
        f"日期: {result.latest_date}\n"
        f"信号: [{style}]{result.signal.value}[/]  "
        f"综合评分: [bold]{result.score:+.3f}[/bold]"
    )
    reason_text = "\n".join(f"- {reason}" for reason in result.reasons) or "- 暂无额外说明"
    indicator_text = _format_indicators(result)
    console.print(Panel(f"{header}\n\n[bold]分析依据[/bold]\n{reason_text}\n\n{indicator_text}"))
    console.print(f"[dim]{result.risk_note}[/dim]")


def _format_indicators(result: AnalysisResult) -> str:
    indicators = result.indicators
    if indicators is None:
        return ""

    return (
        "[bold]关键指标[/bold]\n"
        f"- MA5/10/20/60: {_fmt(indicators.ma5)} / {_fmt(indicators.ma10)} / "
        f"{_fmt(indicators.ma20)} / {_fmt(indicators.ma60)}\n"
        f"- RSI: {_fmt(indicators.rsi)}\n"
        f"- MACD: {_fmt(indicators.macd)}  信号线: {_fmt(indicators.macd_signal)}  "
        f"柱: {_fmt(indicators.macd_hist)}\n"
        f"- 布林带: 上 {_fmt(indicators.boll_upper)} / 中 {_fmt(indicators.boll_middle)} / "
        f"下 {_fmt(indicators.boll_lower)}"
    )


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "-"


def render_search_results(df) -> None:
    table = Table(title="股票搜索结果")
    table.add_column("代码", style="cyan")
    table.add_column("名称")
    for _, row in df.iterrows():
        table.add_row(str(row["代码"]), str(row["名称"]))
    console.print(table)


def render_batch_results(results: list[AnalysisResult]) -> None:
    table = Table(title="批量智能分析")
    table.add_column("代码", style="cyan")
    table.add_column("名称")
    table.add_column("最新价", justify="right")
    table.add_column("信号")
    table.add_column("评分", justify="right")

    for result in sorted(results, key=lambda item: item.score, reverse=True):
        style = SIGNAL_STYLE.get(result.signal, "white")
        table.add_row(
            result.code,
            result.name,
            f"{result.latest_price:.2f}" if result.latest_price else "-",
            f"[{style}]{result.signal.value}[/]",
            f"{result.score:+.3f}",
        )
    console.print(table)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smart-stock",
        description="智能炒股分析系统：基于技术指标的多因子 A 股信号分析",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="使用本地演示数据（网络不可用时推荐）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="分析单只股票")
    analyze_parser.add_argument("code", help="股票代码，如 600519")
    analyze_parser.add_argument("--days", type=int, default=120, help="回看交易日数量")

    search_parser = subparsers.add_parser("search", help="搜索股票")
    search_parser.add_argument("keyword", help="代码或名称关键词")
    search_parser.add_argument("--limit", type=int, default=10, help="返回条数")

    batch_parser = subparsers.add_parser("batch", help="批量分析")
    batch_parser.add_argument("codes", nargs="+", help="多个股票代码")
    batch_parser.add_argument("--days", type=int, default=120, help="回看交易日数量")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            result = analyze_stock(args.code, days=args.days, demo=args.demo)
            render_analysis(result)
        elif args.command == "search":
            results = search_stock(args.keyword, limit=args.limit, demo=args.demo)
            if results.empty:
                console.print("[yellow]未找到匹配股票[/yellow]")
                return 1
            render_search_results(results)
        elif args.command == "batch":
            results = analyze_many(args.codes, days=args.days, demo=args.demo)
            render_batch_results(results)
    except Exception as exc:  # noqa: BLE001 - CLI 需要统一展示错误
        console.print(f"[red]执行失败: {exc}[/red]")
        console.print("[dim]提示: 可尝试添加 --demo 参数使用本地演示数据[/dim]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
