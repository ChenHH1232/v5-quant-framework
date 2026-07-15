# Eastmoney Bank Report Indicator Pipeline

## Type

Data Validation / Indicator Pipeline

## Purpose

This card explains how Quant Validation Agent should use Eastmoney annual-report extraction artifacts migrated from V4 to fill bank-specific indicators that JoinQuant `bank_indicator` no longer reliably provides.

## Evidence Level

Mixed `industry_disclosure`, `V5_internal_rule`, and `data_limited`.

The source is listed-bank annual-report disclosure downloaded from Eastmoney and processed by the V4 extraction pipeline. Automatic extracted values are not accepted evidence until reviewed.

## V4 Source Artifacts

Important V4 files:

- `D:\hh\codex\v4\phase_1_fundamental\download_eastmoney_annual_reports.py`
- `D:\hh\codex\v4\phase_1_fundamental\extract_all_eastmoney_bank_indicator_texts.py`
- `D:\hh\codex\v4\phase_1_fundamental\extract_eastmoney_bank_indicator_values.py`
- `D:\hh\codex\v4\phase_1_fundamental\build_eastmoney_bank_indicator_candidate_queue.py`
- `D:\hh\codex\v4\phase_1_fundamental\eastmoney_bank_indicator_extracted_values.csv`
- `D:\hh\codex\v4\phase_1_fundamental\eastmoney_bank_indicator_candidate_queue.csv`
- `D:\hh\codex\v4\phase_1_fundamental\eastmoney_bank_indicator_candidate_coverage.csv`

## V5 Runner

Use:

```powershell
python -m v5.cli collect-eastmoney-bank-indicators
```

Default source:

```text
D:\hh\codex\v4\phase_1_fundamental\eastmoney_bank_indicator_extracted_values.csv
```

Default outputs:

- `数据库/processed/eastmoney_bank_indicator_long.csv`
- `数据库/processed/eastmoney_bank_quality_manual_csv.csv`
- `数据库/processed/eastmoney_bank_indicator_manifest.json`

## Review Status Rule

Use `review_status` as a hard governance field:

- `reviewed`: allowed for formal Quant Validation if point-in-time rules also pass.
- `needs_check`: allowed for engineering tests and candidate exploration only.
- `unreviewed`: not allowed for factor acceptance.

Default V5 migration includes `needs_check` because it is useful for engineering tests, but formal validation should be rerun with:

```powershell
python -m v5.cli collect-eastmoney-bank-indicators --min-review-status reviewed
```

## Point-In-Time Rule

Use `notice_date` as the visibility date. Do not align annual-report indicators by `report_date` alone.

For a rebalance date:

- indicator is visible only if `notice_date < rebalance_date`;
- if multiple reports are visible, use the latest visible report;
- if no report is visible, the factor is missing.

## V2 Quality Mapping

The V5 runner builds a JoinQuant-manual wide table:

- `asset_quality_trend`: previous-year NPL ratio minus current-year NPL ratio; fallback to negative current NPL ratio.
- `provision_buffer`: provision coverage ratio only. Do not mix provision-to-loan ratio into this score because the unit differs.
- `capital_resilience`: core tier 1 capital adequacy ratio; fallback to tier 1 capital adequacy ratio, then total capital adequacy ratio.

These are engineering mappings, not accepted factor definitions. Quant Validation Agent must test whether they have predictive value.

## Required Validation

Before using these indicators in a formal strategy:

- check coverage by bank and year;
- check review status distribution;
- compare extracted values against raw snippets for a sample;
- verify `notice_date` alignment;
- report missingness by rebalance date;
- run common-sample IC and RankIC;
- run low-PB baseline versus low-PB plus quality guard;
- run robustness by excluding `needs_check` values;
- flag any result that disappears when only `reviewed` rows are used.

## Failure Modes

- OCR or text extraction selects the regulatory threshold instead of the reported value.
- A table contains multiple years and the wrong year column is chosen.
- Group and Bank scopes are mixed.
- Annual report date is used as if it were the disclosure date.
- `needs_check` candidate rows are treated as reviewed data.
- V4 extracted rows are used for platform confirmation but then mistaken for formal evidence.

## Usage Notes

Research Agent may cite annual-report indicators as financially meaningful variables.

Quant Validation Agent must decide whether extracted values are reliable enough for testing and whether any factor survives common-sample rolling validation.

Engineering Agent may use `eastmoney_bank_quality_manual_csv.csv` to populate JoinQuant `MANUAL_BANK_QUALITY_CSV` for platform simulation, but the simulation must be labeled according to review status.
