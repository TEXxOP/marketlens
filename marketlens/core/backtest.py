"""Cost-aware paper-trading simulation and portfolio risk statistics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from marketlens.config import StrategyConfig


@dataclass(frozen=True)
class BacktestResult:
    instruments: pd.DataFrame
    portfolio: pd.DataFrame
    metrics: dict[str, float]


def _maximum_drawdown(equity_curve: pd.Series) -> float:
    peak = equity_curve.cummax()
    return float((equity_curve / peak - 1.0).min())


def calculate_metrics(portfolio: pd.DataFrame, annualization_factor: int = 252) -> dict[str, float]:
    returns = portfolio["net_return"].dropna()
    if len(returns) < 2:
        return {"total_return": 0.0, "annualized_return": 0.0, "annualized_volatility": 0.0,
                "sharpe_ratio": 0.0, "max_drawdown": 0.0, "calmar_ratio": 0.0,
                "hit_rate": 0.0, "average_daily_turnover": 0.0, "observations": float(len(returns))}
    equity = (1.0 + returns).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    annualized_return = float(equity.iloc[-1] ** (annualization_factor / len(returns)) - 1.0)
    annualized_volatility = float(returns.std(ddof=0) * np.sqrt(annualization_factor))
    sharpe = annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0
    drawdown = _maximum_drawdown(equity)
    calmar = annualized_return / abs(drawdown) if drawdown < 0 else 0.0
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": float(sharpe),
        "max_drawdown": drawdown,
        "calmar_ratio": float(calmar),
        "hit_rate": float((returns > 0).mean()),
        "average_daily_turnover": float(portfolio["turnover"].mean()),
        "observations": float(len(returns)),
    }


def run_backtest(prices: pd.DataFrame, positions: pd.DataFrame, config: StrategyConfig) -> BacktestResult:
    """Simulate equal-risk paper exposure, including one-way transaction costs."""
    if not prices.index.equals(positions.index) or list(prices.columns) != list(positions.columns):
        raise ValueError("Prices and positions must have the same index and instruments.")
    returns = prices.pct_change().fillna(0.0)
    turnover = positions.diff().abs().fillna(0.0)
    cost_rate = config.cost_bps / 10_000.0
    gross = positions * returns
    costs = turnover * cost_rate
    net = gross - costs
    records: list[pd.DataFrame] = []
    for symbol in prices.columns:
        frame = pd.DataFrame(
            {
                "date": prices.index,
                "symbol": symbol,
                "price": prices[symbol].values,
                "position": positions[symbol].values,
                "gross_return": gross[symbol].values,
                "cost": costs[symbol].values,
                "net_return": net[symbol].values,
                "turnover": turnover[symbol].values,
            }
        )
        records.append(frame)
    instruments = pd.concat(records, ignore_index=True)
    portfolio = pd.DataFrame(
        {
            "gross_return": gross.mean(axis=1),
            "cost": costs.mean(axis=1),
            "net_return": net.mean(axis=1),
            "turnover": turnover.mean(axis=1),
        },
        index=prices.index,
    )
    portfolio.index.name = "date"
    portfolio["equity"] = (1.0 + portfolio["net_return"]).cumprod()
    portfolio["drawdown"] = portfolio["equity"] / portfolio["equity"].cummax() - 1.0
    return BacktestResult(
        instruments=instruments,
        portfolio=portfolio,
        metrics=calculate_metrics(portfolio, config.annualization_factor),
    )
