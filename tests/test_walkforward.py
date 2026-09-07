from marketlens.config import StrategyConfig
from marketlens.core.walkforward import run_walk_forward
from marketlens.data.market import generate_demo_prices


def test_walk_forward_returns_ordered_out_of_sample_blocks() -> None:
    prices = generate_demo_prices(periods=430).prices
    config = StrategyConfig(fast_window=10, slow_window=40, volatility_window=10)
    folds = run_walk_forward(prices, config, training_days=100, test_days=50)
    assert len(folds) == 7
    assert folds["test_start"].is_monotonic_increasing
    assert (folds["observations"] <= 50).all()


def test_walk_forward_requires_sufficient_warmup() -> None:
    prices = generate_demo_prices(periods=300).prices
    config = StrategyConfig(fast_window=10, slow_window=100, volatility_window=10)
    try:
        run_walk_forward(prices, config, training_days=60)
    except ValueError as exc:
        assert "slow signal" in str(exc)
    else:
        raise AssertionError("Expected a training-window validation error")
