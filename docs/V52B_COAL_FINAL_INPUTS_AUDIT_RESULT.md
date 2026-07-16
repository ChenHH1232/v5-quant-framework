# V5.2b Coal Final Inputs Audit Result

Date: 2026-07-16

Project:

```text
V5.2b Coal Cash-Flow Cycle Value / Capex Policy
```

PM status:

```text
engineering_audit_inputs_repaired_external_state_still_blocked
```

Not status:

```text
formal_strategy_candidate
platform_replication_passed
accepted_strategy
```

## What Was Repaired

Engineering Agent generated the missing audit inputs:

```text
local_daily_backtests_coal_v52b/coal_cashflow_cycle_value_v52b_capex_policy/daily_returns.csv
local_daily_backtests_coal_v52b/coal_cashflow_cycle_value_v52b_capex_policy/rebalance_signals.csv
```

The daily runner now also records audit fields in `rebalance_signals.csv`:

- `factor_visible_date`
- `business_tag_visible_date`
- `external_state_visible_date`
- `universe_visible_date`
- `case`
- `factor`
- `experiment_layer`

This repairs the previous Engineering blocker where overfit audit could not evaluate daily-return stability or rebalance-signal governance.

## Local Daily Simulation Result

Runner:

```text
daily JoinQuant-like simulation
```

Benchmark:

```text
515220.XSHG
```

Reason:

```text
000820.XSHG returned unusable daily open / close values in the current JoinQuant data pull.
```

Window:

```text
2021-05-01 to 2026-05-31
```

This window is platform confirmation / simulation reference only. It must not be used as clean out-of-sample acceptance evidence.

Key metrics:

| Metric | Value |
| --- | ---: |
| Strategy return | 133.69% |
| Annualized return | 19.03% |
| Benchmark return | 94.84% |
| Excess return | 38.85% |
| Max drawdown | 28.11% |
| Max drawdown interval | 2024-05-29 to 2024-09-11 |
| Daily count | 1228 |
| Rebalance signal count | 16 |

## Overfit Audit Result

Output:

```text
validation_overfit_v52b_final_inputs/coal_cashflow_cycle_value_v52b_capex_policy_final_inputs/overfit_audit_summary.json
```

Status:

```text
needs_review
```

Summary:

| Item | Count |
| --- | ---: |
| Checks | 14 |
| Blockers | 0 |
| Needs review | 1 |
| Pass | 13 |

Remaining review item:

```text
platform_window_usage
```

Reason:

```text
2021-05 to 2026-05 overlaps the platform-confirmation window and cannot be treated as clean out-of-sample acceptance.
```

## Formal Validation Result

Output:

```text
validation_formal_v52b_final_inputs/coal_cashflow_cycle_value_v52b_capex_policy/formal_validation_summary.json
```

Status:

```text
formal_validation_completed_not_acceptance
```

Key evidence:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio |
| --- | ---: | ---: | ---: |
| Operating cash-flow yield | 0.1370 | 0.1359 | 63.64% |
| Free cash-flow yield | 0.1167 | 0.1152 | 63.64% |
| Low PB | 0.0886 | 0.1080 | 59.09% |
| Low PE | 0.0714 | 0.0836 | 54.55% |

Weak-year result:

| Year | Selected cumulative return | Positive ratio | Interpretation |
| --- | ---: | ---: | --- |
| 2018 | -35.94% | 0.00% | Severe sector-cycle drawdown; selected basket only slightly outperformed the broad coal universe. |
| 2024 | 6.70% | 75.00% | Weak absolute year, but selected basket outperformed broad coal and low-PB references. |

## Cycle-State Validation Result

Output:

```text
validation_formal_v52b_final_inputs_cycle_state/coal_cashflow_cycle_value_v52b_capex_policy_final_inputs/cycle_state_coking_coal_price_state/cycle_state_validation_summary.json
```

Status:

```text
cycle_state_validation_completed_not_acceptance
```

Cycle-state conclusion:

- Coking-coal price state is useful for interpretation.
- OCF and FCF evidence is strongest in strong-price states.
- Weak-state buckets are too sparse for strategy acceptance.
- Inventory / output state remains missing from the current V5.2 data packet.

## External State Blocker

The external state panel is not complete enough for formal promotion.

Current formal-state manifest:

| Metric | PIT usable history |
| --- | ---: |
| Thermal coal price state | 92 |
| Coking coal price state | 160 |
| Coal inventory or output state | 1 |

Decision:

```text
External state is still blocked because official raw-coal output / inventory history is not PIT-ready.
```

This means 2018 cannot be explained with enough ex-ante cycle-state evidence. A price-only explanation is not enough for a cyclical commodity sector.

## PM Decision

V5.2b is not promoted.

Current classification:

```text
workflow_replication_passed_strategy_candidate_failed
```

Updated sub-status:

```text
engineering_audit_inputs_repaired
external_state_history_still_blocked
research_pit_validation_completed_not_acceptance
```

Reason:

- Engineering audit input blocker is repaired.
- Overfit audit now runs and has no hard blocker.
- Formal IC / RankIC evidence is positive but not decisive.
- 2018 remains a severe failure year.
- Inventory / output cycle-state data is still missing.
- 2021-2026 simulation is not clean out-of-sample acceptance.

## Next Allowed Actions

Allowed:

- manually import official NBS raw-coal output / inventory history;
- add a verified source for coal inventory or production state;
- rerun state-bucket validation after the official state panel is complete;
- keep V5.2b as a negative-control and workflow-replication memory.

Not allowed:

- write JoinQuant production strategy code;
- start paper trading;
- label as formal strategy candidate;
- accept based on high historical return.

