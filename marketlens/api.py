"""FastAPI surface for reproducible research runs; intentionally no execution endpoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from marketlens.config import StrategyConfig
from marketlens.data.cot import CotDataError, fetch_tff_positioning
from marketlens.data.macro import MacroDataError, fetch_fred_series
from marketlens.data.market import DataUnavailableError
from marketlens.services.pipeline import run_research


ROOT = Path(__file__).resolve().parents[1]
EVENT_CALENDAR = ROOT / "data" / "sample" / "macro_events.csv"

app = FastAPI(
    title="MarketLens API",
    version="0.1.0",
    description="Research and paper-trading simulation API. It never places orders.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "research-and-simulation-only"}


def _json_records(frame):
    """Normalize pandas timestamps before handing records to FastAPI."""
    output = frame.copy()
    for column in output.columns:
        if str(output[column].dtype).startswith("datetime"):
            output[column] = output[column].dt.strftime("%Y-%m-%d")
    return output.to_dict(orient="records")


@app.get("/research/run")
def research_run(
    source: str = Query("yahoo", pattern="^(yahoo|synthetic)$"),
    fast_window: int = Query(20, ge=5, le=90),
    slow_window: int = Query(100, ge=30, le=260),
    target_volatility: float = Query(0.12, gt=0.01, le=0.5),
) -> dict[str, object]:
    try:
        result = run_research(
            source=source,
            config=StrategyConfig(
                fast_window=fast_window,
                slow_window=slow_window,
                target_annual_volatility=target_volatility,
            ),
            event_calendar_path=EVENT_CALENDAR,
        )
    except (DataUnavailableError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "source": result.dataset.source,
        "caveat": result.dataset.caveat,
        "metrics": result.backtest.metrics,
        "latest_positions": result.positions.tail(1).round(4).to_dict(orient="records")[0],
        "latest_equity": float(result.backtest.portfolio["equity"].iloc[-1]),
        "event_study": _json_records(result.event_study.tail(20).round(6)),
        "walk_forward": _json_records(result.walk_forward.round(6)),
    }


@app.get("/macro/{series_id}")
def macro_series(series_id: str) -> dict[str, object]:
    try:
        frame = fetch_fred_series(series_id.upper())
    except MacroDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"series_id": series_id.upper(), "observations": _json_records(frame.tail(260))}


@app.get("/positioning/{market}")
def positioning(market: str) -> dict[str, object]:
    try:
        snapshot = fetch_tff_positioning(market)
    except (CotDataError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "market": snapshot.market,
        "source": snapshot.source_url,
        "observations": _json_records(snapshot.data.tail(260).round(6)),
    }
