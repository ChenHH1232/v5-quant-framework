# V5.5j Port / Rail Reviewed Business Sources PM Decision V1

Date: 2026-07-18

Strategy ID:

```text
port_rail_cashflow_value_operating_diagnostic_v55j_reviewed_business_sources
```

## PM Decision

V5.5j fixes the remaining V5.5i early-period business-purity coverage gap.

Status:

```text
formal_strategy_candidate
research_pit_validation_passed
reviewed_business_source_repair_completed
local_daily_smoke_test_completed
overfit_audit_no_blockers_needs_review
preferred_port_rail_candidate
platform_replication_ready_for_pm_approval
not_accepted_strategy
```

V5.5j should supersede V5.5i as the preferred port / rail candidate.

This is a data-source and PIT business-purity repair, not factor tuning.

## Source Repair

The Research Agent found that several port / rail companies disclose segment revenue by service type rather than by industry label.

Reviewed overrides:

| Code | Company | Repair | PM decision |
| --- | --- | --- | --- |
| `601326.XSHG` | Qinhuangdao Port | Coal / metal ore / general cargo / container / liquid cargo services are reviewed as port-service revenue. | include as core port operator |
| `601880.XSHG` | Liaoning Port | Container / oil / bulk / port value-added / grain / passenger roll-on / auto terminal services are reviewed as port-service revenue for the 2020 PIT startup evidence. | include as core port operator |
| `601333.XSHG` | Guangshen Railway | Passenger, freight, network settlement and other transport services are reviewed as railway operating revenue. | include as core rail operator |

Companies still excluded by the business-purity gate:

| Code | Reason |
| --- | --- |
| `600125.XSHG` | supply-chain management dominates revenue; railway-related revenue is too small for a core rail operator gate |
| `600279.XSHG` | commodity trade dominates revenue in the reviewed early periods |
| early `000905.XSHE` rows | trade-dominant before later port-business evidence becomes visible |
| early `000507.XSHE` rows | no PIT-visible 2020 structured operating evidence in the current reviewed source set |

Evidence paths:

```text
数据库/processed/port_rail_operating_evidence_v55h/reviewed_overrides_v55j/port_rail_reviewed_business_purity_overrides_v55j.csv
数据库/processed/port_rail_operating_evidence_v55h/reviewed_evidence_v55j/port_rail_segment_business_evidence_reviewed_v55j.csv
数据库/processed/port_rail_business_purity_gate_v55j_reviewed_sources/panel_core_port_rail_only_reviewed_sources.csv
```

Coverage after repair:

| Item | V5.5i | V5.5j |
| --- | ---: | ---: |
| input rows | 475 | 475 |
| kept rows | 404 | 410 |
| removed rows | 71 | 65 |
| first two rebalance coverage | 16 / 22 | 18 / 22 |
| minimum coverage ratio | 72.73% | 81.82% |

## Formal Validation

Output:

```text
validation_formal_v55j_port_rail_reviewed_business_sources/port_rail_cashflow_value_operating_diagnostic_v55j_reviewed_business_sources/formal_validation_summary.json
```

Key results:

| Test | Result |
| --- | ---: |
| PIT leakage audit | pass |
| row count | 410 |
| date count | 21 |
| equal-weight baseline | 21.58% |
| high-dividend baseline | 34.98% |
| V5.5j composite | 66.26% |

Rolling validation:

| Year | Result |
| --- | ---: |
| 2023 | 7.83% |
| 2024 | 26.84% |
| 2025 | 10.28% |
| 2026 | -4.84% |

Factor evidence remains stable:

| Factor | Mean IC | Mean RankIC | PM interpretation |
| --- | ---: | ---: | --- |
| dividend_yield | 0.1158 | 0.1087 | supportive |
| operating_cash_flow_yield | 0.1198 | 0.1162 | supportive |
| free_cash_flow_yield | 0.1090 | 0.0952 | supportive |
| low_price_to_book | 0.2104 | 0.1980 | strongest |
| capex_burden | -0.0038 | 0.0432 | diagnostic only |
| operating_state_score | 0.0711 | 0.0711 | diagnostic only |

## Local Daily Engineering Smoke Test

Output:

```text
local_daily_backtests_port_rail_v55j_reviewed_business_sources/port_rail_cashflow_value_operating_diagnostic_v55j_reviewed_business_sources/summary.json
```

Metrics:

| Metric | Value |
| --- | ---: |
| first signal / trade | 2021-05-06 |
| signal count | 21 |
| strategy return | 71.23% |
| annualized return | 11.67% |
| benchmark proxy return | 17.69% |
| excess return | 53.53% |
| max drawdown | 20.46% |
| drawdown interval | 2023-05-08 to 2024-01-22 |
| Sharpe | 0.659 |
| information ratio | 0.349 |

Comparison:

| Version | Business evidence | First trade | Local daily return | PM interpretation |
| --- | --- | --- | ---: | --- |
| V5.5g | repaired PIT universe, weaker business gate | 2021-05-06 | 78.52% | useful reference, less clean |
| V5.5i | strict gate, missing reviewed source repair | 2021-10-08 | 56.67% | clean but under-covered early |
| V5.5j | strict gate plus reviewed source repair | 2021-05-06 | 71.23% | preferred candidate |

## Overfit Audit

Output:

```text
validation_overfit_v55j_port_rail_reviewed_business_sources/port_rail_cashflow_value_operating_diagnostic_v55j_reviewed_business_sources/overfit_audit_summary.json
```

Result:

| Item | Count |
| --- | ---: |
| blockers | 0 |
| pass checks | 12 |
| needs review | 2 |

Needs review:

```text
2021-05 to 2026-05 remains platform-confirmation context, not accepted-strategy evidence.
Parameter perturbation contract still needs standardization before final acceptance review.
```

## PM Next Gate

Approve:

```text
V5.5j as preferred port / rail formal_strategy_candidate
local_daily_smoke_test_completed
platform_replication_ready_for_pm_approval
```

Do not approve:

```text
accepted_strategy
live_trading_approved
return_tuning_allowed
```

Next work:

1. If PM approves, Engineering Agent can prepare JoinQuant replication as attribution-only work.
2. Export JoinQuant daily returns, transactions, positions and logs.
3. Run local vs JoinQuant attribution.
4. Start paper trading only after platform replication differences are explainable.

