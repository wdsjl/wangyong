"""盯盘信号单元测试。"""

from smart_stock.indicators import enrich_indicators, latest_indicator_snapshot
from smart_stock.sample_data import generate_demo_bars
from smart_stock.signals import compute_monitoring_snapshot, compute_resonance, compute_trend_score


def test_new_indicators_present():
    enriched = enrich_indicators(generate_demo_bars("600519", days=150))
    snapshot = latest_indicator_snapshot(enriched)
    assert snapshot.obv is not None
    assert snapshot.atr is not None
    assert snapshot.vma5 is not None
    assert snapshot.ma120 is not None


def test_trend_score_range():
    enriched = enrich_indicators(generate_demo_bars("000815", days=150))
    snapshot = latest_indicator_snapshot(enriched)
    price = float(enriched.iloc[-1]["close"])
    score, label = compute_trend_score(price, snapshot)
    assert 0 <= score <= 100
    assert label


def test_monitoring_snapshot():
    enriched = enrich_indicators(generate_demo_bars("000001", days=150))
    snapshot = latest_indicator_snapshot(enriched)
    monitoring = compute_monitoring_snapshot(enriched, snapshot)
    assert monitoring.trend_score >= 0
    assert monitoring.resonance_level in {"none", "weak", "strong"}
    assert isinstance(monitoring.alerts, list)


def test_resonance_returns_hits():
    enriched = enrich_indicators(generate_demo_bars("300750", days=150))
    snapshot = latest_indicator_snapshot(enriched)
    price = float(enriched.iloc[-1]["close"])
    level, side, hits, score = compute_resonance(enriched, snapshot, price)
    assert level in {"none", "weak", "strong"}
    assert side in {"bullish", "bearish", "neutral"}
    assert isinstance(hits, list)
    assert 0 <= score <= 100
