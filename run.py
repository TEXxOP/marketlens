"""Command-line runner that writes auditable research artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from marketlens.config import StrategyConfig
from marketlens.services.pipeline import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a MarketLens paper-trading research simulation.")
    parser.add_argument("--source", choices=("yahoo", "synthetic"), default="yahoo")
    parser.add_argument("--fast-window", type=int, default=20)
    parser.add_argument("--slow-window", type=int, default=100)
    parser.add_argument("--target-volatility", type=float, default=0.12)
    parser.add_argument("--output-dir", default="artifacts")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    output = (root / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = StrategyConfig(
        fast_window=args.fast_window,
        slow_window=args.slow_window,
        target_annual_volatility=args.target_volatility,
    )
    result = run_research(
        source=args.source,
        config=config,
        event_calendar_path=root / "data" / "sample" / "macro_events.csv",
    )
    result.dataset.prices.to_csv(output / "prices.csv", index_label="date")
    result.positions.to_csv(output / "positions.csv", index_label="date")
    result.backtest.instruments.to_csv(output / "instrument_returns.csv", index=False)
    result.backtest.portfolio.to_csv(output / "portfolio_returns.csv", index_label="date")
    result.event_study.to_csv(output / "event_study.csv", index=False)
    result.walk_forward.to_csv(output / "walk_forward.csv", index=False)
    (output / "run_metadata.json").write_text(
        json.dumps(
            {
                "source": result.dataset.source,
                "caveat": result.dataset.caveat,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "price_date_range": {
                    "start": result.dataset.prices.index.min().date().isoformat(),
                    "end": result.dataset.prices.index.max().date().isoformat(),
                },
                "instruments": list(result.dataset.prices.columns),
                "strategy_config": {
                    "fast_window": config.fast_window,
                    "slow_window": config.slow_window,
                    "volatility_window": config.volatility_window,
                    "target_annual_volatility": config.target_annual_volatility,
                    "max_gross_leverage": config.max_gross_leverage,
                    "one_way_cost_bps": config.cost_bps,
                    "annualization_factor": config.annualization_factor,
                },
                "metrics": result.backtest.metrics,
                "research_only": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(result.backtest.metrics, indent=2))
    print(f"Artifacts written to: {output}")


if __name__ == "__main__":
    main()
