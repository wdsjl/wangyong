"""行情回退逻辑测试。"""

from smart_stock.data import fetch_daily_bars_safe


def test_fetch_daily_bars_safe_demo():
    bars, source = fetch_daily_bars_safe("600519", days=30, demo=True)
    assert source == "demo"
    assert len(bars) == 30


def test_fetch_daily_bars_safe_fallback():
    bars, source = fetch_daily_bars_safe(
        "600519",
        days=30,
        demo=False,
        allow_fallback=True,
    )
    assert source in {"live", "demo_fallback"}
    assert len(bars) == 30
