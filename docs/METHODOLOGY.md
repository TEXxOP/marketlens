# Methodology and limitations

## Objective

MarketLens is an educational research project for analyzing transparent,
rules-based futures proxies under realistic-looking constraints. It does not
estimate a tradable recommendation or forecast future performance.

## Price data

The default `yahoo` mode requests adjusted end-of-day closes for continuous
front-month proxies. These are useful for learning and portfolio demonstration,
but a continuous series can hide roll methodology and contract-specific
liquidity. Any serious historical study needs a documented roll rule, exchange
settlements, contract multipliers, margin assumptions, and a licensed dataset.

`synthetic` mode exists solely to exercise the application without an internet
connection. It is deterministic and visibly labelled; no result from it is a
market result.

## Signal and execution timing

For each instrument, the strategy computes moving averages and realized
volatility from prices observed by the close of day `t`. The resulting desired
position is shifted one full session, so the day-`t` return is paired only with
the position known at the close of `t-1`. This is the project’s basic
no-look-ahead control.

## Sizing, costs, and aggregation

Daily target volatility is annual target volatility divided by the square root
of 252. The system scales a directional signal by trailing realized volatility,
then clips exposure at the configured per-instrument leverage cap. Each change
in position incurs a configurable one-way basis-point cost. Instrument results
are averaged equally; this is a research simplification, not capital allocation
guidance.

## Metrics

The application reports total/annualized return, annualized volatility, Sharpe
ratio using a zero cash-rate assumption, maximum drawdown, Calmar ratio, hit
rate, and average daily turnover. These statistics are descriptive and are
sensitive to data source, date window, rollover logic, cost choice, and
selection bias.

## Event study

The event module aligns a fixed number of available trading observations before
and after a supplied event date. It omits events lacking a complete window. The
returned values are strategy returns around those windows, not abnormal returns
or evidence of a causal FOMC effect.

## Regulatory and macro data

CFTC TFF data is weekly and reports aggregated positions subject to CFTC
reporting rules. FRED series can be revised. Neither should be treated as if it
were available in real time without an explicit availability-date model.

## Known exclusions

- No live or simulated order routing
- No brokerage accounts or credentials
- No intraday data or order-book analysis
- No contract roll engine or margin model
- No news scraping, LLM-generated trading recommendation, or sentiment claim
- No optimization against the same sample used to report results

These exclusions are deliberate: the project favors auditable research basics
over a misleading appearance of production trading capability.
