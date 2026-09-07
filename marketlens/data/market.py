"""End-of-day futures price adapters.

The Yahoo adapter is convenient for exploration, not a source of record. It may
use continuous contracts and should be replaced with licensed contract-level
data for decisions beyond a portfolio project.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

from marketlens.config import DEFAULT_SYMBOLS


class DataUnavailableError(RuntimeError):
    """Raised when an external price source cannot return usable data."""


@dataclass(frozen=True)
class PriceDataset:
    prices: pd.DataFrame
    source: str
    caveat: str


def generate_demo_prices(
    symbols: Iterable[str] = DEFAULT_SYMBOLS.keys(), periods: int = 520, seed: int = 17
) -> PriceDataset:
    """Create deterministic synthetic end-of-day prices for offline demos and tests.

    Synthetic output is explicitly labelled and must never be represented as
    historical market performance.
    """
    index = pd.bdate_range(end="2024-12-31", periods=periods)
    rng = np.random.default_rng(seed)
    prices: dict[str, pd.Series] = {}
    for position, symbol in enumerate(symbols):
        drift = (position - 1.5) * 0.00002
        volatility = 0.007 + position * 0.0015
        regime = np.sin(np.linspace(0, 6 * np.pi, periods)) * (0.0008 + position * 0.00015)
        returns = drift + regime + rng.normal(0, volatility, periods)
        prices[symbol] = 100.0 * np.exp(np.cumsum(returns))
    return PriceDataset(
        prices=pd.DataFrame(prices, index=index),
        source="synthetic-demo",
        caveat="Synthetic data for offline product demonstration only; not historical market data.",
    )


def download_yahoo_prices(
    symbols: Iterable[str] = DEFAULT_SYMBOLS.keys(),
    start: str = "2019-01-01",
    end: str | None = None,
) -> PriceDataset:
    """Download daily close proxies from Yahoo Finance's public chart endpoint.

    The implementation deliberately uses only public HTTP and no credential or
    brokerage integration. Yahoo is a convenience source, not a source of
    record. Futures do not pay dividends, so close is the appropriate proxy.
    """
    requested = list(symbols)
    end = end or date.today().isoformat()
    start_epoch = int(pd.Timestamp(start, tz="UTC").timestamp())
    end_epoch = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    series: dict[str, pd.Series] = {}
    for symbol in requested:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
        try:
            response = requests.get(
                url,
                params={"period1": start_epoch, "period2": end_epoch, "interval": "1d", "events": "history"},
                timeout=20,
                headers={"User-Agent": "MarketLens research project/0.1"},
            )
            response.raise_for_status()
            payload = response.json()["chart"]["result"][0]
            timestamps = payload["timestamp"]
            closes = payload["indicators"]["quote"][0]["close"]
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            raise DataUnavailableError(f"Yahoo Finance did not return usable daily data for {symbol}.") from exc
        index = pd.to_datetime(timestamps, unit="s", utc=True).tz_localize(None).normalize()
        series[symbol] = pd.Series(closes, index=index, dtype=float)
    close = pd.DataFrame(series).reindex(columns=requested).dropna(how="all").ffill().dropna(how="any")
    if close.empty or len(close) < 120:
        raise DataUnavailableError("Insufficient shared price history returned for the requested symbols.")
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return PriceDataset(
        prices=close.astype(float),
        source="yahoo-finance-eod",
        caveat=(
            "Public end-of-day continuous futures proxies. Contract rolls, settlement conventions, "
            "survivorship, and data revisions require independent validation."
        ),
    )
