"""命令行入口。"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from smart_stock.analyzer import analyze_many, analyze_stock, search_stock
from smart_stock.network import diagnose_network
from smart_stock.backtest import BacktestConfig, run_backtest
from smart_stock.llm_insight import generate_insight
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
        f"最新价: [cyan]{result.latest_price:.2f}[/cyan] ({result.price_label})  "
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


def render_backtest_result(payload: dict) -> None:
    table = Table(title=f"策略回测 · {payload['name']} ({payload['code']})")
    table.add_column("指标", style="cyan")
    table.add_column("数值", justify="right")
    metrics = [
        ("回测区间", f"{payload['start_date']} ~ {payload['end_date']}"),
        ("初始资金", f"{payload['initial_capital']:,.2f}"),
        ("期末权益", f"{payload['final_equity']:,.2f}"),
        ("策略收益", f"{payload['total_return_pct']:+.2f}%"),
        ("基准收益", f"{payload['benchmark_return_pct']:+.2f}%"),
        ("超额收益", f"{payload['excess_return_pct']:+.2f}%"),
        ("最大回撤", f"{payload['max_drawdown_pct']:.2f}%"),
        ("胜率", f"{payload['win_rate_pct']:.2f}%"),
        ("交易次数", str(payload["trade_count"])),
        ("夏普比率", "-" if payload["sharpe_ratio"] is None else f"{payload['sharpe_ratio']:.2f}"),
    ]
    for label, value in metrics:
        table.add_row(label, value)
    console.print(table)
    console.print(f"[dim]{payload['risk_note']}[/dim]")


def render_insight(payload: dict) -> None:
    mode = "大模型" if payload["mode"] == "llm" else "演示规则"
    console.print(Panel(payload["content"], title=f"AI 解读 · {payload['name']} ({payload['code']}) · {mode}"))
    if payload.get("news"):
        console.print("[bold]参考新闻[/bold]")
        for item in payload["news"]:
            console.print(f"- [{item['published_at']}] {item['title']} ({item['source']})")
    console.print(f"[dim]{payload['disclaimer']}[/dim]")


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

    backtest_parser = subparsers.add_parser("backtest", help="策略回测")
    backtest_parser.add_argument("code", help="股票代码")
    backtest_parser.add_argument("--days", type=int, default=180, help="回测交易日数量")
    backtest_parser.add_argument("--capital", type=float, default=100000, help="初始资金")

    insight_parser = subparsers.add_parser("insight", help="AI 解读财报/新闻")
    insight_parser.add_argument("code", help="股票代码")
    insight_parser.add_argument("--days", type=int, default=120, help="技术分析回看天数")

    subparsers.add_parser("check-network", help="检测行情接口网络连通性")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            result = analyze_stock(
                args.code,
                days=args.days,
                demo=args.demo,
                allow_fallback=not args.demo,
            )
            render_analysis(result)
        elif args.command == "search":
            results = search_stock(args.keyword, limit=args.limit, demo=args.demo)
            if results.empty:
                console.print("[yellow]未找到匹配股票[/yellow]")
                return 1
            render_search_results(results)
        elif args.command == "batch":
            results = analyze_many(
                args.codes,
                days=args.days,
                demo=args.demo,
                allow_fallback=not args.demo,
            )
            render_batch_results(results)
        elif args.command == "backtest":
            result = run_backtest(
                args.code,
                days=args.days,
                demo=args.demo,
                backtest_config=BacktestConfig(initial_capital=args.capital),
            )
            from smart_stock.serializers import backtest_to_dict

            render_backtest_result(backtest_to_dict(result))
        elif args.command == "insight":
            payload = generate_insight(args.code, days=args.days, demo=args.demo)
            render_insight(payload)
        elif args.command == "check-network":
            for line in diagnose_network():
                console.print(line)
    except Exception as exc:  # noqa: BLE001 - CLI 需要统一展示错误
        console.print(f"[red]执行失败: {exc}[/red]")
        console.print("[dim]提示: 可尝试添加 --demo 参数使用本地演示数据[/dim]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
