# V5.1f Utilities Overfit Audit V1

Date: 2026-07-16

Owner: Engineering Agent

Layer: engineering audit gate

## Purpose

This record freezes the first Engineering Agent anti-overfitting audit gate for V5. The gate is reusable across bank, utilities, and later sector tests. It is not a strategy acceptance report.

The audit checks whether a candidate has obvious engineering-level risks before PM can consider promotion:

- survivorship bias in the stock universe,
- future leakage in factor and state visibility dates,
- full-sample normalization or other future-function smells,
- use of the 2021-05 to 2026-05 platform replication window as clean out-of-sample evidence,
- random backtest-window stability,
- execution timing sensitivity proxy,
- parameter perturbation validation contract,
- parameter perturbation evidence from rebalance signals.

## Runner

Command:

```powershell
$env:PYTHONPATH='src'
python -m v5.cli overfit-audit examples\utilities_demand_state_v51f_strategy.json `
  --panel 数据库\processed\utilities_cashflow_value_v51b_panel\panel.csv `
  --daily-returns-csv local_daily_backtests_utilities_v51f\utilities_demand_state_v51f\daily_returns.csv `
  --rebalance-signals-csv local_daily_backtests_utilities_v51f\utilities_demand_state_v51f\rebalance_signals.csv `
  --out validation_overfit
```

Implementation:

- `src/v5/overfit_audit_runner.py`
- CLI entry: `v5 overfit-audit`
- Tests: `tests/test_overfit_audit_runner.py`

## V5.1f Result

Audit status: `needs_review`

Blockers: `0`

Needs review: `1`

Passed checks: `13`

The only review item is `sample_contamination / platform_window_usage`.

Reason: the local daily test overlaps the 2021-05 to 2026-05 platform confirmation window. This window may be used for local-vs-JoinQuant replication and execution alignment, but it must not be used as clean out-of-sample acceptance evidence.

## Decision

V5.1f remains:

- `formal_strategy_candidate_pending_engineering_audit` from the strategy spec,
- platform-frozen signal test passed,
- not an accepted strategy.

PM may only promote after Quant Validation supplies independent evidence, and future/paper-trading records remain separate from the platform replication window.

## Required Follow-Up

Before any candidate is promoted beyond formal candidate:

- run `v5 overfit-audit`,
- resolve all `blocker` items,
- PM/Quant explicitly review all `needs_review` items,
- keep 2021-05 to 2026-05 labeled as platform replication context,
- keep future/paper trading records as the next true forward evidence layer.
