# V5.4e Highway Annual-Report Spot-Check PM Decision V1

Date: 2026-07-18

Status:

```text
research_pit_validation_promising_but_engineering_blocked
```

Strategy ID:

```text
highway_dividend_segment_purity_v54e
```

## What Was Done

V5.4e added an annual-report source check above V5.4d.

Steps completed:

1. Built a 2024 annual-report sample from Tushare disclosure dates.
2. Downloaded CNINFO original annual-report PDFs.
3. Spot-checked Eastmoney F10 segment rows against annual-report text.
4. Extracted candidate operating fields:
   - traffic_volume_yoy;
   - toll_revenue_amount;
   - toll_revenue_yoy;
   - remaining_concession_years;
   - toll_policy_change_flag.
5. Reran formal validation using the segment-purity strategy.

## Source Check Result

Annual-report download:

| Item | Count |
| --- | ---: |
| Requested reports | 8 |
| Downloaded reports | 7 |
| Missing from CNINFO query | 1 |

Eastmoney segment spot check:

| Item | Count |
| --- | ---: |
| Reports checked | 7 |
| Segment rows checked | 30 |
| Pass rows | 28 |
| Needs manual review | 2 |
| Passed report count | 7 |

Interpretation:

```text
Eastmoney segment evidence is broadly supported by original annual reports in the sample.
```

But:

```text
Exact value promotion still requires targeted table/page review.
```

## Operating Field Extraction

Candidate rows extracted:

| Field | Candidate Count |
| --- | ---: |
| traffic_volume_yoy | 34 |
| toll_revenue_amount | 28 |
| toll_revenue_yoy | 7 |
| remaining_concession_years | 24 |
| toll_policy_change_flag | 15 |

PM interpretation:

```text
These are candidates, not PIT-usable factors yet.
```

Reason:

- candidate extraction includes some false positives;
- units differ across company reports;
- some values are road-level rather than company-level;
- remaining concession years often appear as text, not a clean numeric company-level value.

## Formal Validation Result

Panel:

```text
数据库/processed/highway_operating_data/highway_segment_formal_panel.csv
```

PIT leakage audit:

```text
pass
```

Baseline:

| Case | Cumulative Return | Positive Ratio |
| --- | ---: | ---: |
| equal_weight_highway_segment_formal | 52.75% | 72.22% |
| high_dividend_segment_formal_top8 | 92.36% | 72.22% |
| segment_purity_composite_current | 99.57% | 77.78% |

Rolling:

| Year | Return |
| --- | ---: |
| 2024 | 45.73% |
| 2025 | -0.18% |
| 2026 | -3.29% |

## PM Decision

V5.4e is promising, but Engineering Agent should not start local daily simulation yet.

Reason:

- segment evidence has only sample-level annual-report spot check, not full-history review;
- traffic volume, toll revenue, concession years and toll policy are extracted as candidates only;
- the strategy is still primarily high-dividend + segment-purity, not a fully highway-operating-data model;
- V5 governance requires reproducible and reviewed data before platform replication.

Current status:

```text
research_pit_validation_promising
engineering_blocked_by_operating_data_review
```

## Next Required Step

Research Agent / data runner must convert candidate operating fields into reviewed rows:

- confirm value;
- confirm unit;
- confirm whether value is road-level or company-level;
- attach report page;
- set `pit_usable=true` only after review.

After that, run:

```text
V5.4f Highway Dividend + Reviewed Operating Data
```

Only if V5.4f passes should Engineering Agent run local daily simulation.
