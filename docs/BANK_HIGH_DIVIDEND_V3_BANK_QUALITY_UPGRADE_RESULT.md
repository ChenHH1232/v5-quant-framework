# Bank High Dividend V3 Bank Quality Upgrade Result

Date: 2026-07-15

## Purpose

Continue the third test by connecting local Eastmoney annual-report bank quality fields into the JQData point-in-time panel.

Experiment layer:

`research_pit_validation`

## Implementation

Updated runner:

- `src/v5/joinquant_pit_panel_runner.py`

New behavior:

- loads `数据库/processed/eastmoney_bank_quality_manual_csv.csv`;
- matches by normalized bank code;
- uses only snapshots with `notice_date <= trade_date`;
- writes bank quality fields into the PIT panel:
  - `non_performing_loan_ratio`;
  - `provision_coverage_ratio`;
  - `core_tier_1_capital_adequacy_ratio`;
  - `bank_quality_notice_date`;
  - `bank_quality_review_status`.

Formal leakage audit was also tightened:

- if bank quality fields are present, validation checks `bank_quality_notice_date` or `eastmoney_quality_notice_date`;
- `factor_visible_date = trade_date` is no longer allowed to hide a future annual-report quality field.

## Local Panel Coverage

Generated panel:

- `数据库/processed/joinquant_basic_pit_panel/panel.csv`

Coverage after bank-quality merge:

| Item | Count |
| --- | ---: |
| total rows | 1547 |
| rows with bank quality notice date | 139 |
| rows with provision coverage | 104 |
| rows with core tier 1 capital adequacy | 136 |

Interpretation:

The merge works, but coverage is still too narrow for accepting a full "sustainable high dividend" hypothesis. This is usable for exploratory interaction checks, not final research acceptance.

## Research Validation Result

Key factor evidence:

| Factor | Observations | Dates | Mean IC | Mean RankIC | Positive IC Ratio | Top-Bottom Mean Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dividend_yield | 1539 | 49 | 0.1731 | 0.1735 | 77.55% | 2.55% |
| low_price_to_book | 1517 | 49 | 0.1109 | 0.1168 | 61.22% | 1.82% |
| return_on_equity_ttm | 1517 | 49 | 0.0567 | 0.0412 | 57.14% | 1.01% |
| provision_coverage_ratio | 104 | 4 | 0.1040 | 0.1470 | 75.00% | 0.89% |
| core_tier_1_capital_adequacy_ratio | 136 | 4 | 0.0627 | 0.0833 | 75.00% | 0.72% |

Interpretation:

- High dividend yield remains the strongest and best-covered signal.
- PB remains positive.
- ROE is weakly positive.
- Provision and capital are directionally positive, but their sample is far too small.

## Formal Validation Result

Notice-date audit:

```text
status = pass
checked_rows = 1547
missing_notice_date_rows = 0
future_notice_violations = 0
```

Baseline:

| Case | Cumulative Return | Positive Ratio | Mean Selected Count |
| --- | ---: | ---: | ---: |
| equal_weight_all_banks | 35.17 | 61.40% | 27.14 |
| low_pb_top8 | 4.52 | 52.63% | 6.91 |
| composite_current | 59.99 | 64.91% | 6.96 |

Ablation:

| Case | Cumulative Return | Interpretation |
| --- | ---: | --- |
| composite_current | 59.99 | current V3 PIT composite with partial bank quality |
| drop_dividend_yield | 5.40 | dividend yield remains the dominant contributor |
| drop_return_on_equity_ttm | 58.93 | ROE adds little |
| drop_low_price_to_book | 60.00 | low PB adds little in this configuration |
| drop_provision_coverage_ratio | 60.65 | provision does not improve the current sparse-sample composite |
| drop_core_tier_1_capital_adequacy_ratio | 60.22 | capital does not improve the current sparse-sample composite |

Robustness:

- selection count 6: 65.94
- selection count 8: 59.99
- selection count 10: 60.69
- value weight scale 0.8: 60.38
- value weight scale 1.0: 59.99
- value weight scale 1.2: 61.58

## Project Manager Decision

Decision:

`continue_research_with_bank_quality_coverage_upgrade`

Reason:

The third test now has a working PIT data path and a stricter notice-date audit. However, the current bank quality sample is only visible in 4 validation dates, so it cannot yet prove that quality-conditioned high dividend is superior to raw high dividend. It only supports the weaker statement that provision and capital are directionally positive where data exists.

## Next Step

Do not tune weights.

Next work should be:

1. Increase bank quality coverage by reviewing or re-extracting annual/interim reports across more years.
2. Add common-sample interaction tests:
   - high dividend only;
   - high dividend plus ROE;
   - high dividend plus provision;
   - high dividend plus capital;
   - high dividend plus provision plus capital;
   - high dividend trap filter.
3. Separate full-sample result from common-sample result, because sparse quality fields can silently change the investable universe.
4. Only after common-sample validation should Engineering Agent produce a new JoinQuant strategy candidate.
