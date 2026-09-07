"""Interactive MarketLens research dashboard."""

from __future__ import annotations

from pathlib import Path
import sys

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marketlens.config import DEFAULT_SYMBOLS, StrategyConfig
from marketlens.data.cot import CotDataError, fetch_tff_positioning
from marketlens.data.market import DataUnavailableError
from marketlens.services.pipeline import run_research


st.set_page_config(page_title="MarketLens", page_icon="M", layout="wide")
st.title("MarketLens")
st.caption("Global futures research and paper-trading simulation. No brokerage integration. No live orders.")

with st.sidebar:
    st.header("Research controls")
    source = st.selectbox("Price data", ("yahoo", "synthetic"), format_func=lambda value: {
        "yahoo": "Yahoo Finance end-of-day (real data)",
        "synthetic": "Synthetic offline demo",
    }[value])
    fast_window = st.slider("Fast trend window", 5, 60, 20)
    slow_window = st.slider("Slow trend window", 70, 220, 100)
    target_volatility = st.slider("Target annual volatility", 0.04, 0.25, 0.12, 0.01)
    show_positioning = st.checkbox("Load CFTC positioning (ES)", value=False)
    run_button = st.button("Run research", type="primary")

if not run_button:
    st.info("Select real end-of-day data and run a cost-aware, no-look-ahead paper simulation.")
    st.stop()

if fast_window >= slow_window:
    st.error("The fast trend window must be shorter than the slow trend window.")
    st.stop()

config = StrategyConfig(
    fast_window=fast_window,
    slow_window=slow_window,
    target_annual_volatility=target_volatility,
)
try:
    with st.spinner("Loading price data and running the simulation..."):
        result = run_research(
            source=source,
            config=config,
            event_calendar_path=ROOT / "data" / "sample" / "macro_events.csv",
        )
except DataUnavailableError as exc:
    st.error(f"Real market data could not be loaded: {exc}")
    st.caption("Synthetic mode remains available for offline demonstrations and test verification.")
    st.stop()

st.warning(result.dataset.caveat)
metrics = result.backtest.metrics
metric_columns = st.columns(5)
metric_columns[0].metric("Total return", f"{metrics['total_return']:.1%}")
metric_columns[1].metric("Annualized return", f"{metrics['annualized_return']:.1%}")
metric_columns[2].metric("Annualized volatility", f"{metrics['annualized_volatility']:.1%}")
metric_columns[3].metric("Sharpe ratio", f"{metrics['sharpe_ratio']:.2f}")
metric_columns[4].metric("Maximum drawdown", f"{metrics['max_drawdown']:.1%}")

left, right = st.columns(2)
with left:
    equity = result.backtest.portfolio.reset_index()
    figure = px.line(equity, x="date", y="equity", title="Paper portfolio equity curve")
    figure.update_yaxes(tickformat=".2f")
    st.plotly_chart(figure, use_container_width=True)
with right:
    drawdown = px.area(equity, x="date", y="drawdown", title="Drawdown")
    drawdown.update_yaxes(tickformat=".0%")
    st.plotly_chart(drawdown, use_container_width=True)

st.subheader("Latest risk-scaled positions")
latest = result.positions.tail(1).T.reset_index()
latest.columns = ["symbol", "position"]
latest["instrument"] = latest["symbol"].map(DEFAULT_SYMBOLS)
st.dataframe(latest[["symbol", "instrument", "position"]].style.format({"position": "{:.2%}"}), use_container_width=True)

position_history = result.positions.reset_index().melt(id_vars="index", var_name="symbol", value_name="position")
position_history = position_history.rename(columns={"index": "date"})
position_chart = px.line(position_history, x="date", y="position", color="symbol", title="Signal and volatility-scaled exposure")
position_chart.update_yaxes(tickformat=".0%")
st.plotly_chart(position_chart, use_container_width=True)

st.subheader("Macro-event study")
if result.event_study.empty:
    st.caption("No events had a full pre/post window in the selected sample.")
else:
    event_chart = px.bar(
        result.event_study,
        x="date",
        y="full_window_return",
        color="event_type",
        hover_data=["label", "event_day_return", "pre_window_return", "post_window_return"],
        title="11-trading-day strategy return around FOMC event windows",
    )
    event_chart.update_yaxes(tickformat=".1%")
    st.plotly_chart(event_chart, use_container_width=True)
    st.caption("Descriptive event-window analysis only; it does not establish causality or predict future returns.")

st.subheader("Sequential walk-forward test windows")
if result.walk_forward.empty:
    st.caption("Not enough history for the configured warm-up and test windows.")
else:
    st.dataframe(
        result.walk_forward[["fold", "test_start", "test_end", "observations", "annualized_return", "sharpe_ratio", "max_drawdown"]]
        .style.format({"annualized_return": "{:.1%}", "sharpe_ratio": "{:.2f}", "max_drawdown": "{:.1%}"}),
        use_container_width=True,
    )
    st.caption("Fixed-rule sequential test blocks; no parameter optimization is performed between folds.")

if show_positioning:
    st.subheader("CFTC Traders in Financial Futures positioning")
    try:
        with st.spinner("Loading weekly CFTC TFF report..."):
            positioning = fetch_tff_positioning("ES").data
        cot_chart = go.Figure()
        cot_chart.add_trace(go.Scatter(x=positioning["date"], y=positioning["asset_manager_net_pct_oi"], name="Asset manager net / OI"))
        cot_chart.add_trace(go.Scatter(x=positioning["date"], y=positioning["leveraged_money_net_pct_oi"], name="Leveraged money net / OI"))
        cot_chart.update_layout(title="E-mini S&P 500: reportable net positioning", yaxis_tickformat=".0%")
        st.plotly_chart(cot_chart, use_container_width=True)
        st.caption("Weekly CFTC reportable positions; published with a reporting delay and not a trading recommendation.")
    except CotDataError as exc:
        st.warning(f"CFTC positioning was unavailable: {exc}")

with st.expander("Research controls and limitations"):
    st.markdown(
        """
        - Uses a trend signal generated from lagged end-of-day closes.
        - Uses volatility scaling, leverage caps, and explicit one-way transaction costs.
        - Yahoo continuous contracts are research proxies; contract rolls and settlement details need validation.
        - CFTC positioning is weekly and contains reportable positions, not all market activity.
        - Results are illustrative and are not investment advice.
        """
    )
