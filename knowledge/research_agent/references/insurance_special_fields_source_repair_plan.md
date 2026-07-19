# Insurance Special Fields Source Repair Plan

Date: 2026-07-17

Status:

```text
data_repair_required_before_v53d
```

## Purpose

Insurance V5.3c showed a low-PB signal, but the next model cannot proceed until insurance-specific fields are source-repaired.

## Priority Fields

| Priority | Field group | Fields | Why |
| ---: | --- | --- | --- |
| 1 | Embedded value | embedded value, P/EV, embedded-value growth | Core life-insurance valuation anchor |
| 2 | New business value | NBV, NBV growth, NBV margin | Measures future franchise quality |
| 3 | Solvency | core solvency ratio, comprehensive solvency ratio | Dividend safety and balance-sheet quality |
| 4 | Investment quality | net investment yield, total investment yield | Explains rate / equity sensitivity |
| 5 | Liability pressure | surrender rate, reserve pressure | Helps identify low-PB value traps |
| 6 | P&C underwriting | combined ratio, claim ratio, expense ratio | Required for P&C insurers only |

## Source Priority

1. Company annual reports and interim reports.
2. Quarterly / annual solvency reports.
3. Exchange and company disclosure pages.
4. JQData / DataJQ if recent-year table access can be repaired.
5. Tushare announcement links for source discovery.
6. Research reports only as hypothesis and cross-check material.
7. Paid research databases only if they expose publication date and source metadata.

## Manual Import Template

Use:

```text
knowledge/research_agent/references/insurance_special_fields_manual_template.csv
```

Every row must include:

- `report_period`
- `field`
- `value`
- `source_type`
- `source_title`
- `source_url`
- `publish_date`
- `visible_date`
- `pit_status`
- `missing_reason`
- `original_announcement_checked`
- `review_status`

## PIT Rule

Use:

```text
conservative_visible_date = max(report_publish_date, source_visible_date)
```

If the publication date is missing, the field must remain:

```text
not_pit_usable
```

If a database has backfilled old values but the original announcement date has not been checked, the field must remain:

```text
needs_original_announcement_check
```

Missing or delayed disclosure should be recorded as information, not silently filled:

```text
delayed_disclosure
not_disclosed
source_missing
business_change
poor_disclosure_quality
database_backfilled_without_original_date
manual_review_pending
```

## PM Rule

V5.3d cannot start formal validation until the source repair packet reports:

```text
insurance_special_fields_source_repair_passed
```
