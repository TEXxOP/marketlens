"""Event-study helpers that preserve event-time alignment."""

from __future__ import annotations

import pandas as pd


def run_event_study(portfolio: pd.DataFrame, events: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Measure close-to-close portfolio returns around dated macro events.

    Events without a full event window are excluded rather than silently using
    partial data. Results describe this strategy simulation, not causal impact.
    """
    if window < 1:
        raise ValueError("window must be at least one business-day observation.")
    returns = portfolio["net_return"].copy()
    returns.index = pd.to_datetime(returns.index)
    rows: list[dict[str, object]] = []
    for event in events.itertuples(index=False):
        event_date = pd.Timestamp(event.date)
        location = returns.index.searchsorted(event_date)
        if location == len(returns.index):
            continue
        if returns.index[location] != event_date and location > 0:
            location -= 1
        start, end = location - window, location + window
        if start < 0 or end >= len(returns):
            continue
        slice_ = returns.iloc[start : end + 1]
        rows.append(
            {
                "date": returns.index[location],
                "event_type": event.event_type,
                "label": event.label,
                "pre_window_return": float((1 + slice_.iloc[:window]).prod() - 1),
                "event_day_return": float(slice_.iloc[window]),
                "post_window_return": float((1 + slice_.iloc[window + 1 :]).prod() - 1),
                "full_window_return": float((1 + slice_).prod() - 1),
            }
        )
    return pd.DataFrame(rows)
