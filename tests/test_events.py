import pandas as pd

from marketlens.core.events import run_event_study


def test_event_study_excludes_partial_windows() -> None:
    index = pd.bdate_range("2024-01-01", periods=20)
    portfolio = pd.DataFrame({"net_return": [0.001] * 20}, index=index)
    events = pd.DataFrame(
        {
            "date": [index[1], index[10]],
            "event_type": ["FOMC", "FOMC"],
            "label": ["partial", "complete"],
        }
    )
    output = run_event_study(portfolio, events, window=3)
    assert output["label"].tolist() == ["complete"]
    assert output.loc[0, "full_window_return"] > 0
