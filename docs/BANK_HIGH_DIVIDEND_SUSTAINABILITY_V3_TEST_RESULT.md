# Bank High Dividend Sustainability V3 Test Result

Date: 2026-07-15

## Experiment Layer

`research_pit_validation`

## Status

`research_candidate_needs_point_in_time_data_review`

This test produced useful evidence, but it is not an accepted strategy and not ready for JoinQuant platform replication.

## Commands Run

```powershell
$env:PYTHONPATH='src'
python -m v5.cli validate examples\bank_high_dividend_sustainability_v3_strategy.json
python -m v5.cli validate-research examples\bank_high_dividend_sustainability_v3_strategy.json data\processed\bank_value_15y\panel.csv --out validation
python -m v5.cli validate-formal examples\bank_high_dividend_sustainability_v3_strategy.json data\processed\bank_value_15y\panel.csv --out validation_formal --experiment-layer research_pit_validation
```

## Generated Outputs

Ignored local output directories:

- `validation/bank_high_dividend_sustainability_v3/`
- `validation_formal/bank_high_dividend_sustainability_v3/`

Important files:

- `validation_summary.json`
- `factor_validation.csv`
- `formal_validation_summary.json`
- `notice_date_leakage_audit.csv`
- `baseline_tests.csv`
- `ablation_tests.csv`
- `robustness_tests.csv`
- `RUN_MANIFEST.json`

## Spec Audit

The final V3 spec passed the V5 contract audit.

Earlier execution attempts were blocked by missing required fields:

- `portfolio.max_position_weight`
- `risk.defensive_asset`
- `outputs.save_holdings`
- `outputs.save_rebalance_signals`
- factor `disclosure_lag_days`

This is a positive process result: the spec contract prevented incomplete strategy definitions from silently entering validation.

## Factor Evidence

| Factor | Mean IC | Mean RankIC | Positive IC Ratio | Top-Bottom Mean Return |
| --- | ---: | ---: | ---: | ---: |
| dividend_yield | 0.1479 | 0.1506 | 75.51% | 2.74% |
| low_price_to_book | 0.1443 | 0.1345 | 63.27% | 2.36% |
| return_on_equity_ttm | 0.0689 | 0.0587 | 59.57% | 1.26% |
| provision_coverage_ratio | 0.0711 | 0.0318 | 59.09% | 0.13% |
| core_tier_1_capital_adequacy_ratio | 0.0103 | 0.0233 | 50.00% | -0.11% |

Initial interpretation:

- `dividend_yield` has the strongest single-factor evidence in this panel.
- `low_price_to_book` is close behind and remains an important baseline.
- ROE has moderate supporting evidence.
- Provision coverage and core tier 1 capital are weaker as standalone predictors in this panel.
- Capital support may be more useful as a guard or interaction than as a direct alpha factor.

## Formal Validation

Baseline and candidate results:

| Case | Cumulative Return | Positive Ratio | Mean Selected Count |
| --- | ---: | ---: | ---: |
| equal_weight_all_banks | 73.20 | 61.40% | 27.14 |
| low_pb_top8 | 117.84 | 73.68% | 7.02 |
| composite_current | 159.93 | 71.93% | 6.98 |

Ablation:

| Case | Cumulative Return | Interpretation |
| --- | ---: | --- |
| composite_current | 159.93 | current V3 composite |
| drop_dividend_yield | 128.92 | dividend contributes materially |
| drop_return_on_equity_ttm | 139.63 | ROE contributes |
| drop_low_price_to_book | 126.83 | valuation contributes materially |
| drop_provision_coverage_ratio | 137.66 | provision contributes |
| drop_core_tier_1_capital_adequacy_ratio | 145.68 | capital contributes less, but not zero |

Robustness:

- selection count 6: 161.68
- selection count 8: 159.93
- selection count 10: 129.63
- value weight scale 0.8: 131.49
- value weight scale 1.0: 159.93
- value weight scale 1.2: 153.40

Initial interpretation:

- The candidate appears directionally promising.
- Selection count 6 and 8 are similar; count 10 weakens.
- Weight perturbation is not perfectly stable, so parameter sensitivity remains.

## Blocking Limitation

The formal notice-date leakage audit returned:

```text
status: needs_review
checked_rows: 1547
missing_notice_date_rows: 1547
future_notice_violations: 0
```

This means the current panel does not carry enough per-row notice-date metadata to prove point-in-time availability for the fields used in V3.

Therefore:

- V3 cannot be accepted.
- V3 should not be exported to JoinQuant yet.
- V3 should not be used for platform replication yet.

## Decision

Project Manager decision:

`continue_research_with_data_upgrade`

Reason:

The high-dividend hypothesis shows useful statistical signal in the migrated panel, especially relative to low-PB baseline and ablation tests. However, point-in-time metadata is insufficient. The correct next step is not parameter tuning, but data lineage repair.

## Next Steps

1. Use JQData/DataJQ to rebuild the local panel with explicit announcement dates where possible.
2. Attach dividend announcement, ex-dividend, record, and pay dates.
3. Rebuild `dividend_yield` as visible trailing dividend yield.
4. Rebuild ROE and bank quality fields with announcement-date alignment.
5. Rerun V3 as `research_pit_validation`.
6. Only if it survives, create a platform-replication candidate.

