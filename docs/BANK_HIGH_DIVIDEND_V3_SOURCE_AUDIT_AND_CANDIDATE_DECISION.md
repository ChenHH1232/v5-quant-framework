# Bank High Dividend Sustainability V3 - Source Audit and Candidate Decision

Date: 2026-07-15

## 1. Purpose

This document completes the follow-up actions after the fifth research validation test:

1. audit V4 legacy bank-quality source-date plausibility;
2. add IC / RankIC to the formal validation packet;
3. analyze weak years 2018 and 2021;
4. decide whether V3 can enter a formal candidate stage.

Experiment layer:

`research_pit_validation`

## 2. V4 Legacy Quality Source-Date Audit

Runner:

```text
python -m v5.cli audit-v4-quality-source-dates 数据库\processed\v4_legacy_bank_quality.csv --out validation_formal --strategy-id bank_high_dividend_sustainability_v3
```

Generated local outputs:

```text
validation_formal/bank_high_dividend_sustainability_v3/v4_quality_source_date_audit.csv
validation_formal/bank_high_dividend_sustainability_v3/v4_quality_source_date_audit_summary.json
validation_formal/bank_high_dividend_sustainability_v3/v4_quality_source_date_audit_report.md
```

Audit result:

| Item | Result |
| --- | ---: |
| rows | 310 |
| bank codes | 41 |
| source years | 11 |
| plausible bridge dates | 309 |
| needs source review | 1 |
| high severity rows | 0 |
| medium severity rows | 310 |
| mean lag after fiscal year end | 125.31 days |

One row needs review:

| Code | Source Year | Notice Date | Reason |
| --- | ---: | --- | --- |
| 000001.XSHE | 2019 | 2020-11-02 | later than expected annual-report visibility window |

Interpretation:

- The V4 bridge dates are mostly plausible for annual-report visibility.
- This improves confidence in the long-sample quality panel.
- However, the audit still does not verify original exchange announcements or exact JoinQuant PIT availability.
- Therefore the data can support continued research, but not final strategy acceptance.

## 3. Formal IC / RankIC Added

Formal validation now writes:

```text
validation_formal/bank_high_dividend_sustainability_v3/factor_ic_rankic.csv
```

Results:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio | Top-Bottom Mean Return |
| --- | ---: | ---: | ---: | ---: |
| dividend_yield | 0.1731 | 0.1735 | 77.55% | 2.55% |
| low_price_to_book | 0.1109 | 0.1168 | 61.22% | 1.82% |
| provision_coverage_ratio | 0.0924 | 0.0459 | 63.83% | 0.41% |
| return_on_equity_ttm | 0.0567 | 0.0412 | 57.14% | 1.01% |
| core_tier_1_capital_adequacy_ratio | -0.0003 | 0.0225 | 44.68% | 0.19% |

Interpretation:

- Dividend yield remains the strongest and most stable factor.
- Low PB is the second strongest signal.
- Provision coverage is directionally positive but weaker in return spread.
- ROE is mild support.
- Core tier 1 capital is not alpha evidence; it should remain a risk / quality-control variable.

## 4. Weak-Year Failure Mode Analysis

Formal validation now writes:

```text
validation_formal/bank_high_dividend_sustainability_v3/failure_mode_analysis.csv
```

### 2018

| Metric | Result |
| --- | ---: |
| selected cumulative return | -3.22% |
| selected mean return | -0.35% |
| selected positive ratio | 40.00% |
| relative to all-bank mean | +1.80 pct points |
| relative to low-PB mean | +1.56 pct points |

Interpretation:

2018 was a weak absolute-return year, but V3 still outperformed the all-bank and low-PB comparators on mean return. The issue is more a weak sector/regime environment than pure selection failure.

### 2021

| Metric | Result |
| --- | ---: |
| selected cumulative return | 0.97% |
| selected mean return | 0.37% |
| selected positive ratio | 25.00% |
| relative to all-bank mean | +1.57 pct points |
| relative to low-PB mean | +1.41 pct points |

Interpretation:

2021 also had weak positive-period stability, but V3 outperformed all-bank and low-PB comparators on mean return. This suggests the model did not fully fail versus alternatives, but the holding path was not smooth.

## 5. Candidate Decision

Decision:

```text
status = conditional_research_candidate
not_status = formal_strategy_candidate
not_status = accepted_strategy
```

V3 can move from “continue research” to **conditional research candidate** because:

- mechanical notice-date leakage audit passes;
- V4 quality bridge dates are mostly plausible;
- dividend yield has strong IC / RankIC evidence;
- ablation confirms dividend yield is essential;
- robustness is not destroyed by selection-count or weight perturbation;
- weak years are not clear relative failures versus all-bank and low-PB comparators.

V3 cannot yet become a formal strategy candidate because:

- V4 legacy quality source dates are plausible but not independently verified from original announcements;
- one source-date row needs review;
- quality factors add modest incremental evidence, not decisive evidence;
- cumulative returns are very large and may reflect sample/regime effects;
- exact local-vs-JoinQuant replication remains imperfect.

## 6. Required Gate Before Formal Candidate

Before V3 can become a formal strategy candidate:

1. review the `000001.XSHE` 2019 source-date anomaly;
2. verify original announcement dates for a representative sample of V4 legacy quality fields;
3. rerun formal validation after any corrected quality dates;
4. add a final PM candidate comparison against:
   - high dividend only;
   - low PB;
   - equal-bank;
   - V3 full sustainability composite.

## 7. PM Instruction

Project Manager Agent should label V3 as:

```text
conditional_research_candidate
```

It should not be handed to Engineering Agent as a new accepted strategy. Engineering work may continue only for infrastructure and replication support.

