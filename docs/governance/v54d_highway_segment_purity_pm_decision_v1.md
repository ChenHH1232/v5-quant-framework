# V5.4d Highway Segment Purity PM Decision V1

Date: 2026-07-18

Status:

```text
research_pit_validation_promising_not_engineering_handoff
```

Strategy ID:

```text
highway_dividend_segment_purity_v54d
```

## What Was Added

V5.4d repaired one real operating-data gap:

```text
non-highway business contamination / highway business purity
```

Sources:

- Eastmoney F10 BusinessAnalysis/PageAjax;
- Tushare disclosure_date for report visible dates.

Generated data:

| Dataset | Result |
| --- | ---: |
| Eastmoney raw segment rows | 3860 |
| Segment evidence rows | 379 |
| PIT usable segment rows | 179 |
| Covered companies | 20 |
| Segment-enriched panel rows | 344 |
| Formal highway-only panel rows | 234 |

Still not repaired:

- traffic volume;
- toll revenue trend;
- remaining concession years;
- toll policy / tariff changes.

Those fields remain blocked until annual/interim report evidence is extracted and reviewed.

## Quant Result

PIT leakage audit:

```text
pass
```

Baseline tests:

| Case | Cumulative Return | Positive Ratio |
| --- | ---: | ---: |
| equal_weight_highway_segment_formal | 52.75% | 72.22% |
| high_dividend_segment_formal_top8 | 92.36% | 72.22% |
| highway_revenue_ratio_top8 | 77.36% | 66.67% |
| low_non_highway_ratio_top8 | 77.36% | 66.67% |
| segment_purity_composite_current | 99.57% | 77.78% |

Single-factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio |
| --- | ---: | ---: | ---: |
| dividend_yield | 0.2577 | 0.2859 | 77.78% |
| highway_revenue_ratio | 0.0537 | 0.0325 | 50.00% |
| non_highway_revenue_ratio | 0.0537 | 0.0325 | 50.00% |
| capex_burden | -0.0087 | -0.0390 | 44.44% |

Rolling result:

| Year | Return | Read |
| --- | ---: | --- |
| 2024 | 45.73% | strong |
| 2025 | -0.18% | near flat |
| 2026 | -3.29% | still negative but materially improved |

## PM Decision

V5.4d is upgraded to:

```text
research_pit_validation_promising
```

But it is not yet a formal strategy candidate.

Reason:

- segment purity evidence is useful and improves the high-dividend line;
- however, Eastmoney segment evidence still needs annual-report spot checks;
- direct highway operating fields are not yet repaired;
- the validation window remains short because JQData HY03160 begins in 2021-12;
- ablation rows are affected by the known min_factor_count limitation.

## Next Gate

Before Engineering Agent can run local daily simulation:

1. Spot-check Eastmoney segment rows against original annual/interim reports.
2. Fill at least a reviewed sample of:
   - traffic_volume_yoy;
   - toll_revenue_yoy or toll_revenue_amount;
   - remaining_concession_years;
   - toll_policy_change_flag.
3. Rerun V5.4d / V5.4e formal validation.

No JoinQuant strategy code yet.
