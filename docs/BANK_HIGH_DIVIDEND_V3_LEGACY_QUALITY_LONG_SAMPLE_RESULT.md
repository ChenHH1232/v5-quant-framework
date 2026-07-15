# Bank High Dividend V3 Legacy Quality Long-Sample Result

Date: 2026-07-15

## Purpose

Extend the third V3 test beyond the short Eastmoney 2024-2025 annual-report extraction by migrating historical V4 `bank_indicator` quality fields into the V5 quality format.

Experiment layer:

`research_pit_validation`

Important governance note:

This is a long-sample exploratory bridge. It uses V4 historical JoinQuant bank-indicator fields and treats the first V4 rebalance date where a source year appears as the conservative visibility date. It is not final acceptance evidence until original announcement dates or JoinQuant PIT behavior are independently reviewed.

## New Runner

Runner:

- `src/v5/v4_legacy_bank_quality_runner.py`

CLI:

```powershell
$env:PYTHONPATH='src'
python -m v5.cli collect-v4-legacy-bank-quality `
  --source-panel D:\hh\codex\v4\phase_1_fundamental\phase1_training_panel.csv `
  --out-dir 数据库\processed
```

Generated local files:

- `数据库/processed/v4_legacy_bank_quality.csv`
- `数据库/processed/v4_legacy_bank_quality_manifest.json`

These generated files are local data and should not be committed.

## Source Coverage

V4 source:

- `D:\hh\codex\v4\phase_1_fundamental\phase1_training_panel.csv`

Historical quality coverage:

| Item | Count |
| --- | ---: |
| migrated rows | 310 |
| bank codes | 41 |
| source years | 2013-2023 |

Source-year row counts:

| Source Year | Rows |
| --- | ---: |
| 2013 | 14 |
| 2014 | 15 |
| 2015 | 15 |
| 2016 | 23 |
| 2017 | 24 |
| 2018 | 26 |
| 2019 | 35 |
| 2020 | 36 |
| 2021 | 40 |
| 2022 | 41 |
| 2023 | 41 |

## PIT Panel Coverage

Generated panel:

- `数据库/processed/joinquant_basic_pit_panel_v4_legacy_quality/panel.csv`

Coverage:

| Item | Count |
| --- | ---: |
| total panel rows | 1547 |
| rows with bank quality notice date | 1365 |
| rows with provision coverage | 1365 |
| rows with core tier 1 capital adequacy | 1365 |

This is much wider than the Eastmoney 2024-2025 quality panel:

| Source | Quality Rows | Common-Sample Dates |
| --- | ---: | ---: |
| Eastmoney annual-report extraction | 139 | 4 |
| V4 legacy bank-indicator bridge | 1365 | 47 |

## Factor Evidence

Using the V4 legacy quality PIT panel:

| Factor | Observations | Dates | Mean IC | Mean RankIC | Positive IC Ratio | Top-Bottom Mean Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dividend_yield | 1539 | 49 | 0.1731 | 0.1735 | 77.55% | 2.55% |
| low_price_to_book | 1517 | 49 | 0.1109 | 0.1168 | 61.22% | 1.82% |
| return_on_equity_ttm | 1517 | 49 | 0.0567 | 0.0412 | 57.14% | 1.01% |
| provision_coverage_ratio | 1365 | 47 | 0.0924 | 0.0459 | 63.83% | 0.41% |
| core_tier_1_capital_adequacy_ratio | 1365 | 47 | -0.0003 | 0.0225 | 44.68% | 0.19% |

Interpretation:

- Dividend yield remains the strongest and most stable signal.
- Provision coverage has positive IC, but its return spread is much smaller than dividend yield and PB.
- Core tier 1 capital adequacy is not a useful standalone return predictor in this long-sample bridge.

## Common-Sample Interaction Test

Common sample:

| Item | Count |
| --- | ---: |
| rows | 1365 |
| dates | 47 |
| securities | 41 |

Results:

| Case | Cumulative Return | Mean Return | Positive Ratio |
| --- | ---: | ---: | ---: |
| high dividend only | 337.23% | 3.71% | 59.57% |
| high dividend + ROE | 313.76% | 3.62% | 65.96% |
| high dividend + low PB | 323.73% | 3.63% | 63.83% |
| high dividend + provision | 319.21% | 3.64% | 61.70% |
| high dividend + capital | 309.47% | 3.57% | 57.45% |
| high dividend + provision + capital | 313.44% | 3.61% | 59.57% |
| high dividend + all support fields | 361.01% | 3.84% | 61.70% |

Interpretation:

- On the long common sample, raw high dividend is already very strong.
- Adding provision or capital alone does not beat high dividend alone.
- The full support composite beats high dividend alone in cumulative and mean return, but the improvement is modest and depends on the legacy source-date assumption.
- Capital should be treated more as a risk/control variable than as an alpha factor unless further evidence appears.

## Project Manager Decision

Decision:

`continue_research_with_source_date_review_before_engineering_candidate`

Reason:

The long-sample bridge is promising because it turns the quality test from 4 dates into 47 dates. However, it relies on V4's historical bank-indicator source-year visibility rather than directly reviewed announcement dates. V3 should not be handed to Engineering Agent for a new JoinQuant candidate until the visibility assumption is audited.

## Next Step

1. Audit V4 legacy quality visibility:
   - compare `source_year`;
   - first visible `rebalance_date`;
   - expected annual-report announcement window;
   - known report dates where available.
2. Add a source-date audit report for `v4_legacy_bank_quality.csv`.
3. If the audit passes, rerun formal validation and mark the long-sample result as stronger research evidence.
4. If the audit fails, use this only as exploratory evidence and prioritize annual-report extraction for 2013-2023.
