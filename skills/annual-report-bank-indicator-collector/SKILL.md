---
name: annual-report-bank-indicator-collector
description: Collect bank-specialized indicators from Eastmoney annual report PDFs for Bank Quant V5. Use when JoinQuant bank_indicator is unavailable, when standard APIs cannot provide regulatory banking metrics, or when extracting NPL ratio, provision coverage, capital adequacy, liquidity, customer concentration, deposit-loan, net interest margin, and other annual-report-only banking fields with traceable snippets and review status.
---

# V5 Annual Report Bank Indicator Collector

## Role

Collect bank-specialized indicators from annual report PDFs.

## Mission

Create a traceable fallback path for banking indicators that are unavailable from standard APIs.

## Workflow

1. Route the request through `data-source-router`.
2. Define bank universe, report years, and target fields.
3. Download annual report PDFs from an approved disclosure source such as Eastmoney.
4. Save a manifest with stock code, report year, notice date, title, PDF URL, status, and local path.
5. Extract text or OCR text from PDFs.
6. Build candidate snippets around target aliases.
7. Use AI-assisted extraction only with raw snippet references and review status.
8. Save extracted values in a long table.
9. Save missing logs separately from extracted values.
10. Require human review for low-confidence or ambiguous fields.

## Target Output Schema

Use a long table with:

- `code`
- `bank_name`
- `source_type`
- `source_file`
- `field_name_english`
- `field_name_chinese`
- `report_year`
- `value`
- `unit_or_percent`
- `value_scope`
- `source_page`
- `raw_snippet_reference`
- `extraction_method`
- `review_status`
- `report_date`
- `notice_date`
- `mapping_target`
- `confidence`

## Priority Fields

- `capital_adequacy_ratio`
- `tier_1_capital_adequacy_ratio`
- `core_tier_1_capital_adequacy_ratio`
- `non_performing_loan_ratio`
- `provision_coverage_ratio`
- `provision_to_loan_ratio`
- `liquidity_ratio`
- `liquidity_matching_ratio`
- `single_largest_customer_loan_ratio`
- `top_ten_customer_loan_ratio`

## Guardrails

- Do not write empty numeric rows for missing values.
- Do not accept an AI extraction without source snippet or review status.
- Distinguish group scope, parent-bank scope, and unknown scope.
- Keep annual report disclosure date as the point-in-time availability date.
- Do not mix annual-report extracted values with API values without source labels.

## Output

```text
Collection Scope:
Report Source:
Target Fields:
Manifest:
Extracted Values:
Missing Log:
Review Status:
Known Limitations:
Next Skill:
```

## V4 References

- `D:\hh\codex\v4\phase_1_fundamental\download_eastmoney_annual_reports.py`
- `D:\hh\codex\v4\phase_1_fundamental\eastmoney_bank_indicator_schema_v1.md`
- `D:\hh\codex\v4\phase_1_fundamental\extract_eastmoney_bank_indicator_values.py`
- `D:\hh\codex\v4\phase_1_fundamental\prepare_bank_indicator_deepseek_targeted_tasks.py`
