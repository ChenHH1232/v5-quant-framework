# V5.8 Telecom Observation Sleeve PM Decision V1

Date: 2026-07-19

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
research_pit_validation
```

## Decision

PM decision:

```text
small_sample_observation_sleeve_approved_for_basket_diagnostic_not_standalone_strategy
```

Telecom operators are not promoted to formal strategy candidate and are not handed to Engineering Agent.

## Evidence Reviewed

Source validation packet:

```text
validation_formal_v55a_similar_sectors/telecom_operators_cashflow_dividend_v55a/formal_validation_summary.json
```

Key evidence:

| Check | Result |
| --- | ---: |
| Core A-share operators | 3 |
| PIT panel rows | 52 |
| Rebalance dates | 20 |
| Equal-weight core telecom return | 25.24% |
| High-dividend top2 return | 26.07% |
| Cash-flow dividend composite top2 return | 48.93% |
| Rolling 2023 | 8.00% |
| Rolling 2024 | 30.86% |
| Rolling 2025 | -1.86% |
| Rolling 2026 | -17.73% |
| Dividend yield mean IC | 0.3513 |
| Dividend yield mean RankIC | 0.3333 |
| OCF yield mean IC | -0.2542 |
| Low PB mean IC | -0.2165 |
| Capex burden mean IC | -0.1562 |
| Composite mean selected count | 1.5 |

## Interpretation

Telecom has a plausible business fit for the dividend low-volatility cash-flow basket, but it is not a normal sector model. The sample is too small, the selected count is too concentrated, and the 2026 rolling result is weak.

The most defensible signal is dividend yield. The operating cash-flow yield, low PB and capex burden factors do not yet provide stable standalone evidence in this three-name universe.

## Governance Outcome

Current status:

```text
research_signal_only
small_sample_observation_sleeve
basket_diagnostic_only
not_engineering_handoff
```

Blocked statuses:

```text
formal_strategy_candidate
platform_replication
paper_trading_ready
accepted_strategy
```

Allowed next gate:

```text
basket_level_contribution_test_or_paper_observation_only
```

Required before any Engineering handoff:

```text
real daily open / close prices
cash dividend events
specialist operating data
leave-one-name-out concentration diagnostic
PM approval for specialist sleeve handling
```

## PM Note

This decision keeps the useful telecom signal alive without overstating the evidence. Telecom may help the enhanced dividend low-volatility cash-flow ETF as a capped sleeve, but it should not be marketed or tested as a standalone robust strategy.

