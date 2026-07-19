# V5.3g Insurance Platform Replication Export Request V1

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

Prepare platform replication for the frozen V5.3g insurance P/EV candidate.

This is an attribution task only. The JoinQuant run must not change factor logic, selection count, rebalance timing, benchmark, dividend handling, or execution assumptions to improve results.

## Frozen Contract

```text
Select 3 core insurance names with the lowest PIT P/EV at each quarterly rebalance.
```

Frozen model file:

```text
examples/insurance_pev_value_v53g_strategy.json
```

Local daily packet:

```text
local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/
```

## Required Backtest Window

```text
2021-05-01 to 2026-05-31
```

This window is platform-confirmation context only. It must not be used for research tuning.

## Required JoinQuant Exports

After running the frozen JoinQuant version, export:

| Export | Required | Purpose |
| --- | --- | --- |
| Daily result / daily returns CSV | yes | Local-vs-platform daily NAV attribution |
| Transaction / trade detail CSV | yes | Order, price, commission, lot-size attribution |
| Position CSV | yes | Holding, cash, and rebalance attribution |
| Full log TXT | yes | Signal, selection, data coverage, and execution diagnostics |

## Local Attribution Inputs

Required local files:

```text
local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/daily_returns.csv
local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/rebalance_signals.csv
local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/holdings.csv
local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/trades.csv
local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/dividends.csv
local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/summary.json
```

## Expected Difference Sources

Differences may be acceptable only if explained by:

- JoinQuant 09:40 or intraday scheduled execution versus local daily-open approximation;
- benchmark adjustment and price source differences for `399809.XSHE`;
- dividend ex-date versus actual cash-arrival timing;
- dividend tax treatment;
- 100-share lot rounding;
- commission minimums;
- suspended, limit-up, or limit-down handling;
- residual cash after target-weight orders.

## Engineering Compatibility Notes

- Use `order_target_value(code, target_value)` rather than `order_target_percent`.
- Some JoinQuant runtimes do not expose `order_target_percent`; using it can stop the backtest before the first successful rebalance.
- Target value should be computed as `context.portfolio.total_value * target_weight`.

## Stop Rule

Do not edit V5.3g to fit JoinQuant output.

If platform replication fails, status must be one of:

```text
platform_replication_needs_attribution
data_gap
execution_contract_mismatch
benchmark_contract_mismatch
```

It must not become a new tuned strategy inside the V5.3g ID.
