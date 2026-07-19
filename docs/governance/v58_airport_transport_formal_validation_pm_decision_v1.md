# V5.8 Airport / Transport Formal Validation PM Decision V1

Date: 2026-07-19

Owner: Project Manager Agent, Quant Validation Agent

Status:

```text
research_pit_validation_completed
data_workflow_replication_passed
strategy_hypothesis_not_promoted
not_engineering_handoff
```

## Scope

Strategy under test:

```text
airport_transport_cashflow_operating_state_v58
```

Panel:

```text
数据库/processed/airport_transport_formal_panel_v58/panel.csv
```

Validation output:

```text
validation_formal_v58_airport_transport/airport_transport_cashflow_operating_state_v58/
```

## Data Gate

The airport operating-state data gate passed for research validation:

| Check | Result |
| --- | ---: |
| PIT panel rows | 80 |
| Rebalance dates | 20 |
| Operating-state coverage | 100% |
| CNINFO original PDF sample checks | 12 / 12 |
| PIT leakage audit | pass |

Remaining data limitation:

```text
Business-purity evidence still relies on Eastmoney first-layer segment evidence.
Annual-report business-purity spot-check is still required before any strategy-candidate promotion.
```

## Quant Evidence

Baseline results:

| Case | Cumulative return |
| --- | ---: |
| Equal-weight airport pool | -17.80% |
| High-dividend top3 | -7.35% |
| Cash-flow top3 | -10.60% |
| Operating-state top3 | -21.10% |
| Composite | -4.99% |

Factor IC / RankIC:

| Factor | Mean IC | Mean RankIC | Interpretation |
| --- | ---: | ---: | --- |
| dividend_yield | 0.2774 | 0.1962 | strongest positive signal |
| low_price_to_book | 0.1918 | 0.0600 | positive but not enough alone |
| operating_cash_flow_yield | 0.0613 | 0.0200 | weak positive |
| free_cash_flow_yield | 0.0766 | 0.0000 | weak / unstable |
| capex_burden | 0.0667 | 0.0900 | weak positive risk signal |
| airport_operating_state_score | -0.1264 | -0.0100 | not a positive alpha factor |

Rolling validation:

| Year | Cumulative return |
| --- | ---: |
| 2023 | -14.94% |
| 2024 | 7.12% |
| 2025 | 9.25% |
| 2026 | -14.88% |

Robustness:

```text
Selection count 2 and 3 are similar, but selection count 4 falls back to the weak equal-weight pool.
Weight scaling around OCF and operating state does not produce a stable improvement large enough for promotion.
```

## PM Decision

Do not promote V5.8 airport / transport to formal_strategy_candidate.

Reason:

```text
The data workflow replicated successfully, but the research hypothesis is not strong enough.
The composite improves versus simple baselines in relative terms, but absolute cumulative return remains negative and rolling years are unstable.
The operating-state score fails as a positive standalone alpha factor.
```

Allowed next action:

```text
Return to Research Agent.
Treat airport operating-state variables as explanation / risk-state candidates.
Do not tune weights on the 2021-2026 window.
Design a narrower hypothesis before another Quant loop.
```

Recommended research reset:

```text
1. Separate airport franchise types:
   - hub airport with international / duty-free exposure
   - regional domestic airport

2. Treat passenger recovery as a state bucket, not a linear positive factor.

3. Add commercial / duty-free / rental exposure and policy risk as business-model variables.

4. Keep dividend and low PB as benchmark signals, but do not assume airport operators fit the broad dividend low-volatility cash-flow basket.
```

Historical performance alone is never sufficient evidence for accepting a strategy.
