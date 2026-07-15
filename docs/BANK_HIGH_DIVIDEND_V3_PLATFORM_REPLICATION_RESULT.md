# Bank High Dividend V3 Platform Replication Result

Date: 2026-07-15

## Purpose

Run a local JoinQuant-like platform replication before handing the strategy code to JoinQuant.

Experiment layer:

`platform_replication`

This is an engineering/platform comparison run, not research acceptance evidence.

## Local Simulation Inputs

Strategy:

- `examples/bank_high_dividend_sustainability_v3_strategy.json`

Signal panel:

- `数据库/processed/joinquant_basic_pit_panel_v4_legacy_quality/panel.csv`

Execution data:

- stock execution prices: `数据库/processed/joinquant_real_daily_prices.csv`
- benchmark prices: `数据库/processed/joinquant_real_benchmark_prices.csv`
- dividend cash: `数据库/processed/joinquant_cash_dividends.csv`

Window:

- `2021-05-01` to `2026-05-31`

Execution assumptions:

- daily open execution approximation;
- daily close valuation;
- A-share 100-share lot rounding;
- open and close commission `0.0003`;
- minimum commission `5`;
- target exposure `0.995`;
- no defensive overlay;
- benchmark `512800.XSHG`.

## Local Simulation Output

Output directory:

- `local_daily_backtests_v3_platform_replication/bank_high_dividend_sustainability_v3/`

Key files:

- `summary.json`
- `daily_returns.csv`
- `holdings.csv`
- `trades.csv`
- `dividends.csv`
- `rebalance_signals.csv`

## Local Metrics

| Metric | Value |
| --- | ---: |
| strategy return | 65.36% |
| annualized return | 10.87% |
| benchmark return | 25.16% |
| excess return | 40.20% |
| alpha | 0.067 |
| beta | 0.877 |
| Sharpe | 0.701 |
| max drawdown | 15.84% |
| max drawdown interval | 2022-04-06 to 2022-10-31 |
| strategy volatility | 16.71% |
| benchmark volatility | 16.89% |
| information ratio | 0.711 |
| profit count | 600 |
| loss count | 589 |

Engineering checks:

- rebalance signals: 19
- daily rows: 1228
- buy trades: 117
- sell trades: 88
- dividend events credited: 44
- total dividend cash credited: 439634.84

## JoinQuant Code

Generated file:

- `exports/joinquant/bank_high_dividend_sustainability_v3_joinquant_near5y.py`

The JoinQuant code uses:

- `set_benchmark('512800.XSHG')`;
- `set_option('use_real_price', True)`;
- `set_option('avoid_future_data', True)`;
- quarterly rebalance at `09:40`;
- PB and ROE from `get_fundamentals(date=factor_date)`;
- embedded visible cash dividend table for trailing dividend yield;
- embedded V4 legacy bank quality table using latest `notice_date <= factor_date`;
- 8-stock equal-weight target with 100-share rounding;
- no stop loss, no take profit, no defensive overlay.

## Expected Difference From Local

Local simulation uses daily open as execution approximation. JoinQuant runs the scheduled order at `09:40`, so fills, limit checks, and intraday prices can differ.

The code also uses `factor_date = previous_date` to avoid future data. This is stricter than some panel rows generated at rebalance date, so selected names may differ slightly from the local runner. Treat the first JoinQuant run as a platform-alignment test.
