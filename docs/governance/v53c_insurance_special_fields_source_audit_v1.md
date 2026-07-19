# V5.3c Insurance Special Fields Source Audit V1

Date: 2026-07-17

Status:

```text
insurance_special_fields_source_repair_blocked
```

Not status:

```text
insurance_special_fields_source_repair_passed
v53d_model_ready
platform_replication_approved
accepted_strategy
```

## Purpose

Run the new insurance special-fields audit gate against the manual import template.

This verifies that V5.3d cannot start merely because a template exists. The fields must be filled, reviewed, sourced and PIT-usable.

## Command

```text
python -m v5.cli insurance-special-fields-audit knowledge/research_agent/references/insurance_special_fields_manual_template.csv --out insurance_special_fields_audit
```

## Result

| Item | Value |
| --- | ---: |
| Rows | 8 |
| PIT usable rows | 0 |
| Field count | 8 |
| PIT blocked rows | 8 |
| Blockers | 6 |

Missing required core fields:

```text
comprehensive_solvency_ratio
core_solvency_ratio
embedded_value
net_investment_yield
new_business_value
total_investment_yield
```

## PM Read

The source-repair gate is functioning correctly.

Current template rows are placeholders. They are not PIT usable because values, source titles, source URLs, publish dates, visible dates and reviewed status are not filled.

The upgraded audit also requires:

```text
pit_status
missing_reason
original_announcement_checked
```

The current template rows are correctly marked:

```text
pit_status = needs_original_announcement_check
missing_reason = manual_review_pending
original_announcement_checked = false
```

This means Eastmoney/F10 or vendor backfilled history cannot enter V5.3d until the original announcement date is checked.

## Decision

```text
blocked_for_v53d_until_reviewed_special_fields_are_imported
```

## Next Required Work

Research Agent / Engineering Agent must populate the manual template or another reviewed import file with:

- embedded value;
- new business value;
- core solvency ratio;
- comprehensive solvency ratio;
- net investment yield;
- total investment yield.

Every row must include:

- source document;
- source URL or local source reference;
- publication date;
- conservative visible date;
- PIT status;
- missing reason;
- original announcement checked flag;
- review status = `reviewed`.

Allowed `missing_reason` values include:

```text
delayed_disclosure
not_disclosed
source_missing
business_change
poor_disclosure_quality
database_backfilled_without_original_date
manual_review_pending
```

## Next Gate

```text
insurance_special_fields_source_repair
```
