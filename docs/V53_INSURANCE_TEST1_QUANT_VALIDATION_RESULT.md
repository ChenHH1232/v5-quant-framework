# V5.3 Insurance Test-1 Quant Validation Result

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

Strategy:

```text
insurance_value_quality_v53_test1
```

PM status:

```text
research_pit_validation_completed_current_composite_not_promoted
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## Work Completed

The requested sequence was executed:

1. reviewed the 8 insurance codes;
2. built a Test-1 formal PIT insurance universe;
3. replaced missing 2024-2025 `insurance_indicator` dependency with a safer Test-1 data policy;
4. decided EV / NBV status;
5. built a rate / equity state panel;
6. ran Quant Validation:
   - baseline;
   - IC / RankIC;
   - rolling validation;
   - ablation;
   - robustness;
   - weak-year analysis;
   - rate / equity state review.

## Formal PIT Insurance Universe

Test-1 uses the 5 cleanest core listed insurance companies:

| Code | Company | Subgroup |
| --- | --- | --- |
| `601318.XSHG` | 中国平安 | insurance group |
| `601628.XSHG` | 中国人寿 | life insurance |
| `601601.XSHG` | 中国太保 | insurance group |
| `601336.XSHG` | 新华保险 | life insurance |
| `601319.XSHG` | 中国人保 | P&C insurance group |

Excluded from Test-1:

| Code | Reason |
| --- | --- |
| `000627.XSHE` | holding / ST special case, not clean operating insurer for first formal test |
| `600291.XSHG` | delisted / historical special case |
| `002423.XSHE` | financial holding contamination |

Universe output:

```text
数据库/processed/insurance_formal_universe/
```

## 2024-2025 Insurance Indicator Decision

`insurance_indicator` exists and is useful, but the first DataJQ probe returned:

| Source year | Coverage |
| --- | ---: |
| 2021 | 75.00% |
| 2022 | 75.00% |
| 2023 | 75.00% |
| 2024 | 0.00% |
| 2025 | 0.00% |

PM decision:

```text
Do not use insurance_indicator as a required Test-1 scoring input.
```

Replacement policy:

- keep `insurance_indicator` fields in the panel as diagnostic latest-visible data;
- do not require them for 2024-2025 scoring;
- use generic PIT valuation, dividend, ROE and profit-growth fields for Test-1 only;
- require repair or report extraction before any formal candidate promotion.

## EV / NBV Decision

EV / NBV are downgraded for Test-1:

```text
deferred_enhancement_not_required_for_test1
```

Reason:

- EV / NBV were not found in `insurance_indicator`;
- they likely require annual-report extraction or a reviewed vendor source;
- Test-1 should first test process feasibility and basic value evidence.

Before formal promotion, Research Agent must decide whether:

- EV / NBV become required life-insurance factors; or
- V5.3 remains a simpler listed-insurance valuation strategy without EV / NBV.

## Rate / Equity State Panel

Generated:

```text
数据库/processed/insurance_external_state/insurance_rate_equity_state.csv
```

Current state policy:

| State | Current proxy | Formal-candidate requirement |
| --- | --- | --- |
| Rate state | `511010.XSHG` bond ETF trailing return | replace with PIT 10Y government bond yield |
| Equity state | `000300.XSHG` CSI 300 trailing return | acceptable as broad equity state proxy |

PM note:

```text
The bond ETF proxy is acceptable for Test-1 research validation, but not enough for formal strategy candidacy.
```

## Formal Validation

Panel:

```text
数据库/processed/insurance_pit_panel_v53_test1/panel.csv
```

Output:

```text
validation_formal_v53_insurance_test1/insurance_value_quality_v53_test1/
```

Summary:

| Item | Value |
| --- | ---: |
| Rows | 206 |
| Rebalance dates | 44 |
| Securities | 5 |
| Leakage audit | pass |

## Factor IC / RankIC

| Factor | Mean IC | Mean RankIC | Positive IC ratio | PM read |
| --- | ---: | ---: | ---: | --- |
| Low PB | 0.2004 | 0.2023 | 70.45% | strongest evidence |
| Dividend yield | 0.1606 | 0.1614 | 61.36% | positive support |
| ROE TTM | 0.0594 | 0.0452 | 50.00% | weak |
| Profit growth YoY | -0.0888 | -0.0955 | 38.64% | negative / reject as scoring factor |

## Baseline And Composite

| Case | Cumulative return | Positive ratio |
| --- | ---: | ---: |
| Equal-weight core insurance | 79.01% | 50.00% |
| Low PB top 3 | 137.12% | 47.73% |
| High dividend top 3 | 86.56% | 52.27% |
| High ROE top 3 | 55.90% | 45.45% |
| High profit growth top 3 | 53.93% | 45.45% |
| Composite current | 114.09% | 52.27% |

PM read:

```text
The composite does not beat the simple low-PB baseline.
```

## Rolling Validation

Weak years:

| Year | Composite return | Positive ratio |
| --- | ---: | ---: |
| 2018 | -28.16% | 25.00% |
| 2021 | -27.00% | 0.00% |
| 2022 | -6.66% | 25.00% |
| 2023 | -4.10% | 50.00% |
| 2026 | -27.10% | 0.00% |

Strong years:

| Year | Composite return |
| --- | ---: |
| 2017 | 58.14% |
| 2019 | 64.28% |
| 2024 | 51.65% |
| 2025 | 56.17% |

PM read:

```text
The result is regime-sensitive and cannot be accepted as a stable strategy.
```

## Ablation

| Case | Cumulative return | PM read |
| --- | ---: | --- |
| Composite current | 114.09% | base |
| Drop low PB | 74.43% | low PB matters |
| Drop dividend yield | 75.48% | dividend matters |
| Drop ROE | 127.12% | ROE hurts the current composite |
| Drop profit growth | 105.72% | profit growth weakens the model |

PM read:

```text
Low PB + dividend is the main useful structure. ROE and profit-growth should not be accepted as current scoring factors.
```

## Robustness

Selection-count robustness:

| Selection count | Cumulative return |
| ---: | ---: |
| 2 | 127.15% |
| 3 | 114.09% |
| 4 | 73.67% |
| 5 | 67.16% |

PM read:

```text
Evidence is concentrated in a smaller selection set, which is useful but requires overfit caution in a 5-stock universe.
```

## State Bucket Review

State output:

```text
validation_formal_v53_insurance_test1/insurance_value_quality_v53_test1/state_bucket_validation/
```

Findings:

- In weak / falling equity buckets, the composite return is high but does not beat equal weight.
- In mid equity buckets, returns are low.
- Bond proxy buckets do not show a clean stable rule.
- Rate state currently uses a bond ETF proxy, not real 10Y yield.

PM read:

```text
State review does not support formal promotion yet.
```

## PM Decision

Do not promote V5.3 Test-1.

Current classification:

```text
workflow_continues_current_composite_rejected
```

Recommended next model:

```text
V5.3b Insurance Low-PB + Dividend With Real Rate State
```

Required changes:

- remove profit growth from scoring;
- do not use ROE as a positive scoring factor until insurance-specific quality is repaired;
- test low PB + dividend as the main candidate;
- replace bond ETF proxy with real PIT 10Y government bond yield;
- decide whether EV / NBV can be collected, otherwise explicitly keep them out of Test-1 / Test-2;
- keep 2021, 2022 and 2026 as failure years requiring explanation.

