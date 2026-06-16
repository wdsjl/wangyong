"""核心逻辑单元测试（无需网络）。"""

import pandas as pd

from smart_stock.indicators import enrich_indicators, latest_indicator_snapshot
from smart_stock.models import Signal
from smart_stock.sample_data import generate_demo_bars, search_demo_stocks
from smart_stock.strategy import compute_trade_markers, generate_signal


def test_demo_search():
    result = search_demo_stocks("茅台")
    assert not result.empty
    assert result.iloc[0]["代码"] == "600519"


def test_indicator_pipeline():
    bars = generate_demo_bars("600519", days=120)
    enriched = enrich_indicators(bars)
    snapshot = latest_indicator_snapshot(enriched)

    assert snapshot.ma5 is not None
    assert snapshot.rsi is not None
    assert snapshot.macd is not None
    assert snapshot.boll_upper is not None


def test_signal_generation():
    bars = generate_demo_bars("000001", days=120)
    enriched = enrich_indicators(bars)
    snapshot = latest_indicator_snapshot(enriched)
    signal, score, reasons = generate_signal(enriched, snapshot)

    assert isinstance(signal, Signal)
    assert isinstance(score, float)
    assert isinstance(reasons, list)
    assert len(enriched) == 120


def test_compute_trade_markers():
    bars = generate_demo_bars("000815", days=120)
    enriched = enrich_indicators(bars)
    markers = compute_trade_markers(enriched, warmup_days=30)
    assert "buy_markers" in markers
    assert "sell_markers" in markers
    assert isinstance(markers["buy_markers"], list)
    assert isinstance(markers["sell_markers"], list)


def test_analyze_stock_demo():
    from smart_stock.analyzer import analyze_stock

    result = analyze_stock("600519", demo=True)
    assert result.code == "600519"
    assert result.latest_price > 0
    assert result.signal in Signal
