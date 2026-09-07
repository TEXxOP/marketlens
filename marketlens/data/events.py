"""Validated local macro-event calendar for reproducible event studies."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"date", "event_type", "label"}


def load_event_calendar(path: str | Path) -> pd.DataFrame:
    events = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(events.columns)
    if missing:
        raise ValueError(f"Event calendar is missing columns: {sorted(missing)}")
    events["date"] = pd.to_datetime(events["date"])
    if events["date"].isna().any():
        raise ValueError("Event calendar contains invalid dates.")
    return events.sort_values("date").reset_index(drop=True)
