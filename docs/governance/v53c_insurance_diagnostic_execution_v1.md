# V5.3c Insurance Diagnostic Execution V1

Date: 2026-07-17

Status:

```text
insurance_diagnosis_executed_needs_data_model_decision
```

Not status:

```text
accepted_strategy
paper_trading_ready
joinquant_code_ready
platform_replication_approved
```

## Scope

This run executes the V5.3c insurance diagnostic workflow. It does not tune selection count, factor weights, benchmark, or trading rules.

The diagnostic target is:

```text
insurance_low_pb_only_v53c
```

## Inputs Checked

| Input | Path | Status |
| --- | --- | --- |
| Formal PIT validation | `validation_formal_v53c_insurance_low_pb_only/insurance_low_pb_only_v53c` | available |
| Local daily simulation | `local_daily_backtests_insurance_v53c/insurance_low_pb_only_v53c` | available |
| Overfit audit | `validation_overfit_v53c_insurance/insurance_low_pb_only_v53c` | available |
| Insurance knowledge packet | `knowledge/research_agent/references/insurance_data_field_map.md` | available |
| Diagnostic workflow table | `docs/governance/v53c_insurance_diagnostic_workflow_table_v1.md` | available |

## Formal Validation Restatement

| Item | Value |
| --- | ---: |
| PIT leakage violations | 0 |
| Low PB mean IC | 0.2004 |
| Low PB mean RankIC | 0.2023 |
| Positive IC ratio | 70.45% |
| Equal-weight core insurance cumulative return | 79.01% |
| High-dividend reference cumulative return | 86.56% |
| Low PB-only top 3 cumulative return | 137.12% |

PM read:

```text
Low PB is a real research signal, but not yet a deployable insurance strategy.
```

## Robustness Restatement

| Selection count | Cumulative return | Read |
| ---: | ---: | --- |
| 2 | 180.94% | strongest but most concentrated |
| 3 | 137.12% | frozen V5.3c case |
| 4 | 56.42% | materially weaker |
| 5 | 67.16% | materially weaker |

PM read:

```text
The edge is concentration-sensitive. This blocks platform replication until small-universe risk is explicitly accepted or repaired.
```

## Local Daily Simulation Restatement

| Item | Value |
| --- | ---: |
| Window | 2021-05-01 to 2026-05-31 |
| Strategy return | 42.03% |
| Annualized return | 7.47% |
| Benchmark | 399809.XSHE |
| Benchmark return | -3.02% |
| Excess return | 45.05% |
| Max drawdown | 33.02% |
| Max drawdown interval | 2021-07-06 to 2022-10-28 |
| Dividend status | real net cash dividends included |
| Experiment layer | engineering_smoke_test |

PM read:

```text
Execution is mechanically feasible, but the drawdown is large and this remains an engineering smoke test rather than platform replication.
```

## Failure-Year Attribution

Output:

```text
failure_attribution_insurance_v53c/insurance_low_pb_only_v53c
```

| Year | Strategy return | Benchmark return | Excess return | Max drawdown | Dividend cash | PM read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2021 | -12.00% | -16.72% | 4.73% | 14.52% | 36,618.72 | industry drawdown; low PB adds relative value but loses money |
| 2022 | -1.26% | -8.27% | 7.01% | 28.26% | 47,763.20 | low PB again adds relative value but does not avoid drawdown |
| 2026 | -22.56% | -19.59% | -2.98% | 30.99% | 0.00 | unresolved failure; low PB underperforms benchmark and has no dividend cushion |

PM read:

```text
2021 and 2022 are not fatal because low PB outperformed the insurance benchmark. 2026 remains unresolved and blocks platform replication.
```

## Overfit Audit

| Item | Value |
| --- | ---: |
| Blockers | 0 |
| Needs review | 1 |
| Passed checks | 13 |

Only needs-review item:

```text
2021-05 to 2026-05 is a platform-confirmation / engineering window, not clean out-of-sample acceptance evidence.
```

## Data Model Diagnosis

The insurance knowledge packet already marks the following as important but not yet fully repaired for formal PIT use:

| Variable group | Examples | Current diagnostic status |
| --- | --- | --- |
| Embedded value | EV, P/EV, EV growth | required for insurance-specific value model; currently deferred |
| New business value | NBV, NBV growth | required for life-insurance franchise quality; currently deferred |
| Solvency | core / comprehensive solvency adequacy ratio | required for balance-sheet quality and dividend safety; currently deferred |
| Liability pressure | surrender, reserve pressure, liability duration | economically important; source inventory incomplete |
| Investment state | investment yield, equity exposure, rate state | needed to explain rate/equity sensitivity; incomplete as model input |
| Equity state | broad equity / insurance index trend and drawdown | available as diagnostic state; not approved as timing rule |

## Step Status Against Diagnostic Workflow

| Step | Gate | Status | Read |
| ---: | --- | --- | --- |
| 1 | PM diagnostic gate | passed | diagnosis-only scope preserved |
| 2 | Research knowledge repair | partial | insurance-specific missing variables identified |
| 3 | Data source inventory | partial | field map exists, but EV/NBV/solvency PIT sources are not yet complete |
| 4 | PIT universe audit | passed_with_risk | PIT validation passed, but universe is very small |
| 5 | Baseline restatement | passed | V5.3c evidence restated without tuning |
| 6 | Failure-year attribution | passed_with_unresolved_2026 | 2021/2022 explainable as relative outperformance; 2026 unresolved |
| 7 | Interest-rate state diagnosis | pending | real-rate state not yet enough to explain 2026 |
| 8 | Equity-market state diagnosis | pending | equity-state attribution still needed |
| 9 | EV / NBV availability decision | pending | required before V5.3d |
| 10 | Solvency and liability-side decision | pending | required before V5.3d |
| 11 | Concentration audit | needs_review | top2/top3 materially stronger than top4/top5 |
| 12 | Local daily simulation review | passed_with_review | feasible, but max drawdown remains large |
| 13 | Data-model PM decision | this_record | simple low-PB model cannot proceed to platform replication |
| 14 | Optional Test-2 design | blocked_until_data_model | V5.3d requires data repair first |

## PM Decision

```text
needs_insurance_specific_data_model
```

V5.3c should not proceed to JoinQuant code or platform replication now.

## Why

- The low-PB signal is statistically visible.
- Local daily simulation is mechanically feasible.
- Real dividends and an insurance benchmark are already connected.
- But the simple low-PB model does not explain 2026.
- Results are sensitive to small-universe concentration.
- Insurance-specific variables remain missing or deferred: EV/NBV, solvency, liability-side pressure, and investment/rate state.

## Allowed Next Work

- Build an insurance data availability matrix for EV/NBV, solvency, investment yield, liability pressure, and equity/rate states.
- Use annual reports, solvency reports, insurer disclosures, JQData/DataJQ, Tushare, and paid research sources if available.
- Let Research Agent propose V5.3d only after source coverage and PIT visible dates are known.

## Blocked Next Work

- No selection-count tuning.
- No weight tuning.
- No defensive overlay added from 2021-2026 results.
- No JoinQuant strategy code.
- No paper trading.

## Next Gate

```text
insurance_specific_data_availability_matrix
```

Data availability matrix:

```text
docs/governance/v53c_insurance_data_availability_matrix_v1.md
```
