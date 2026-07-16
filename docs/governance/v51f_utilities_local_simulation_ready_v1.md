# Governance Record: v51f_utilities_local_simulation_ready_v1

Date: 2026-07-16

Strategy:

```text
utilities_demand_state_v51f
```

Status:

```text
local_joinquant_like_simulation_ready
```

Not status:

```text
platform_replication
JoinQuant_code_ready
accepted_strategy
```

## Purpose

Prepare the V5.1f utilities formal candidate for local JoinQuant-like daily simulation without mixing bank-platform replication data.

## Data Contract

The local simulation uses separate utilities-specific execution files:

```text
database/processed/utilities_joinquant_real_daily_prices.csv
database/processed/utilities_joinquant_real_benchmark_prices.csv
database/processed/utilities_joinquant_cash_dividends.csv
```

The generic JoinQuant real-data collector now supports:

```text
--output-prefix utilities
```

This prevents overwriting bank files:

```text
joinquant_real_daily_prices.csv
joinquant_real_benchmark_prices.csv
joinquant_cash_dividends.csv
```

## Benchmark

Initial utilities platform benchmark:

```text
000007.XSHG
```

Rationale:

```text
JoinQuant index dictionary lists 000007.XSHG as 公用指数 with long history.
```

This is sufficient for local simulation and attribution preparation. Benchmark choice must still be rechecked before platform replication.

## Readiness Result

Command:

```text
python -m v5.cli utilities-daily-backtest ready --execution-price-csv database/processed/utilities_joinquant_real_daily_prices.csv --benchmark-csv database/processed/utilities_joinquant_real_benchmark_prices.csv
```

Result:

```text
status = ready
blockers = []
panel_rebalance_dates = 20
state_covered_rebalance_dates = 20
execution_price_dates = 1228
benchmark_dates = 1228
```

## Local Simulation Result

Command:

```text
python -m v5.cli utilities-daily-backtest run examples/utilities_demand_state_v51f_strategy.json --execution-price-csv database/processed/utilities_joinquant_real_daily_prices.csv --benchmark-csv database/processed/utilities_joinquant_real_benchmark_prices.csv --benchmark-id 000007.XSHG --out local_daily_backtests_utilities_v51f
```

Output:

```text
local_daily_backtests_utilities_v51f/utilities_demand_state_v51f/
```

Generated files:

```text
summary.json
daily_returns.csv
holdings.csv
trades.csv
dividends.csv
rebalance_signals.csv
```

Summary metrics:

```text
strategy_return = 200.92%
annualized_return = 25.37%
benchmark_return = 15.86%
excess_return = 185.06%
max_drawdown = 27.53%
beta = 1.0837
sharpe = 1.0533
information_ratio = 1.2939
max_drawdown_interval = 2024-05-29,2024-09-11
```

## Known Limitations

Cash dividends are not yet complete for utilities platform replication.

Attempted:

```text
python -m v5.cli collect-dividends database/processed/utilities_cashflow_value_v51b_panel/panel.csv --database-dir database --start-date 2021-05-01 --end-date 2026-05-31 --output-prefix utilities
```

Result:

```text
timed out after about 5 minutes
```

Interpretation:

```text
The strategy can run local JoinQuant-like simulation now, but platform replication must not be approved until utilities cash dividends are collected through a faster or resumable path.
```

## PM Decision

V5.1f may proceed to:

```text
local daily simulation review
```

V5.1f may not proceed to:

```text
accepted_strategy
```

until:

```text
1. utilities cash dividends are collected or explicitly waived for a price-only attribution test;
2. local-vs-JoinQuant platform daily attribution is completed;
3. PM confirms the benchmark contract;
4. forward / paper-trading tracking starts.
```

