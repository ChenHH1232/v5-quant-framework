# V5.3b Insurance Low-PB Dividend Result

Date: 2026-07-17

Project:

```text
V5.3b Insurance Low-PB + Dividend With Real Rate State
```

Strategy:

```text
insurance_low_pb_dividend_v53b
```

PM status:

```text
research_pit_validation_completed_not_promoted
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## Requested Changes

Completed:

- removed profit growth from scoring;
- did not treat ROE as a positive quality factor;
- changed main signal to low PB + dividend yield;
- replaced bond ETF rate proxy with real ChinaBond 10Y government yield;
- retested failure years 2021, 2022 and 2026.

## Data Outputs

Real 10Y yield:

```text
database / processed / insurance_external_state / china_gov_bond_10y_yield_daily.csv
```

State panel:

```text
database / processed / insurance_external_state_v53b / insurance_real_rate_equity_state.csv
```

PIT panel:

```text
database / processed / insurance_pit_panel_v53b / panel.csv
```

Validation output:

```text
validation_formal_v53b_insurance_low_pb_dividend / insurance_low_pb_dividend_v53b
```

## Real 10Y Rate State

Source:

```text
ChinaBond 10Y government yield via akshare.bond_china_yield
```

Coverage:

| Item | Value |
| --- | ---: |
| Daily 10Y yield rows | 3100 |
| Start | 2014-01-02 |
| End | 2026-05-29 |
| V5.3b rebalance state rows | 44 |

Visibility rule:

```text
Use latest ChinaBond yield row with visible_date <= rebalance date.
```

## Formal Validation

| Item | Value |
| --- | ---: |
| Rows | 206 |
| Rebalance dates | 44 |
| Securities | 5 |
| Leakage audit | pass |

Factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC ratio |
| --- | ---: | ---: | ---: |
| Low PB | 0.2004 | 0.2023 | 70.45% |
| Dividend yield | 0.1606 | 0.1614 | 61.36% |

## Baseline Comparison

| Case | Cumulative return | Positive ratio |
| --- | ---: | ---: |
| Equal-weight core insurance | 79.01% | 50.00% |
| Low PB top 3 | 137.12% | 47.73% |
| High dividend top 3 | 86.56% | 52.27% |
| Low PB + dividend V5.3b | 114.17% | 50.00% |

PM read:

```text
V5.3b improves the conceptual cleanliness of Test-1, but it still does not beat the simple low-PB baseline.
```

## Rolling Validation

| Year | V5.3b return | Positive ratio |
| --- | ---: | ---: |
| 2017 | 63.54% | 100.00% |
| 2018 | -28.40% | 25.00% |
| 2019 | 58.23% | 75.00% |
| 2020 | 8.63% | 75.00% |
| 2021 | -26.01% | 0.00% |
| 2022 | -2.75% | 25.00% |
| 2023 | -0.64% | 50.00% |
| 2024 | 52.65% | 75.00% |
| 2025 | 42.97% | 50.00% |
| 2026 | -28.43% | 0.00% |

Failure-year read:

- 2021 remains a broad insurance weakness year; V5.3b slightly outperforms equal weight but underperforms low PB.
- 2022 improves versus Test-1, but still does not beat equal weight or low PB.
- 2026 remains severe and underperforms equal weight.

## Ablation

| Case | Cumulative return |
| --- | ---: |
| V5.3b composite | 114.17% |
| Drop low PB | 86.56% |
| Drop dividend yield | 137.12% |

PM read:

```text
Low PB is the dominant signal. Dividend yield is positive as a standalone factor, but adding it weakens the low-PB baseline in this 5-stock universe.
```

## Robustness

| Selection count | Cumulative return |
| ---: | ---: |
| 2 | 190.24% |
| 3 | 114.17% |
| 4 | 67.62% |
| 5 | 67.16% |

PM read:

```text
Performance concentration in the top 2 names is a useful clue but also an overfit warning.
```

## Real Rate State Review

State validation output:

```text
validation_formal_v53b_insurance_low_pb_dividend / insurance_low_pb_dividend_v53b / real_rate_state_validation
```

Main findings:

- Falling 10Y yield states have high insurance returns, but V5.3b still does not beat low PB.
- High 10Y yield states are positive but also do not beat low PB.
- Mid-rate states are weak.
- Equity weak/falling states are strong, but again V5.3b does not materially beat low PB.

PM read:

```text
Real 10Y rate state helps interpret insurance regimes, but it does not rescue the current low-PB + dividend composite.
```

## PM Decision

Do not promote V5.3b to formal strategy candidate.

Current classification:

```text
research_revision_completed_current_composite_rejected
```

What passed:

- workflow;
- real 10Y rate-state ingestion;
- low PB evidence;
- dividend standalone evidence.

What failed:

- low PB + dividend composite did not beat low PB alone;
- 2021, 2022 and 2026 remain problematic;
- no repaired EV / NBV / solvency quality layer yet;
- 5-stock universe makes selection-count sensitivity high.

## Recommended Next Step

Start only one of these:

1. `V5.3c Insurance Low-PB State Review`
   - treat low PB as the main candidate;
   - use real 10Y and equity state only for risk interpretation;
   - test whether low PB alone is stable enough.

2. `V5.3 Quality Data Repair`
   - repair insurance_indicator 2024-2025;
   - extract EV / NBV from reports;
   - then test whether quality improves low PB instead of diluting it.

PM recommendation:

```text
Do not write strategy code yet. Run V5.3c low-PB-only formal review first.
```

