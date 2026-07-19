# V5.5i Port / Rail Business Purity Gate PM Decision V1

Date: 2026-07-18

Strategy ID:

```text
port_rail_cashflow_value_operating_diagnostic_v55i_business_purity_gate
```

## PM Decision

V5.5i is the cleaner successor test to V5.5g.

Status:

```text
formal_strategy_candidate
research_pit_validation_passed
business_purity_gate_added
local_daily_smoke_test_completed
overfit_audit_no_blockers_needs_review
platform_replication_not_yet_approved
not_accepted_strategy
```

V5.5i should replace V5.5g as the preferred port / rail candidate for further Engineering review because it removes stocks without PIT-visible core port / rail business-purity evidence.

It is not yet approved for JoinQuant replication because original-report spot checks are still incomplete for `601326.XSHG`, and the strict evidence gate causes no trades in 2021-05 and 2021-07 under the existing 80% coverage rule.

## Research Fix

V5.5h repaired the Eastmoney segment classifier:

| Item | Result |
| --- | ---: |
| raw Eastmoney rows | 4,226 |
| segment evidence rows | 476 |
| PIT usable rows | 213 |
| covered companies | 22 / 23 |

V5.5i then applied a strict business-purity gate:

```text
allowed_tags = core_port_operator, core_rail_operator
```

Gate output:

| Item | Value |
| --- | ---: |
| input rows | 475 |
| kept rows | 404 |
| removed rows | 71 |
| kept codes | 21 |
| covered dates | 21 |

Evidence paths:

```text
数据库/processed/port_rail_business_purity_gate_v55i/panel_core_port_rail_only.csv
数据库/processed/port_rail_business_purity_gate_v55i/removed_by_business_purity_gate.csv
数据库/processed/port_rail_business_purity_gate_v55i/business_purity_gate_manifest.json
```

## Original Report Spot Check

Focused targets:

```text
000507.XSHE
000905.XSHE
600125.XSHG
600279.XSHG
601326.XSHG
```

CNINFO annual report download:

| Item | Value |
| --- | ---: |
| requested reports | 30 |
| downloaded reports | 24 |
| missing reports | 6 |

All missing reports are for:

```text
601326.XSHG
```

This requires Shanghai Stock Exchange, company website, Eastmoney F10 report link, or manual source repair.

Eastmoney-vs-original-report spot check on downloaded reports:

| Item | Value |
| --- | ---: |
| reports checked | 24 |
| spot-check rows | 120 |
| pass rows | 113 |
| passed report count | 21 |
| errors | 0 |

Interpretation:

```text
Eastmoney segment item names are broadly consistent with original annual-report text for downloaded reports.
However, this validates table consistency, not exact numeric promotion or final business-purity acceptance.
```

## Formal Validation

Output:

```text
validation_formal_v55i_port_rail_business_purity_gate/port_rail_cashflow_value_operating_diagnostic_v55i_business_purity_gate/formal_validation_summary.json
```

Key results:

| Test | Result |
| --- | ---: |
| PIT leakage audit | pass |
| row count | 404 |
| date count | 21 |
| equal-weight baseline | 20.35% |
| high-dividend baseline | 34.07% |
| V5.5i composite | 64.71% |

Rolling validation:

| Year | Result |
| --- | ---: |
| 2023 | 7.83% |
| 2024 | 26.84% |
| 2025 | 10.28% |
| 2026 | -4.84% |

Factor evidence:

| Factor | Mean IC | Mean RankIC | Interpretation |
| --- | ---: | ---: | --- |
| dividend_yield | 0.1198 | 0.1103 | supportive |
| operating_cash_flow_yield | 0.1199 | 0.1235 | supportive |
| free_cash_flow_yield | 0.1067 | 0.0930 | supportive |
| low_price_to_book | 0.2097 | 0.1980 | strongest |
| capex_burden | -0.0056 | 0.0407 | diagnostic only |
| operating_state_score | 0.0735 | 0.0773 | diagnostic only |

PM interpretation:

```text
Business-purity filtering lowers the composite from V5.5g's 74.96% formal result to 64.71%, but the hypothesis still beats equal-weight and high-dividend baselines.
```

## Local Daily Engineering Smoke Test

Output:

```text
local_daily_backtests_port_rail_v55i_business_purity_gate/port_rail_cashflow_value_operating_diagnostic_v55i_business_purity_gate/summary.json
```

Execution assumptions:

```text
daily open execution
daily close valuation
100-share lot rounding
0.03% open / close commission
20% tax-adjusted cash dividends
516970.XSHG proxy benchmark
no defensive overlay
value trap guard disabled
```

Metrics:

| Metric | Value |
| --- | ---: |
| first signal / trade | 2021-10-08 |
| signal count | 19 |
| strategy return | 56.67% |
| annualized return | 9.65% |
| benchmark proxy return | 17.69% |
| excess return | 38.98% |
| max drawdown | 20.45% |
| drawdown interval | 2023-05-08 to 2024-01-22 |
| Sharpe | 0.577 |
| information ratio | 0.243 |

Why first trade moved from 2021-05-06 to 2021-10-08:

```text
The strict PIT business-purity gate leaves only 16 / 22 candidates in 2021-05 and 2021-07.
The existing Engineering coverage rule requires at least 80% rebalance-date coverage, so those dates are correctly blocked.
```

## Overfit Audit

Output:

```text
validation_overfit_v55i_port_rail_business_purity_gate/port_rail_cashflow_value_operating_diagnostic_v55i_business_purity_gate/overfit_audit_summary.json
```

Result:

| Item | Count |
| --- | ---: |
| blockers | 0 |
| pass checks | 12 |
| needs review | 2 |

Needs review:

```text
2021-05 to 2026-05 remains a platform-confirmation window, not acceptance evidence.
Parameter perturbation contract should be standardized before final promotion.
```

## PM Next Gate

Approve:

```text
V5.5i as preferred port / rail formal_strategy_candidate
Engineering local smoke test completed
```

Do not approve yet:

```text
platform_replication
paper_trading
accepted_strategy
joinquant_code_ready
```

Next required work:

1. Repair `601326.XSHG` original annual-report source through SSE / company site / Eastmoney report link / manual import.
2. Decide whether 2021-05 and 2021-07 should remain blocked by the 80% coverage rule or whether V5.5i should explicitly start from 2021-10-08.
3. If PM approves the later start date, run platform replication as attribution-only work; do not tune returns.

