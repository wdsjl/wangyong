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
    ma120: float | None = None
    bias20: float | None = None
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    boll_upper: float | None = None
    boll_middle: float | None = None
    boll_lower: float | None = None
    obv: float | None = None
    atr: float | None = None
    vma5: float | None = None
    vma20: float | None = None
    volume_ratio: float | None = None


@dataclass
class MoneyFlowSnapshot:
    main_net_inflow: float | None = None
    large_net_inflow: float | None = None
    super_large_net_inflow: float | None = None
    main_net_pct: float | None = None
    source: str = "unavailable"


@dataclass
class MonitoringSnapshot:
    """盯盘衍生指标（第一期）。"""

    trend_score: int = 50
    trend_label: str = "震荡"
    resonance_level: str = "none"
    resonance_side: str = "neutral"
    resonance_hits: list[str] = field(default_factory=list)
    resonance_score: int = 0
    atr_stop_loss: float | None = None
    atr_stop_multiplier: float = 2.0
    obv_trend: str = "flat"
    volume_signal: str = "量能平稳"
    boll_position: str = "中轨附近"
    alerts: list[dict[str, str]] = field(default_factory=list)
    money_flow: MoneyFlowSnapshot | None = None


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
    monitoring: MonitoringSnapshot | None = None
    price_label: str = "收盘价"
    risk_note: str = "本系统仅供学习研究，不构成投资建议。"
