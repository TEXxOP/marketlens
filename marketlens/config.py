"""Application defaults. These values are intentionally conservative for research use."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyConfig:
    fast_window: int = 20
    slow_window: int = 100
    volatility_window: int = 20
    target_annual_volatility: float = 0.12
    max_gross_leverage: float = 1.0
    cost_bps: float = 2.0
    annualization_factor: int = 252


DEFAULT_SYMBOLS: dict[str, str] = {
    "ES=F": "S&P 500 E-mini futures",
    "CL=F": "WTI crude oil futures",
    "GC=F": "Gold futures",
    "ZN=F": "10-year Treasury Note futures",
}
