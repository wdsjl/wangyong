"""股票新闻与资讯获取。"""

from __future__ import annotations

from dataclasses import dataclass

from smart_stock.data import normalize_code
from smart_stock.sample_data import get_demo_name

try:
    import akshare as ak
except ImportError:  # pragma: no cover
    ak = None


@dataclass
class NewsItem:
    title: str
    source: str
    published_at: str
    summary: str
    url: str = ""


DEMO_NEWS: dict[str, list[dict[str, str]]] = {
    "600519": [
        {
            "title": "贵州茅台发布季度经营数据，营收保持稳健增长",
            "source": "证券时报",
            "published_at": "2026-06-10",
            "summary": "公司主营产品市场需求稳定，渠道库存处于合理区间。",
        },
        {
            "title": "白酒板块震荡走强，高端酒企估值修复",
            "source": "财联社",
            "published_at": "2026-06-08",
            "summary": "机构认为高端白酒长期景气度仍在，短期关注消费复苏节奏。",
        },
    ],
    "000001": [
        {
            "title": "平安银行推进零售转型，资产质量保持稳定",
            "source": "上海证券报",
            "published_at": "2026-06-09",
            "summary": "银行板块整体估值较低，息差压力仍需持续跟踪。",
        }
    ],
    "300750": [
        {
            "title": "宁德时代获海外动力电池大单",
            "source": "第一财经",
            "published_at": "2026-06-07",
            "summary": "新能源产业链需求回暖，关注原材料价格波动风险。",
        }
    ],
}


def _demo_news(code: str, limit: int) -> list[NewsItem]:
    name = get_demo_name(code)
    rows = DEMO_NEWS.get(
        code,
        [
            {
                "title": f"{name} 获机构调研关注",
                "source": "演示资讯",
                "published_at": "2026-06-05",
                "summary": "市场关注公司基本面变化与行业政策影响。",
            }
        ],
    )
    return [
        NewsItem(
            title=row["title"],
            source=row["source"],
            published_at=row["published_at"],
            summary=row["summary"],
        )
        for row in rows[:limit]
    ]


def fetch_stock_news(code: str, limit: int = 5, demo: bool = False) -> list[NewsItem]:
    """获取个股相关新闻。"""
    normalized_code = normalize_code(code)
    if demo:
        return _demo_news(normalized_code, limit)

    if ak is None:
        return _demo_news(normalized_code, limit)

    try:
        raw = ak.stock_news_em(symbol=normalized_code)
        if raw is None or raw.empty:
            return _demo_news(normalized_code, limit)

        items: list[NewsItem] = []
        for _, row in raw.head(limit).iterrows():
            items.append(
                NewsItem(
                    title=str(row.get("新闻标题", row.get("title", "未命名新闻"))),
                    source=str(row.get("文章来源", row.get("source", "未知来源"))),
                    published_at=str(row.get("发布时间", row.get("date", ""))),
                    summary=str(row.get("新闻内容", row.get("content", "")))[:180],
                    url=str(row.get("新闻链接", row.get("url", ""))),
                )
            )
        return items or _demo_news(normalized_code, limit)
    except Exception:
        return _demo_news(normalized_code, limit)
