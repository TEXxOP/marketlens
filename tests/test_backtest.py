from marketlens.config import StrategyConfig
from marketlens.core.backtest import run_backtest
from marketlens.core.strategy import build_positions
from marketlens.data.market import generate_demo_prices


def test_backtest_contains_costs_and_risk_metrics() -> None:
    prices = generate_demo_prices(periods=240).prices
    config = StrategyConfig(fast_window=12, slow_window=40, volatility_window=12, cost_bps=3.0)
    result = run_backtest(prices, build_positions(prices, config), config)
    assert set(["equity", "drawdown", "net_return", "turnover"]).issubset(result.portfolio.columns)
    assert result.instruments["cost"].ge(0).all()
    assert result.metrics["observations"] == 240.0
    assert result.metrics["max_drawdown"] <= 0.0


def test_misaligned_prices_and_positions_fail() -> None:
    prices = generate_demo_prices(periods=180).prices
    config = StrategyConfig(fast_window=10, slow_window=30, volatility_window=10)
    positions = build_positions(prices, config).iloc[1:]
    try:
        run_backtest(prices, positions, config)
    except ValueError as exc:
        assert "same index" in str(exc)
    else:
        raise AssertionError("Expected a mismatch validation error")
