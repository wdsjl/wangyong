"""数据模型。"""

from dataclasses import dataclass, field
from enum import Enum


class Signal(str, Enum):
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    HOLD = "观望"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"


@dataclass
class IndicatorSnapshot:
    ma5: float | None = None
    ma10: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    boll_upper: float | None = None
    boll_middle: float | None = None
    boll_lower: float | None = None


@dataclass
class AnalysisResult:
    code: str
    name: str
    latest_price: float
    latest_date: str
    signal: Signal
    score: float
    reasons: list[str] = field(default_factory=list)
    indicators: IndicatorSnapshot | None = None
    risk_note: str = "本系统仅供学习研究，不构成投资建议。"
