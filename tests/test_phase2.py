"""第二期指标与筹码测试。"""

from smart_stock.chip import compute_chip_distribution
from smart_stock.fundamentals import fetch_fundamental_snapshot, fetch_northbound_snapshot
from smart_stock.indicators import enrich_indicators, latest_indicator_snapshot
from smart_stock.sample_data import generate_demo_bars
from smart_stock.signals import _momentum_resonance, _trend_regime


def test_phase2_indicators():
    enriched = enrich_indicators(generate_demo_bars("600519", days=150))
    snapshot = latest_indicator_snapshot(enriched)
    for field in ("kdj_k", "cci", "wr", "mfi", "adx"):
        assert getattr(snapshot, field) is not None


def test_chip_distribution():
    enriched = enrich_indicators(generate_demo_bars("000815", days=120))
    chip = compute_chip_distribution(enriched)
    assert chip.avg_cost is not None
    assert chip.profit_ratio is not None
    assert chip.support_price is not None


def test_fundamental_demo():
    fundamentals = fetch_fundamental_snapshot("600519", demo=True)
    assert fundamentals.pe_ttm is not None
    assert fundamentals.valuation_label


def test_northbound_demo():
    north = fetch_northbound_snapshot("600519", demo=True)
    assert north.eligible is True
    assert north.net_inflow_today is not None


def test_trend_regime_and_momentum():
    enriched = enrich_indicators(generate_demo_bars("000001", days=150))
    snapshot = latest_indicator_snapshot(enriched)
    assert _trend_regime(snapshot.adx) in {"趋势市", "震荡市", "过渡区", "未知"}
    assert _momentum_resonance(snapshot) in {"无", "超卖共振", "超买共振"}
