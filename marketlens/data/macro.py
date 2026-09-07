"""Key-free FRED adapter for macroeconomic research context."""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests


class MacroDataError(RuntimeError):
    pass


def fetch_fred_series(series_id: str, timeout_seconds: int = 15) -> pd.DataFrame:
    """Fetch a public FRED graph CSV. This endpoint needs no private API key."""
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    try:
        response = requests.get(url, params={"id": series_id}, timeout=timeout_seconds)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise MacroDataError(f"Could not fetch FRED series {series_id}.") from exc
    frame = pd.read_csv(StringIO(response.text))
    date_column = "DATE" if "DATE" in frame.columns else "observation_date"
    if date_column not in frame.columns or series_id not in frame.columns:
        raise MacroDataError(f"FRED response for {series_id} has an unexpected format.")
    frame[date_column] = pd.to_datetime(frame[date_column])
    frame[series_id] = pd.to_numeric(frame[series_id], errors="coerce")
    return frame.dropna().rename(columns={date_column: "date", series_id: "value"})
