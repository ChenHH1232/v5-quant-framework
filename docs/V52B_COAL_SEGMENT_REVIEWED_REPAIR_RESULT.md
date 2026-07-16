# V5.2b Coal Segment Evidence Repair Result

Date: 2026-07-16

Owner:

```text
Research Agent / Quant Validation Agent / Engineering Agent
```

Status:

```text
business_segment_evidence_repaired_formal_universe_validation_completed_not_acceptance
```

## Purpose

The Eastmoney segment runner covered `33 / 37` coal-universe companies. The missing four companies required a fallback source and Research Agent judgment:

```text
000611.XSHE
000780.XSHE
600532.XSHG
600652.XSHG
```

The repair objective was not to force-fill every company as coal. The objective was to decide whether each company should be included in a point-in-time formal coal universe.

## Runner Additions

New commands:

```text
python -m v5.cli coal-data-audit collect-tushare-segments --codes 000611.XSHE 000780.XSHE 600532.XSHG 600652.XSHG
python -m v5.cli coal-data-audit merge-segment-evidence
python -m v5.cli coal-data-audit build-reviewed-business-tag-panel
```

Outputs:

```text
database/processed/coal_business_tags/coal_segment_business_evidence_tushare.csv
database/processed/coal_business_tags/coal_segment_business_evidence_reviewed.csv
database/processed/coal_business_tags/coal_business_tag_pit_reviewed_panel.csv
database/processed/coal_business_tags/coal_business_tag_pit_formal_universe_panel.csv
```

Source policy:

```text
Eastmoney remains the preferred structured source. Tushare fina_mainbz is used as a licensed fallback for Eastmoney gaps. No credential values are written.
```

## Evidence Result

Reviewed segment evidence:

| Item | Value |
| --- | ---: |
| Evidence rows | 623 |
| PIT usable rows | 623 |
| Covered companies | 37 |
| Segment evidence audit | pass |

Source split:

| Source | Rows |
| --- | ---: |
| Eastmoney F10 + disclosure date | 561 |
| Tushare fina_mainbz + disclosure date | 62 |

## Research Judgment For The Four Missing Companies

| Code | PIT judgment | Formal universe treatment |
| --- | --- | --- |
| `000611.XSHE` | Short coal-trade exposure existed historically, but the 2022 panel dates are non-core / disclosure-risk rows. | Exclude from formal coal universe on 2022 panel dates. |
| `000780.XSHE` | Coal mining / coal selection revenue and profit are consistently dominant before absorption/exit. | Include as core coal during visible PIT periods; later corporate-action exit still requires platform handling. |
| `600532.XSHG` | Coal exposure is trade-oriented and mixed with medical/service exposure; not coal mining/operation. | Exclude from formal coal universe unless Research Agent explicitly approves a special trade-only hypothesis. |
| `600652.XSHG` | Early 2014-2015 reports show coal exposure; later years become game/media/non-core. | Include only during PIT-visible coal period; exclude later non-core periods. |

Research rule:

```text
Coal trade revenue is not equivalent to coal mining or coal operation. Trade-only, shell, ST, delisted, or disclosure-risk rows must not be upgraded to core coal by revenue ratio alone.
```

## PIT Panel Result

Reviewed panel:

| Item | Value |
| --- | ---: |
| Full reviewed rows | 1206 |
| Formal-universe rows | 861 |
| Rows without visible segment evidence at trade date | 256 |
| Rows excluded by formal-universe rule | 89 |
| Covered company count | 37 |

Important interpretation:

```text
Rows before a segment report is visible are intentionally excluded from the formal universe. This is PIT discipline, not a data failure.
```

## Formal Validation Rerun

Formal universe panel:

```text
database/processed/coal_business_tags/coal_business_tag_pit_formal_universe_panel.csv
```

Formal validation:

```text
validation_formal_v52b_segment_formal_universe/coal_cashflow_cycle_value_v52b_capex_policy/
```

Key results:

| Metric | Result |
| --- | ---: |
| Rows | 861 |
| Dates | 44 |
| Leakage audit | pass |
| Composite cumulative return | 3.7066 |
| OCF yield mean IC | 0.1370 |
| OCF yield mean RankIC | 0.1359 |
| FCF yield mean IC | 0.1167 |
| Low PB mean IC | 0.0886 |
| Low PE mean IC | 0.0714 |

Rolling weak year:

```text
2018 remains weak: cumulative return -35.94%, positive ratio 0.0.
```

However, after the formal universe repair, 2018 is now slightly better than the all-universe and low-PB references in that year. This means the failure is more likely a sector-cycle drawdown problem than a pure bad-stock-selection problem.

## PM Decision

V5.2b status changes from:

```text
business_segment_evidence_blocked
```

to:

```text
business_segment_evidence_repaired
research_pit_validation_completed_not_acceptance
engineering_overfit_audit_needs_review
```

It is still not:

```text
accepted_strategy
platform_replication_passed
paper_trading_ready
```

Remaining blockers / reviews:

1. external inventory/output state remains incomplete;
2. overfit audit still needs daily returns and rebalance signals;
3. ST / delisting / absorption corporate-action treatment must be handled before any JoinQuant-style platform replication;
4. 2018 remains a weak-year stress case and should not be ignored.

