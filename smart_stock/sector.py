"""板块情绪与行业归属。"""

from __future__ import annotations

import hashlib

from smart_stock.models import SectorSnapshot

# 常见 A 股行业映射（演示/离线兜底）
SECTOR_BY_CODE: dict[str, tuple[str, str]] = {
    "600519": ("白酒", "BK0896"),
    "000001": ("银行", "BK0475"),
    "000815": ("云计算", "BK0922"),
    "300750": ("电池", "BK1033"),
    "601318": ("保险", "BK0474"),
    "600036": ("银行", "BK0475"),
    "601012": ("光伏", "BK1031"),
    "300059": ("证券", "BK0473"),
}

# 行业代码 → 行业名称（用于演示板块涨跌）
SECTOR_NAMES = {code: name for name, code in ((v[0], v[1]) for v in SECTOR_BY_CODE.values())}


def _demo_sector_for_code(code: str) -> tuple[str, str]:
    sectors = list({item[0]: item[1] for item in SECTOR_BY_CODE.values()}.items())
    index = int(hashlib.md5(code.encode()).hexdigest()[:4], 16) % len(sectors)
    name, sector_code = sectors[index]
    return name, sector_code


def resolve_sector(code: str) -> tuple[str, str]:
    normalized = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    if normalized in SECTOR_BY_CODE:
        return SECTOR_BY_CODE[normalized]
    return _demo_sector_for_code(normalized)


def fetch_sector_sentiment(code: str, *, demo: bool = False) -> SectorSnapshot:
    """获取个股所属板块及情绪评分。"""
    sector_name, sector_code = resolve_sector(code)
    seed = int(hashlib.md5(f"{code}:{sector_code}".encode()).hexdigest()[:8], 16)

    if demo:
        change_pct = round(((seed % 401) - 200) / 100, 2)
        up_ratio = round(35 + (seed % 40), 1)
        source = "demo"
    else:
        try:
            from smart_stock.eastmoney import fetch_sector_quote

            quote = fetch_sector_quote(sector_code)
            if quote:
                return SectorSnapshot(
                    sector_name=sector_name,
                    sector_code=sector_code,
                    change_pct=quote.change_pct,
                    up_ratio=quote.up_ratio,
                    sentiment_score=quote.sentiment_score,
                    sentiment_label=quote.sentiment_label,
                    source="live",
                )
        except Exception:
            pass
        change_pct = round(((seed % 301) - 150) / 100, 2)
        up_ratio = round(40 + (seed % 35), 1)
        source = "fallback"

    sentiment_score = int(round(50 + change_pct * 8 + (up_ratio - 50) * 0.3))
    sentiment_score = max(0, min(100, sentiment_score))

    if sentiment_score >= 65:
        label = "板块偏强"
    elif sentiment_score <= 35:
        label = "板块偏弱"
    else:
        label = "板块中性"

    return SectorSnapshot(
        sector_name=sector_name,
        sector_code=sector_code,
        change_pct=change_pct,
        up_ratio=up_ratio,
        sentiment_score=sentiment_score,
        sentiment_label=label,
        source=source,
    )
