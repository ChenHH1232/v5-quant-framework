# Bank Value Quality V2 Local JoinQuant Simulation Status

Date: 2026-07-15

## Purpose

Build a local daily runner that can reproduce the current JoinQuant `Bank Value Quality V2` engineering test as closely as possible, while keeping a stricter research-grade point-in-time mode for future validation.

## Implemented

- Local V2 scoring engine supports `value_score + quality_score`.
- `eastmoney_bank_quality_manual_csv.csv` can be merged into the local panel with two visibility modes:
  - `notice_date`: research-grade point-in-time mode.
  - `joinquant_source_year`: platform-replication mode matching the current JoinQuant V2 code.
- Daily runner uses JoinQuant-style real unadjusted stock `open/close` execution data.
- Daily runner emits:
  - `daily_returns.csv`
  - `holdings.csv`
  - `cash` inside `daily_returns.csv`
  - `trades.csv`
  - `dividends.csv`
  - `rebalance_signals.csv`
- Trading constraints now skip paused stocks, opening high-limit buys, and opening low-limit sells.
- Cash dividends are credited from `joinquant_cash_dividends.csv`.
- Benchmark loader supports a previous-trading-day close anchor when the benchmark CSV contains one.

## Current Local Results

### Research PIT mode

Command mode: `--eastmoney-visibility-mode notice_date`

- Strategy return: 28.06%
- Benchmark return with current JoinQuant benchmark CSV: 25.16%
- This is stricter than the current JoinQuant V2 code because bank-quality data is unavailable before its notice date.

### JoinQuant source-year replication mode

Command mode: `--eastmoney-visibility-mode joinquant_source_year`

Using the benchmark file with the 2021-04-30 anchor:

- Strategy return: 35.17%
- Benchmark return: 26.59%
- Beta: 0.836
- Max drawdown: 17.05%

User's latest JoinQuant result:

- Strategy return: 35.43%
- Benchmark return: 26.51%
- Beta: 0.837
- Max drawdown: 18.08%

The strategy return gap is currently about 0.26 percentage points. This is close enough to start daily attribution once the JoinQuant daily return CSV is exported.

## Remaining Known Gaps

- Local execution uses daily open, while JoinQuant code runs at 09:40 and uses `current_data.last_price`.
- The current `joinquant_real_benchmark_prices.csv` starts at 2021-05-06, so it cannot reproduce JoinQuant's benchmark return unless the previous trading day close is also collected.
- True daily attribution requires the JoinQuant daily returns CSV from the exact 35.43% run.

## Next Step

After exporting the JoinQuant daily returns CSV, run the platform attribution runner against:

- Local: `local_daily_backtests_v2_jq_source_year_ak_bm/bank_value_quality_v2/daily_returns.csv`
- JoinQuant: exported platform daily returns CSV

