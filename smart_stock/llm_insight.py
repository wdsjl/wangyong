"""大模型投研解读。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx

from smart_stock.analyzer import analyze_stock
from smart_stock.news import NewsItem, fetch_stock_news


@dataclass(frozen=True)
class LLMConfig:
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"


def load_llm_config() -> LLMConfig:
    return LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )


def _news_sentiment_hint(news_items: list[NewsItem]) -> str:
    positive_words = ("增长", "回暖", "修复", "大单", "稳健", "超预期")
    negative_words = ("下滑", "承压", "风险", "减持", "亏损", "调查")
    text = " ".join(item.title + item.summary for item in news_items)
    positive = sum(word in text for word in positive_words)
    negative = sum(word in text for word in negative_words)
    if positive > negative:
        return "新闻情绪偏正面"
    if negative > positive:
        return "新闻情绪偏谨慎"
    return "新闻情绪中性"


def _build_prompt(code: str, name: str, analysis, news_items: list[NewsItem]) -> str:
    news_text = "\n".join(
        f"- [{item.published_at}] {item.title}（{item.source}）：{item.summary}"
        for item in news_items
    )
    reasons = "\n".join(f"- {reason}" for reason in analysis.reasons)
    return f"""请基于以下信息，输出一份简洁的 A 股个股解读（300-500 字）：

股票：{name} ({code})
最新价：{analysis.latest_price}
交易信号：{analysis.signal.value}
综合评分：{analysis.score}
技术面依据：
{reasons}

近期新闻：
{news_text}

请按以下结构输出：
1. 技术面结论
2. 新闻与事件影响
3. 主要风险
4. 综合观点（不构成投资建议）
"""


def _generate_demo_insight(code: str, name: str, analysis, news_items: list[NewsItem]) -> dict:
    sentiment = _news_sentiment_hint(news_items)
    news_lines = [f"- {item.title}" for item in news_items[:3]]
    view = "偏多" if analysis.score >= 0.6 else "偏空" if analysis.score <= -0.6 else "中性"
    content = (
        f"## 技术面结论\n"
        f"{name}（{code}）当前信号为 **{analysis.signal.value}**，综合评分 {analysis.score:+.3f}，"
        f"短期技术判断{view}。关键依据包括：{'; '.join(analysis.reasons[:3])}。\n\n"
        f"## 新闻与事件影响\n"
        f"{sentiment}。近期关注：\n"
        + "\n".join(news_lines)
        + "\n\n"
        f"## 主要风险\n"
        f"- 技术指标基于历史行情，存在滞后性\n"
        f"- 新闻事件可能快速变化，需持续跟踪\n"
        f"- 单一策略信号不应作为独立决策依据\n\n"
        f"## 综合观点\n"
        f"当前更宜将其作为观察标的，结合仓位管理与基本面研究综合判断。"
    )
    return {
        "code": code,
        "name": name,
        "mode": "demo",
        "model": "rule-based",
        "content": content,
        "news": [_news_to_dict(item) for item in news_items],
        "disclaimer": "本解读仅供学习研究，不构成投资建议。",
    }


def _news_to_dict(item: NewsItem) -> dict:
    return {
        "title": item.title,
        "source": item.source,
        "published_at": item.published_at,
        "summary": item.summary,
        "url": item.url,
    }


def _call_llm(prompt: str, config: LLMConfig) -> str:
    endpoint = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": "你是专业的 A 股投研助手，回答要客观、结构化，并明确风险提示。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    response = httpx.post(endpoint, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return str(data["choices"][0]["message"]["content"]).strip()


def generate_insight(
    code: str,
    days: int = 120,
    demo: bool = False,
    news_limit: int = 5,
    llm_config: LLMConfig | None = None,
) -> dict:
    """生成技术面 + 新闻的大模型解读。"""
    analysis = analyze_stock(code, days=days, demo=demo)
    news_items = fetch_stock_news(analysis.code, limit=news_limit, demo=demo)
    config = llm_config or load_llm_config()

    if not config.api_key:
        return _generate_demo_insight(analysis.code, analysis.name, analysis, news_items)

    prompt = _build_prompt(analysis.code, analysis.name, analysis, news_items)
    try:
        content = _call_llm(prompt, config)
    except Exception as exc:  # noqa: BLE001 - 回退到演示解读
        result = _generate_demo_insight(analysis.code, analysis.name, analysis, news_items)
        result["mode"] = "fallback"
        result["error"] = str(exc)
        return result

    content = re.sub(r"\n{3,}", "\n\n", content)
    return {
        "code": analysis.code,
        "name": analysis.name,
        "mode": "llm",
        "model": config.model,
        "content": content,
        "news": [_news_to_dict(item) for item in news_items],
        "disclaimer": "本解读仅供学习研究，不构成投资建议。",
    }
