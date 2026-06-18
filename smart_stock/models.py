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
    kdj_k: float | None = None
    kdj_d: float | None = None
    kdj_j: float | None = None
    cci: float | None = None
    wr: float | None = None
    mfi: float | None = None
    adx: float | None = None
    plus_di: float | None = None
    minus_di: float | None = None
    ama: float | None = None


@dataclass
class VixSnapshot:
    index_value: int | None = None
    realized_vol: float | None = None
    label: str = "未知"
    trend: str = "平稳"
    source: str = "unavailable"


@dataclass
class SectorSnapshot:
    sector_name: str = "未知板块"
    sector_code: str = ""
    change_pct: float | None = None
    up_ratio: float | None = None
    sentiment_score: int = 50
    sentiment_label: str = "板块中性"
    source: str = "unavailable"


@dataclass
class IntradaySnapshot:
    latest_price: float | None = None
    latest_time: str = "--"
    rsi: float | None = None
    macd_hist: float | None = None
    vwap: float | None = None
    vwap_signal: str = "未知"
    momentum_label: str = "未知"
    trend_label: str = "震荡"
    bar_count: int = 0
    source: str = "unavailable"


@dataclass
class ChipSnapshot:
    avg_cost: float | None = None
    profit_ratio: float | None = None
    trapped_ratio: float | None = None
    support_price: float | None = None
    pressure_price: float | None = None
    peak_price: float | None = None


@dataclass
class FundamentalSnapshot:
    pe_ttm: float | None = None
    pb: float | None = None
    roe: float | None = None
    valuation_label: str = "未知"
    source: str = "unavailable"


@dataclass
class NorthboundSnapshot:
    eligible: bool = False
    net_inflow_today: float | None = None
    holding_ratio: float | None = None
    source: str = "unavailable"


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
    adx: float | None = None
    trend_regime: str = "未知"
    momentum_resonance: str = "无"
    chip: ChipSnapshot | None = None
    fundamentals: FundamentalSnapshot | None = None
    northbound: NorthboundSnapshot | None = None
    vix: VixSnapshot | None = None
    sector: SectorSnapshot | None = None
    intraday: IntradaySnapshot | None = None
    ama_signal: str = "未知"
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
