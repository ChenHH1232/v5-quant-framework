# Platform Replication Workflow

Purpose:

Make local-vs-JoinQuant platform replication a repeatable Engineering Agent workflow, with Project Manager Agent gates that prevent data gaps, mixed experiment layers, or false acceptance.

Experiment layer:

```text
platform_replication
```

## Required Inputs

Local run directory:

```text
local_daily_backtests.../<strategy_id>/
```

Required local files:

- `daily_returns.csv`
- `rebalance_signals.csv`
- `trades.csv`
- `holdings.csv`
- `dividends.csv`

Required platform exports:

- JoinQuant daily result CSV
- JoinQuant transaction CSV
- JoinQuant position CSV

Optional:

- JoinQuant log TXT with guard and selected-code lines.

## JoinQuant Warm-Up Data Contract

JoinQuant backtest start date is the evaluation window start, not the earliest data date a strategy may read.

If the strategy needs data before the backtest start date, the JoinQuant script must preload the required history at initialization or before the first rebalance. Do not let the first rebalance run with blank warm-up state.

Examples that require pre-start reads:

- moving averages or volatility windows;
- trailing dividend yield and dividend cash history;
- external macro/state variables with publication lag;
- rolling ranks, expanding tertiles, or historical state buckets;
- prior financial statement snapshots needed for point-in-time factor selection.

Engineering rule:

- define `backtest_start_date` and `data_warmup_start_date` separately;
- compute `data_warmup_start_date = backtest_start_date - required_lookback_buffer`;
- in JoinQuant code, call platform data APIs with the warm-up start or sufficient `count` before the first signal;
- log warm-up coverage at initialization and block trading if required history is missing;
- keep the formal performance window unchanged when reporting results.

PM interpretation:

Warm-up reads are allowed when they only use information that would have been visible before each decision date. They are not sample contamination. They become leakage only if the script reads data whose visibility date is after the decision date.

## One-Click Runner

Use:

```text
python -m v5.cli platform-replication-packet <local_run_dir> --strategy-id <strategy_id> --panel-csv <pit_panel.csv> --joinquant-daily-csv <result.csv> --joinquant-transaction-csv <transaction.csv> --joinquant-position-csv <position.csv>
```

The runner performs:

1. PIT panel coverage check.
2. `rebalance_signals.csv` coverage check.
3. Daily NAV attribution.
4. Transaction attribution.
5. Position attribution.
6. PM status decision.

## PM Status Rules

`platform_replication_passed`

Daily, transaction, and position attribution are complete; local signal dates cover platform rebalance dates; remaining residuals are small and explainable.

`pending_attribution`

At least one required attribution file is missing, or daily residuals exceed configured thresholds but no contract/data-gap cause has been proven yet.

`data_gap`

The local PIT panel or local `rebalance_signals.csv` does not cover platform rebalance dates. This blocks interpretation until local data coverage is fixed.

`contract_mismatch`

The local and platform selected-stock contract differs, such as unmatched transaction keys with no data explanation or position code mismatches on rebalance dates.

## V3 Current Packet

V3 passed platform replication after the local PIT panel was extended through `2026-04-01`.

Current accepted residual explanation:

- JoinQuant executes at `09:40`; local execution approximates with daily open.
- Position sizes differ slightly due to prices, cash drift, and hundred-share rounding.
- Benchmark return differs because local and JoinQuant benchmark conventions are not identical.

Important:

Platform replication is not research validation. It must not be used to tune factors or accept a strategy.
