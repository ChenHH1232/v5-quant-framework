# V5.1f Utilities Platform Replication Export Request V1

Date: 2026-07-17

Status:

```text
pending_user_joinquant_run
```

Not status:

```text
platform_replication_passed
accepted_strategy
live_trading_approved
```

## Purpose

Complete the V5.1f utilities golden workflow platform-replication packet without tuning the strategy.

This is an attribution task only. The JoinQuant run must use the frozen script and should not change factor weights, selection count, rebalance timing, guard logic, benchmark, or data window.

## Frozen Script

Use:

```text
exports/joinquant/utilities_demand_state_v51f_joinquant_live_recompute.py
```

Backup / reference near-5Y script:

```text
exports/joinquant/utilities_demand_state_v51f_joinquant_near5y.py
```

## Required Backtest Window

```text
2021-05-01 to 2026-05-31
```

This window is for platform replication and V4/V5 comparison only. It must not be used for research tuning.

## Required Exports

After running the frozen JoinQuant script, export:

| Export | Required | Purpose |
| --- | --- | --- |
| Daily result / daily returns CSV | yes | Local-vs-platform daily NAV attribution |
| Transactions / trade detail CSV | yes | Order, price, commission, lot-size attribution |
| Positions CSV | yes | Holding and rebalance attribution |
| Full log TXT | yes | Signal, selection, guard, and execution diagnostics |

## Local Attribution Inputs

Existing local packet:

```text
local_daily_backtests_utilities_v51f/utilities_demand_state_v51f/
```

Required local files:

```text
daily_returns.csv
rebalance_signals.csv
holdings.csv
trades.csv
dividends.csv
summary.json
```

## PM Acceptance Rule

The platform-replication packet can pass only if differences are explained by known platform mechanics such as:

- JoinQuant scheduled intraday execution versus local daily-open approximation;
- benchmark price source or adjustment differences;
- dividend cash timing or tax handling;
- order rounding, minimum commission, and cash residuals;
- suspended / limit-up / limit-down execution differences.

If unexplained daily return, holdings, or transaction gaps remain, status must be:

```text
platform_replication_needs_attribution
```

## Stop Rule

Do not edit the strategy to improve platform results during this process.

Any proposed strategy logic change must return to:

```text
Research Agent -> Quant Validation Agent -> PM formal candidate decision
```
