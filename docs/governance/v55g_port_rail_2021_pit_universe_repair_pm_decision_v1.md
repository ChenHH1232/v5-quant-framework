# V5.5g Port / Rail 2021 PIT Universe Repair PM Decision V1

Date: 2026-07-18

Strategy ID:

```text
port_rail_cashflow_value_operating_diagnostic_v55g_repaired_2021
```

Experiment layers:

```text
research_pit_validation
engineering_smoke_test
engineering_smoke_test_local_attribution
```

## PM Decision

V5.5g repairs the V5.5c 2021 no-signal gap.

Status:

```text
formal_strategy_candidate
research_pit_validation_passed
2021_pit_universe_repaired
local_daily_smoke_test_completed
local_daily_attribution_completed
overfit_audit_no_blockers_needs_review
platform_replication_blocked
not_accepted_strategy
```

V5.5g supersedes V5.5c for the specific purpose of repairing the 2021 PIT universe. V5.5c should remain archived as the original candidate that exposed the data-source gap.

## Repair Method

V5.5c used new JoinQuant industry codes:

| Code | Meaning |
| --- | --- |
| `HY03155` | railway transport |
| `HY03159` | port |

These returned zero members before 2021-12-31.

V5.5g repairs 2021 with older PIT-visible industry sources:

| Period | Port source | Rail source |
| --- | --- | --- |
| before 2022 | SW L3 `851711` port + legacy JQ L2 `HY03034` port | SW L3 `851771` railway transport + legacy JQ L2 `HY03029` railway transport |
| 2022 onward | JQ L2 `HY03159` port | JQ L2 `HY03155` railway transport |

V5.5g also adds a 2021-05-06 startup catch-up signal because the comparison window starts mid-quarter on the first tradable day after 2021-05-01.

This repair did not change:

```text
factor weights
factor definitions
selection count
risk controls
defensive overlay
stop loss / take profit
return window
```

## Data Outputs

| Data | Path |
| --- | --- |
| repaired PIT panel | `数据库/processed/port_rail_pit_universe_repair_v55g/panel_repaired_2021.csv` |
| repair manifest | `数据库/processed/port_rail_pit_universe_repair_v55g/collection_manifest.json` |
| repaired operating-state panel | `数据库/processed/port_rail_operating_state_v55g_repaired_2021/panel_operating_state.csv` |
| frozen spec | `examples/port_rail_cashflow_value_operating_diagnostic_v55g_repaired_2021_strategy.json` |

Repair result:

| Item | V5.5c | V5.5g |
| --- | ---: | ---: |
| panel rows | 409 | 475 |
| signal dates | 18 | 21 |
| first local signal | 2022-01-04 | 2021-05-06 |
| first local trade | 2022-01-04 | 2021-05-06 |
| stock count | 23 | 23 |
| repair warnings | n/a | 0 |

## Formal Validation

Output:

```text
validation_formal_v55g_port_rail_repaired_2021/port_rail_cashflow_value_operating_diagnostic_v55g_repaired_2021/formal_validation_summary.json
```

Key evidence:

| Test | Result |
| --- | ---: |
| PIT leakage audit | pass |
| row count | 475 |
| date count | 21 |
| equal-weight port / rail baseline | 21.73% |
| high-dividend top8 baseline | 32.72% |
| V5.5g composite | 74.96% |
| common-sample composite | 74.96% |

Rolling validation:

| Year | Result |
| --- | ---: |
| 2023 | 12.28% |
| 2024 | 19.32% |
| 2025 | 14.90% |
| 2026 | -4.84% |

Factor evidence:

| Factor | Mean IC | Mean RankIC | PM interpretation |
| --- | ---: | ---: | --- |
| dividend_yield | 0.1040 | 0.0848 | supportive |
| operating_cash_flow_yield | 0.1034 | 0.1053 | supportive |
| free_cash_flow_yield | 0.1115 | 0.0918 | supportive |
| low_price_to_book | 0.2097 | 0.2035 | strongest |
| capex_burden | -0.0424 | 0.0316 | weak, risk diagnostic |
| operating_state_score | 0.0430 | 0.0319 | diagnostic only |

## Local Daily Smoke Test

Output:

```text
local_daily_backtests_port_rail_v55g_repaired_2021/port_rail_cashflow_value_operating_diagnostic_v55g_repaired_2021/summary.json
```

Execution assumptions:

```text
daily open execution
daily close valuation
100-share lot rounding
0.03% open / close commission
20% tax-adjusted cash dividends
no defensive overlay
value trap guard disabled because no hard guard is approved
```

Metrics:

| Metric | Value |
| --- | ---: |
| signal count | 21 |
| daily rows | 1,228 |
| trades | 223 |
| dividend events | 44 |
| strategy return | 78.52% |
| annualized return | 12.63% |
| benchmark proxy return | 17.69% |
| excess return | 60.83% |
| max drawdown | 20.20% |
| drawdown interval | 2023-05-08 to 2024-01-22 |
| Sharpe | 0.693 |
| information ratio | 0.399 |

Annual attribution:

| Year | Strategy | Benchmark proxy | Dividend cash | Note |
| --- | ---: | ---: | ---: | --- |
| 2021 | 8.54% | 22.55% | 65,346.00 | repaired and invested |
| 2022 | 6.30% | -11.96% | 60,635.18 | active |
| 2023 | 10.18% | -7.69% | 63,349.80 | active |
| 2024 | 21.69% | 13.30% | 52,474.12 | active |
| 2025 | 10.70% | 6.27% | 58,516.75 | active |
| 2026 | 4.25% | -1.85% | 0.00 | partial year |

## Overfit Audit

Output:

```text
validation_overfit_v55g_port_rail_repaired_2021/port_rail_cashflow_value_operating_diagnostic_v55g_repaired_2021/overfit_audit_summary.json
```

Result:

| Item | Count |
| --- | ---: |
| blockers | 0 |
| pass checks | 11 |
| needs_review checks | 3 |

Needs review items:

1. First-date constituent smell test: repaired first date already has broad coverage, so the repair source must remain disclosed.
2. Platform-window usage: 2021-05 to 2026-05 is still a platform confirmation window, not acceptance evidence.
3. Parameter perturbation contract: should be further standardized before final acceptance review.

PM interpretation:

```text
No blocker prevents local engineering review.
These review items still block accepted_strategy.
```

## Remaining Blockers

V5.5g is not ready for platform replication until:

```text
original operating evidence review is completed;
benchmark policy is finalized;
PM approves JoinQuant replication as attribution-only work.
```

Operating evidence still needs original-source review for:

```text
port revenue share;
rail revenue share;
cargo throughput;
container throughput;
rail freight volume;
tariff / pricing policy;
capex project commitments.
```

## Next Gate

```text
V5.5h operating evidence review or platform replication approval decision
```

Recommended PM path:

```text
Approve V5.5g as the repaired local candidate.
Do not write JoinQuant code yet unless the PM explicitly accepts operating-evidence review as a separate post-local gate.
```
