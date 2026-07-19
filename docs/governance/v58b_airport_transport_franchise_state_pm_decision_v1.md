# V5.8b Airport / Transport Franchise State PM Decision V1

Date: 2026-07-19

Owner: Project Manager Agent, Research Agent, Quant Validation Agent

Status:

```text
research_pit_validation_completed
data_workflow_replication_passed
strategy_candidate_failed
not_engineering_handoff
archive_until_new_domain_data
```

## Why V5.8b Was Run

V5.8 was rejected because it treated airport operating recovery as a linear positive factor. Quant evidence showed:

```text
airport_operating_state_score mean IC = -0.1264
operating_state_top3 cumulative return = -21.10%
```

Research Agent redesigned the hypothesis:

```text
For a dividend low-volatility cash-flow basket, prefer stable airport operating state and penalize commercial / concession / rental exposure risk until contract and policy evidence is reviewed.
```

Research framework:

```text
knowledge/research_agent/factor_theory/airport_transport_franchise_state_framework_v58b.md
```

Strategy under test:

```text
airport_transport_franchise_state_v58b
```

## Data And Validation

Panel:

```text
数据库/processed/airport_transport_formal_panel_v58b/panel.csv
```

Validation output:

```text
validation_formal_v58b_airport_transport/airport_transport_franchise_state_v58b/
```

Data checks:

| Check | Result |
| --- | ---: |
| PIT panel rows | 80 |
| Rebalance dates | 20 |
| Operating-state coverage | 100% |
| PIT leakage audit | pass |

## Quant Evidence

Baseline results:

| Case | Cumulative return |
| --- | ---: |
| Equal-weight airport pool | -17.80% |
| High-dividend top3 | -7.35% |
| Low state-instability top3 | -13.92% |
| Low commercial-exposure top3 | -5.82% |
| Franchise state-risk composite | -5.18% |

Factor IC / RankIC:

| Factor | Mean IC | Mean RankIC | Interpretation |
| --- | ---: | ---: | --- |
| dividend_yield | 0.2774 | 0.1962 | strongest remaining signal |
| low_price_to_book | 0.1918 | 0.0600 | positive but weak rank evidence |
| operating_cash_flow_yield | 0.0613 | 0.0200 | weak positive |
| capex_burden | 0.0667 | 0.0900 | weak positive risk signal |
| airport_operating_state_instability | 0.0561 | -0.0200 | not reliable |
| airport_commercial_exposure_risk | 0.0997 | 0.0445 | mild evidence, needs source repair |

Rolling validation:

| Year | Cumulative return |
| --- | ---: |
| 2023 | -14.94% |
| 2024 | 7.12% |
| 2025 | 9.25% |
| 2026 | -14.88% |

Robustness note:

```text
selection_count_2 is positive, but selection_count_3 is negative and selection_count_4 falls back to the weak equal-weight pool.
With only four airport names, selection_count_2 is a concentration-sensitive result and cannot be used as acceptance evidence.
```

## PM Decision

Do not promote V5.8b.

Airport / transport is archived as:

```text
workflow_replication_passed
strategy_candidate_failed
blocked_until_new_domain_data
```

Reason:

```text
The V5 workflow successfully replicated to airport operators: PIT universe, reviewed operating data, CNINFO PDF checks, formal validation and failure return all worked.
The strategy itself is not good enough: absolute return remains negative, rolling validation is unstable, and state-risk factors do not provide robust incremental evidence.
```

## Restart Conditions

Only restart airport / transport if Research Agent can add new domain data:

```text
international passenger recovery versus 2019
duty-free / commercial lease contract terms
rent concession / minimum annual guarantee changes
airport fee / policy changes
capex project cycle and capacity expansion evidence
annual-report business-purity spot-check
```

Until then:

```text
No Engineering handoff.
No local daily simulation.
No JoinQuant script.
Do not tune selection_count or weights on 2021-2026.
```

Historical performance alone is never sufficient evidence for accepting a strategy.
