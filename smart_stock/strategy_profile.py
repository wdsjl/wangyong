"""可持久化策略配置组合。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from smart_stock.config import (
    DEFAULT_RESONANCE_CONFIG,
    DEFAULT_STRATEGY_CONFIG,
    ResonanceConfig,
    StrategyConfig,
)


@dataclass
class FactorWeights:
    trend: float = 1.0
    momentum: float = 1.0
    volatility: float = 1.0
    volume: float = 1.0
    obv: float = 1.0

    def clamp(self) -> "FactorWeights":
        def _clamp(value: float) -> float:
            return max(0.1, min(3.0, float(value)))

        return FactorWeights(
            trend=_clamp(self.trend),
            momentum=_clamp(self.momentum),
            volatility=_clamp(self.volatility),
            volume=_clamp(self.volume),
            obv=_clamp(self.obv),
        )


@dataclass
class StrategyProfile:
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    resonance: ResonanceConfig = field(default_factory=ResonanceConfig)
    weights: FactorWeights = field(default_factory=FactorWeights)
    use_ama_trend: bool = True
    vix_caution_threshold: int = 65

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": asdict(self.strategy),
            "resonance": asdict(self.resonance),
            "weights": asdict(self.weights),
            "use_ama_trend": self.use_ama_trend,
            "vix_caution_threshold": self.vix_caution_threshold,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "StrategyProfile":
        if not payload:
            return cls()
        strategy_data = payload.get("strategy") or {}
        resonance_data = payload.get("resonance") or {}
        weights_data = payload.get("weights") or {}
        return cls(
            strategy=StrategyConfig(**{**asdict(DEFAULT_STRATEGY_CONFIG), **strategy_data}),
            resonance=ResonanceConfig(**{**asdict(DEFAULT_RESONANCE_CONFIG), **resonance_data}),
            weights=FactorWeights(**{**asdict(FactorWeights()), **weights_data}).clamp(),
            use_ama_trend=bool(payload.get("use_ama_trend", True)),
            vix_caution_threshold=int(payload.get("vix_caution_threshold", 65)),
        )


DEFAULT_STRATEGY_PROFILE = StrategyProfile()
