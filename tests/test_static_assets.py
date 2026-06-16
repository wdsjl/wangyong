"""前端静态资源测试。"""

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "smart_stock" / "web" / "static"


def test_chart_vendor_files_exist():
    vendor = STATIC_DIR / "vendor"
    for name in (
        "chart.umd.min.js",
        "hammer.min.js",
        "chartjs-chart-financial.min.js",
        "chartjs-plugin-zoom.min.js",
    ):
        assert (vendor / name).exists(), f"缺少图表库文件: {name}"


def test_index_uses_local_vendor_scripts():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "/static/vendor/chart.umd.min.js" in html
    assert "cdn.jsdelivr.net" not in html
