"""One reproducible research run shared by every user interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from marketlens.config import DEFAULT_SYMBOLS, StrategyConfig
from marketlens.core.backtest import BacktestResult, run_backtest
from marketlens.core.events import run_event_study
from marketlens.core.strategy import build_positions
from marketlens.core.walkforward import run_walk_forward
from marketlens.data.events import load_event_calendar
from marketlens.data.market import PriceDataset, download_yahoo_prices, generate_demo_prices


@dataclass(frozen=True)
class ResearchRun:
    dataset: PriceDataset
    positions: pd.DataFrame
    backtest: BacktestResult
    event_study: pd.DataFrame
    walk_forward: pd.DataFrame


def run_research(
    source: str = "yahoo",
    config: StrategyConfig = StrategyConfig(),
    symbols: tuple[str, ...] = tuple(DEFAULT_SYMBOLS.keys()),
    event_calendar_path: str | Path = "data/sample/macro_events.csv",
) -> ResearchRun:
    if source == "synthetic":
        dataset = generate_demo_prices(symbols=symbols)
    elif source == "yahoo":
        dataset = download_yahoo_prices(symbols=symbols)
    else:
        raise ValueError("source must be either 'synthetic' or 'yahoo'.")
    positions = build_positions(dataset.prices, config)
    backtest = run_backtest(dataset.prices, positions, config)
    events = load_event_calendar(event_calendar_path)
    event_study = run_event_study(backtest.portfolio, events)
    walk_forward = run_walk_forward(dataset.prices, config)
    return ResearchRun(
        dataset=dataset,
        positions=positions,
        backtest=backtest,
        event_study=event_study,
        walk_forward=walk_forward,
    )
