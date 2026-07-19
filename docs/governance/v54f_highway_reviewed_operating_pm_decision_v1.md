# V5.4f Highway Reviewed Operating Data PM Decision V1

Date: 2026-07-18

Status:

```text
research_pit_validation_completed
engineering_blocked_by_reviewed_operating_coverage
```

Strategy ID:

```text
highway_dividend_reviewed_operating_v54f
```

## What Was Done

V5.4f converted the V5.4e operating-field candidates into reviewed PIT operating-disclosure evidence.

Completed steps:

1. Built `highway_reviewed_operating_disclosure_data.csv` from original annual-report candidate snippets.
2. Required each row to retain visible date, source URL, local PDF path and review status.
3. Promoted a row to PIT usable only when at least 3 of 4 disclosure categories were supported:
   - traffic / toll table available;
   - toll revenue evidence available;
   - remaining concession evidence available;
   - toll policy evidence available.
4. Joined the latest visible reviewed operating evidence back to the formal highway segment panel.
5. Ran formal validation for `Highway Dividend + Reviewed Operating Data V5.4f`.

## Reviewed Operating Coverage

Reviewed annual-report disclosure data:

| Item | Count |
| --- | ---: |
| Reviewed disclosure rows | 7 |
| PIT usable rows | 5 |
| PIT usable companies | 5 |

Joined formal panel:

| Item | Count |
| --- | ---: |
| Segment formal panel rows | 234 |
| Reviewed-operating formal rows | 18 |
| Missing reviewed-operating rows | 216 |
| Covered companies after PIT join | 4 |
| Covered rebalance dates | 5 |

PM interpretation:

```text
Reviewed operating disclosure is technically joined, but coverage is too narrow for Engineering handoff.
```

## Formal Validation Result

Panel:

```text
数据库/processed/highway_operating_data/annual_reports/highway_reviewed_operating_formal_panel.csv
```

PIT leakage audit:

```text
pass
```

Rolling validation:

```text
skipped: insufficient_history
```

Baseline:

| Case | Periods | Cumulative Return | Positive Ratio | Mean Selected Count |
| --- | ---: | ---: | ---: | ---: |
| equal_weight_reviewed_operating_formal | 5 | -6.64% | 40.00% | 3.6 |
| high_dividend_reviewed_operating_top8 | 5 | -6.64% | 40.00% | 3.6 |
| reviewed_operating_segment_purity_composite | 5 | -2.20% | 40.00% | 3.2 |

Factor IC / RankIC:

| Factor | Observations | Dates | Mean IC | Mean RankIC |
| --- | ---: | ---: | ---: | ---: |
| dividend_yield | 18 | 4 | 0.4631 | 0.5500 |
| highway_revenue_ratio | 18 | 4 | -0.0184 | 0.0500 |
| non_highway_revenue_ratio | 18 | 4 | -0.0184 | 0.0500 |
| capex_burden | 18 | 4 | -0.2240 | -0.1500 |
| reviewed_operating_disclosure_score | 18 | 0 | n/a | n/a |

## PM Decision

V5.4f does not pass the Engineering handoff gate.

Reasons:

- reviewed operating coverage starts only after the 2024 annual reports become visible;
- the formal panel has only 18 rows and 5 rebalance dates;
- rolling validation cannot run;
- reviewed operating disclosure score is constant in the usable panel, so it is a data-quality gate, not a validated alpha factor;
- exact traffic volume, toll revenue, concession years and toll policy numeric values remain unpromoted.

Current status:

```text
research_pit_validation_completed
pit_leakage_audit_passed
reviewed_operating_data_joined
engineering_blocked_by_reviewed_operating_coverage
not_engineering_handoff
```

## Next Required Step

Do not tune V5.4f.

Research/data work required before another engineering decision:

1. Expand reviewed operating evidence to multiple report years, ideally 2021-2025.
2. Review exact numeric values with company-level / road-level distinction.
3. Add unit normalization for traffic volume, toll revenue and concession maturity.
4. Fill missing `001965.XSHE` from alternate annual-report sources.
5. Rerun V5.4g only after the reviewed operating panel covers enough dates for rolling validation.

Engineering Agent remains blocked.
