# Governance Record: bank_high_dividend_sustainability_v3_research_validation_v1

Date: 2026-07-15

Experiment layer:

`research_pit_validation`

Status:

`continue_research_not_formal_acceptance`

## Decision

V3 has enough evidence to continue research.

V3 is not accepted as a formal strategy.

## Evidence Summary

- Notice-date leakage audit passed mechanically:
  - `missing_notice_date_rows = 0`
  - `future_notice_violations = 0`
- Rolling validation is positive in most years, but weak in 2018 and 2021.
- Dividend yield is the dominant contributor.
- Removing dividend yield causes major deterioration.
- ROE, low PB, and provision coverage are useful support fields but not decisive standalone evidence.
- Core tier 1 capital adequacy is weak as alpha and should be treated mainly as risk / quality control.
- Common-sample all-support composite modestly beats high dividend alone.

## Blocking Condition

Formal acceptance is blocked by V4 legacy quality source-date uncertainty.

The quality bridge uses first visible V4 rebalance date / source-year assumptions. It still needs direct announcement-date verification or replacement with stronger PIT quality data.

## Rules

- Do not tune on 2021-2026 platform replication results.
- Do not use platform replication as research evidence.
- Do not promote V3 until source-date audit is complete.
- Keep defensive and macro variables as risk-control candidates only.

## Next Gate

Research Agent:

- audit source dates for V4 legacy quality fields;
- build a field-level source confidence table.

Quant Validation Agent:

- rerun formal validation after source-date audit;
- add explicit IC / RankIC report to the formal packet;
- review 2018 and 2021 failure modes.

