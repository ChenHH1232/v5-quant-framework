---
name: financial-statement-standardizer
description: Standardize Bank Quant V5 raw financial statement data into point-in-time model-ready panels. Use for mapping balance, income, cash-flow, indicator, finance statement tables, period basis, quarterly conversion, consolidated versus parent scope, source priority, missingness audit, and traceable standardized outputs.
---

# V5 Financial Statement Standardizer

## Role

Turn raw statement tables into traceable model-ready financial panels.

## Mission

Separate raw source retention from standardized research fields.

## Core Rules

- Never overwrite raw source files.
- Preserve source-specific columns in a raw layer.
- Store standardized fields in a separate cleaned layer.
- Every standardized value must preserve source table, source field, report period, disclosure date, period basis, statement scope, transformation rule, and missing reason.

## Source Priority

- Income statement: prefer dedicated financial-company income statement when available, then ordinary `income`.
- Cash-flow statement: prefer dedicated financial-company cash-flow statement when available, then ordinary `cash_flow`.
- Balance sheet: prefer ordinary consolidated `balance`; keep finance parent balance as a separate parent-scope source.
- Financial indicators: use ordinary `indicator` as the quarterly backbone.
- Bank-specialized annual indicators must be handled by `bank-indicator-replacement-collector` or `annual-report-bank-indicator-collector`.

## Period Handling

- Treat Q1 as first-quarter value.
- Treat many Q2, Q3, Q4 income and cash-flow fields as year-to-date until proven otherwise.
- Convert cumulative fields by differencing: Q2 minus Q1, Q3 minus Q2, Q4 minus Q3.
- Keep point-in-time balance-sheet fields as period-end snapshots.

## Output

```text
Raw Inputs:
Standardized Tables:
Source Priority:
Period Basis Rules:
Statement Scope Rules:
Missingness Audit:
Transformation Notes:
```

## V4 References

- `D:\hh\codex\v4\phase_1_fundamental\statement_standardization_rules.md`
- `D:\hh\codex\v4\phase_1_fundamental\standardized_outputs`
