import pandas as pd

from marketlens.config import StrategyConfig
from marketlens.core.strategy import build_positions
from marketlens.data.market import generate_demo_prices


def test_positions_are_lagged_and_bounded() -> None:
    prices = generate_demo_prices(periods=180).prices
    config = StrategyConfig(fast_window=10, slow_window=30, volatility_window=10, max_gross_leverage=0.8)
    positions = build_positions(prices, config)
    assert positions.iloc[0].eq(0).all()
    assert positions.abs().max().max() <= 0.8
    assert positions.index.equals(prices.index)


def test_invalid_windows_are_rejected() -> None:
    prices = generate_demo_prices(periods=150).prices
    config = StrategyConfig(fast_window=50, slow_window=20)
    try:
        build_positions(prices, config)
    except ValueError as exc:
        assert "fast_window" in str(exc)
    else:
        raise AssertionError("Expected invalid strategy windows to be rejected")
