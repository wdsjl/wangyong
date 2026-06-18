"""全局配置。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorConfig:
    ma_periods: tuple[int, ...] = (5, 10, 20, 60, 120)
    vma_periods: tuple[int, ...] = (5, 20)
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    boll_period: int = 20
    boll_std: float = 2.0
    atr_period: int = 14
    bias_period: int = 20
    kdj_period: int = 9
    kdj_k: int = 3
    kdj_d: int = 3
    cci_period: int = 14
    wr_period: int = 14
    mfi_period: int = 14
    adx_period: int = 14
    ama_period: int = 10
    ama_fast: int = 2
    ama_slow: int = 30


@dataclass(frozen=True)
class StrategyConfig:
    buy_threshold: float = 0.6
    sell_threshold: float = -0.6
    lookback_days: int = 120
    atr_stop_multiplier: float = 2.0
    adx_trend_threshold: float = 25.0
    adx_range_threshold: float = 20.0


@dataclass(frozen=True)
class ResonanceConfig:
    """多指标共振阈值。"""

    strong_min_hits: int = 4
    weak_min_hits: int = 2
    volume_breakout_ratio: float = 1.2
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    kdj_oversold: float = 20.0
    kdj_overbought: float = 80.0
    cci_oversold: float = -100.0
    cci_overbought: float = 100.0
    wr_oversold: float = -80.0
    wr_overbought: float = -20.0
    mfi_oversold: float = 20.0
    mfi_overbought: float = 80.0


DEFAULT_INDICATOR_CONFIG = IndicatorConfig()
DEFAULT_STRATEGY_CONFIG = StrategyConfig()
DEFAULT_RESONANCE_CONFIG = ResonanceConfig()
