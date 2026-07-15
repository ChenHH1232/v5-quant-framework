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
