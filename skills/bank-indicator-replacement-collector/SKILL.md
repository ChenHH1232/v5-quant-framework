---
name: bank-indicator-replacement-collector
description: Replace unavailable JoinQuant bank_indicator fields in Bank Quant V5 using standard statements, ordinary indicators, reconstructed ratios, annual report extraction, and explicit source labels. Use when collecting or reconstructing bank-specific indicators such as NPL ratio, provision coverage, capital adequacy, core tier 1 capital adequacy, deposit-loan ratio, net interest margin, non-interest income ratio, cost-income ratio, and related banking metrics.
---

# V5 Bank Indicator Replacement Collector

## Role

Design safe replacements for unavailable bank-specialized indicator data.

## Mission

Keep bank-factor research alive after direct JoinQuant `bank_indicator` access is unavailable, without pretending reconstructed fields are identical to the old source.

## Current Critical Constraint

As of 2026-07-14, do not rely on direct JoinQuant `bank_indicator` access for new V5 collection work.

## Replacement Classes

- Direct replacement: field exists in ordinary financial indicator APIs with the same or very close meaning.
- Reconstructed replacement: field can be rebuilt from balance, income, cash-flow, or ordinary indicator data.
- Annual-report extraction: field must be extracted from annual reports because normal APIs do not provide a reliable equivalent.
- Unavailable: field has no reliable current source and must be excluded or manually researched.

## Priority Fields

- `total_loan`
- `total_deposit`
- `net_interest_margin`
- `non_interest_income`
- `non_interest_income_ratio`
- `net_profit_margin`
- `deposit_loan_ratio`
- `cost_to_income_ratio`
- `capital_adequacy_ratio`
- `core_tier_1_capital_adequacy_ratio`
- `non_performing_loan_ratio`
- `provision_coverage_ratio`

## Source Labels

Every collected or reconstructed field must include:

- `source_type`
- `source_table`
- `source_field`
- `mapping_method`
- `confidence`
- `review_status`
- `is_original_bank_indicator`

## Guardrails

- Do not forward-fill missing bank indicators blindly.
- Do not merge original `bank_indicator` and reconstructed fields without a source label.
- Do not treat regulatory capital, non-performing loan, provision coverage, liquidity, or customer concentration fields as solved unless the source is explicit.
- Do not use reconstructed fields in formal validation until their definitions are documented.

## Output

```text
Requested Field:
Replacement Class:
Proposed Source:
Formula or Extraction Rule:
Point-in-Time Date:
Confidence:
Known Difference From Old bank_indicator:
Review Status:
Next Skill:
```

## V4 References

- `D:\hh\codex\v4\phase_1_fundamental\bank_indicator_replacement_map.md`
- `D:\hh\codex\v4\phase_1_fundamental\bank_indicator_2013_backfill_plan.md`
- `D:\hh\codex\v4\phase_1_fundamental\apply_joinquant_2013_bank_indicator_backfill.py`
