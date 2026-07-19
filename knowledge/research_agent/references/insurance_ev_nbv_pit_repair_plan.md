# Insurance EV / NBV PIT Repair Plan

Date: 2026-07-17

Project:

```text
V5.3e Insurance Data Repair Before P/EV Hypothesis
```

Status:

```text
research_data_repair_required
```

## Why This Is Required

V5.3d kept EV / NBV as enhancement fields because historical PIT coverage was not complete enough for rolling validation.

Insurance-specific valuation needs EV / NBV because PB can miss:

- embedded policy value;
- future new-business franchise;
- liability duration;
- channel quality;
- life-insurance-specific value creation.

P/EV must not be tested until the data has verified original announcement dates.

## Required Fields

| Field | Required for | PIT date rule |
| --- | --- | --- |
| embedded_value | P/EV valuation | report publication date |
| new_business_value | franchise quality / P/NBV sensitivity | report publication date |
| embedded_value_yoy | franchise trend | visible after current and prior report dates |
| new_business_value_yoy | franchise trend | visible after current and prior report dates |
| market_cap | P/EV denominator pairing | trade date |
| insurance_subgroup | life / P&C / group split | report or company classification visible date |

## Source Priority

1. Company annual reports and interim reports.
2. Solvency reports if the field is disclosed there.
3. Exchange / official announcement pages.
4. Oriental Wealth / F10 only as structured navigation, then verify against original report.
5. DataJQ / JQData vendor fields if publication date and field definition are auditable.
6. Manual import template if no stable API exists.

## Batch Extraction Operating Rule

Annual-report reading should not be done page-by-page inside the Codex conversation except for a small layout sample.

Required workflow:

1. Build a local annual-report manifest with code, company name, report period, publish date, visible date, source title, source URL and local file path.
2. Run a random sample first with `insurance-annual-report-sample`.
3. Research Agent reviews the sample to confirm:
   - where EV / NBV tables appear;
   - whether the report uses group, life-only or life-plus-health scope;
   - whether units are RMB million, RMB 100 million or another unit;
   - whether current-year and comparable-assumption columns differ.
4. Run batch extraction with `insurance-annual-report-extract`.
5. Treat extracted rows as candidates only. Candidate rows must stay `unreviewed` and `needs_original_announcement_check`.
6. Research Agent upgrades only checked rows to `pit_usable`, `original_announcement_checked=true` and `review_status=reviewed`.
7. Quant Agent may not use candidate rows before the source audit passes.

This rule prevents bulk PDF reading from consuming conversation compute and prevents unreviewed parser output from entering PIT validation.

## Required Row-Level Audit Columns

Every repaired row must include:

```text
code
report_period
field_name
field_value
source_name
source_document_title
source_url_or_file
original_announcement_date
conservative_visible_date
original_announcement_checked
field_definition_checked
collector_note
```

Formal use requires:

```text
original_announcement_checked = true
field_definition_checked = true
conservative_visible_date <= rebalance_date
```

## Coverage Gate

Before Quant Agent may test P/EV:

- at least five core insurance codes must have reviewed EV coverage;
- coverage should span enough years for rolling validation;
- each rebalance date must meet the minimum coverage ratio;
- missing EV must not be backfilled from future reports;
- life-only and combined-universe coverage must be reported separately.

## Research Decision After Repair

If coverage passes:

```text
Research Agent may propose P/EV or EV-growth hypotheses.
```

If coverage fails:

```text
EV / NBV remain research metadata only, not formal factors.
```
