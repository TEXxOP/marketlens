"""Simple, transparent trend and volatility-regime strategy construction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from marketlens.config import StrategyConfig


def build_positions(prices: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """Return risk-scaled positions using only information available at t-1.

    A positive position denotes a long exposure, a negative position denotes a
    short exposure. Each symbol is clipped before equal-weight portfolioing.
    """
    if prices.empty or prices.shape[1] == 0:
        raise ValueError("Prices must contain at least one instrument.")
    if config.fast_window >= config.slow_window:
        raise ValueError("fast_window must be smaller than slow_window.")
    returns = prices.pct_change()
    fast = prices.rolling(config.fast_window, min_periods=config.fast_window).mean()
    slow = prices.rolling(config.slow_window, min_periods=config.slow_window).mean()
    direction = np.sign(fast - slow).replace(0, np.nan).ffill().fillna(0.0)
    daily_target = config.target_annual_volatility / np.sqrt(config.annualization_factor)
    realized_volatility = returns.rolling(
        config.volatility_window, min_periods=config.volatility_window
    ).std(ddof=0)
    scaler = (daily_target / realized_volatility.replace(0, np.nan)).clip(
        upper=config.max_gross_leverage
    )
    raw_positions = (direction * scaler).fillna(0.0)
    # At a close-to-close frequency this shift is the anti-look-ahead control.
    return raw_positions.shift(1).fillna(0.0)
