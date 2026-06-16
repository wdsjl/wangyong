"""全局配置。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorConfig:
    ma_periods: tuple[int, ...] = (5, 10, 20, 60)
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    boll_period: int = 20
    boll_std: float = 2.0


@dataclass(frozen=True)
class StrategyConfig:
    buy_threshold: float = 0.6
    sell_threshold: float = -0.6
    lookback_days: int = 120


DEFAULT_INDICATOR_CONFIG = IndicatorConfig()
DEFAULT_STRATEGY_CONFIG = StrategyConfig()
