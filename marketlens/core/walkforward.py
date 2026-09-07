"""Sequential out-of-sample reporting without parameter optimization."""

from __future__ import annotations

import pandas as pd

from marketlens.config import StrategyConfig
from marketlens.core.backtest import calculate_metrics, run_backtest
from marketlens.core.strategy import build_positions


def run_walk_forward(
    prices: pd.DataFrame,
    config: StrategyConfig,
    training_days: int = 252,
    test_days: int = 63,
) -> pd.DataFrame:
    """Report sequential fixed-rule test windows after a minimum history period.

    MarketLens does not tune on each window. This routine instead makes the
    time ordering visible and gives each test block metrics computed only from
    that block's returns. Signals are recomputed using price history available
    through the end of each block and remain one session lagged.
    """
    if training_days < config.slow_window:
        raise ValueError("training_days must cover at least the slow signal window.")
    if test_days < 5:
        raise ValueError("test_days must be at least 5.")
    rows: list[dict[str, object]] = []
    start = training_days
    fold_number = 1
    while start < len(prices):
        stop = min(start + test_days, len(prices))
        prefix = prices.iloc[:stop]
        result = run_backtest(prefix, build_positions(prefix, config), config)
        test_portfolio = result.portfolio.iloc[start:stop]
        if len(test_portfolio) >= 2:
            metrics = calculate_metrics(test_portfolio, config.annualization_factor)
            rows.append(
                {
                    "fold": fold_number,
                    "test_start": test_portfolio.index[0],
                    "test_end": test_portfolio.index[-1],
                    "observations": int(len(test_portfolio)),
                    **metrics,
                }
            )
        start = stop
        fold_number += 1
    return pd.DataFrame(rows)
