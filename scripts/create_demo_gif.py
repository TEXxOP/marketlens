"""Create a checked-in GIF from a live MarketLens research run.

Run from the repository root:
    python scripts/create_demo_gif.py

The result is a product preview, not a performance advertisement. It is built
from delayed public data and retains the project caveats in the frame text.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marketlens.data.cot import CotDataError, fetch_tff_positioning
from marketlens.services.pipeline import run_research


OUTPUT = ROOT / "assets" / "marketlens-demo.gif"
NAVY = "#102a43"
BLUE = "#1f77b4"
TEAL = "#0f766e"
RED = "#c2410c"


def to_frame(figure: plt.Figure) -> Image.Image:
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=125, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def add_header(figure: plt.Figure, title: str, subtitle: str) -> None:
    figure.suptitle(title, x=0.055, y=0.96, ha="left", fontsize=19, fontweight="bold", color=NAVY)
    figure.text(0.055, 0.905, subtitle, ha="left", fontsize=9, color="#486581")


def make_summary_frame(result) -> Image.Image:
    metrics = result.backtest.metrics
    prices = result.dataset.prices
    figure = plt.figure(figsize=(11, 6.2), facecolor="white")
    add_header(
        figure,
        "MarketLens live research run",
        f"Source: {result.dataset.source} | {prices.index.min():%d %b %Y} to {prices.index.max():%d %b %Y}",
    )
    items = [
        ("Instruments", str(prices.shape[1])),
        ("Observations", f"{metrics['observations']:,.0f}"),
        ("Sharpe ratio", f"{metrics['sharpe_ratio']:.2f}"),
        ("Maximum drawdown", f"{metrics['max_drawdown']:.1%}"),
        ("Average turnover", f"{metrics['average_daily_turnover']:.2%}"),
    ]
    for number, (label, value) in enumerate(items):
        axis = figure.add_axes([0.055 + number * 0.185, 0.63, 0.16, 0.17])
        axis.set_facecolor("#f0f7ff")
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_visible(False)
        axis.text(0.08, 0.66, label, transform=axis.transAxes, fontsize=9, color="#486581")
        axis.text(0.08, 0.28, value, transform=axis.transAxes, fontsize=18, fontweight="bold", color=NAVY)
    table_axis = figure.add_axes([0.055, 0.18, 0.89, 0.33])
    table_axis.axis("off")
    latest = result.positions.tail(1).T.rename(columns={result.positions.index[-1]: "Latest position"})
    latest["Latest position"] = latest["Latest position"].map(lambda value: f"{value:.2%}")
    table = table_axis.table(
        cellText=[[symbol, value] for symbol, value in latest["Latest position"].items()],
        colLabels=["Futures proxy", "Risk-scaled paper position"],
        cellLoc="left",
        colLoc="left",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    figure.text(0.055, 0.075, "Delayed public data. Research and simulation only. No orders are placed.", fontsize=9, color=RED)
    return to_frame(figure)


def make_equity_frame(result) -> Image.Image:
    portfolio = result.backtest.portfolio
    figure, axes = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, gridspec_kw={"height_ratios": [2.3, 1]})
    figure.subplots_adjust(top=0.82, left=0.08, right=0.95, hspace=0.13)
    add_header(figure, "Cost-aware paper portfolio", "Lagged trend signal, volatility targeting, leverage cap, and one-way transaction costs")
    axes[0].plot(portfolio.index, portfolio["equity"], color=BLUE, linewidth=2)
    axes[0].set_ylabel("Equity index")
    axes[0].grid(alpha=0.2)
    axes[0].spines[["top", "right"]].set_visible(False)
    axes[1].fill_between(portfolio.index, portfolio["drawdown"], 0, color=RED, alpha=0.75)
    axes[1].set_ylabel("Drawdown")
    axes[1].set_xlabel("Date")
    axes[1].yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    axes[1].grid(alpha=0.2)
    axes[1].spines[["top", "right"]].set_visible(False)
    return to_frame(figure)


def make_context_frame(result) -> Image.Image:
    figure, axes = plt.subplots(1, 2, figsize=(11, 6.2))
    figure.subplots_adjust(top=0.82, left=0.08, right=0.95, wspace=0.28)
    add_header(figure, "Market context and validation", "FOMC event windows and CFTC reportable positioning are separate research views")
    events = result.event_study
    if events.empty:
        axes[0].text(0.5, 0.5, "No complete event windows", ha="center", va="center")
    else:
        axes[0].bar(events["date"], events["full_window_return"], color=TEAL)
        axes[0].yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
        axes[0].set_title("FOMC event-window return")
        axes[0].set_ylabel("11-day strategy return")
    axes[0].grid(alpha=0.2, axis="y")
    axes[0].spines[["top", "right"]].set_visible(False)
    try:
        cot = fetch_tff_positioning("ES", limit=104).data
        axes[1].plot(cot["date"], cot["asset_manager_net_pct_oi"], label="Asset manager", color=BLUE)
        axes[1].plot(cot["date"], cot["leveraged_money_net_pct_oi"], label="Leveraged money", color=RED)
        axes[1].legend(frameon=False)
        axes[1].yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
        axes[1].set_title("CFTC E-mini S&P 500 net positioning")
        axes[1].set_ylabel("Net positions / open interest")
    except CotDataError:
        axes[1].text(0.5, 0.5, "CFTC source unavailable", ha="center", va="center")
    axes[1].grid(alpha=0.2)
    axes[1].spines[["top", "right"]].set_visible(False)
    figure.text(0.055, 0.06, "Event studies are descriptive. CFTC reports are weekly and delayed.", fontsize=9, color=RED)
    return to_frame(figure)


def main() -> None:
    result = run_research(source="yahoo", event_calendar_path=ROOT / "data" / "sample" / "macro_events.csv")
    frames = [make_summary_frame(result), make_equity_frame(result), make_context_frame(result)]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=[2200, 2200, 2600], loop=0, disposal=2)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
