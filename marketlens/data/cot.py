"""CFTC Traders in Financial Futures (TFF) positioning adapter.

The CFTC publishes the TFF dataset through its unauthenticated Public Reporting
Environment API. It is weekly, reportable-position data—not a real-time signal.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import requests


TFF_ENDPOINT = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
SUPPORTED_MARKETS = {
    "ES": "E-MINI S&P 500",
    "ZN": "UST 10Y NOTE",
}


class CotDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class PositioningSnapshot:
    market: str
    data: pd.DataFrame
    source_url: str = TFF_ENDPOINT


def fetch_tff_positioning(market: str = "ES", limit: int = 260, timeout_seconds: int = 20) -> PositioningSnapshot:
    """Fetch weekly net positions for a supported TFF contract market."""
    key = market.upper()
    if key not in SUPPORTED_MARKETS:
        raise ValueError(f"market must be one of {sorted(SUPPORTED_MARKETS)}")
    contract = SUPPORTED_MARKETS[key]
    fields = ",".join(
        [
            "report_date_as_yyyy_mm_dd",
            "contract_market_name",
            "open_interest_all",
            "asset_mgr_positions_long",
            "asset_mgr_positions_short",
            "lev_money_positions_long",
            "lev_money_positions_short",
        ]
    )
    params = {
        "$select": fields,
        "$where": f"contract_market_name='{contract}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": str(limit),
    }
    try:
        response = requests.get(TFF_ENDPOINT, params=params, timeout=timeout_seconds)
        response.raise_for_status()
        rows = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CotDataError("Could not fetch CFTC TFF positioning data.") from exc
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise CotDataError(f"CFTC returned no TFF rows for {contract}.")
    numeric = [column for column in fields.split(",") if column not in {"report_date_as_yyyy_mm_dd", "contract_market_name"}]
    frame["date"] = pd.to_datetime(frame.pop("report_date_as_yyyy_mm_dd"))
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["asset_manager_net"] = frame["asset_mgr_positions_long"] - frame["asset_mgr_positions_short"]
    frame["leveraged_money_net"] = frame["lev_money_positions_long"] - frame["lev_money_positions_short"]
    frame["asset_manager_net_pct_oi"] = frame["asset_manager_net"] / frame["open_interest_all"]
    frame["leveraged_money_net_pct_oi"] = frame["leveraged_money_net"] / frame["open_interest_all"]
    return PositioningSnapshot(market=key, data=frame.sort_values("date").reset_index(drop=True))
