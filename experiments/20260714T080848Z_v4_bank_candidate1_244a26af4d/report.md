# Research Run: V4 Bank Fundamental Candidate 1

- Strategy ID: `v4_bank_candidate1`
- Objective: Reproduce the accepted V4 bank fundamental strategy as the first V5 standard case.
- Audit passed: `True`
- Engine stage: scaffold

## Audit Issues

- `warning` `NO_FINANCIAL_DISCLOSURE_LAG`: Factor roe has zero disclosure lag; confirm the vendor uses true announcement dates.
- `warning` `NO_FINANCIAL_DISCLOSURE_LAG`: Factor non_performing_loan_ratio has zero disclosure lag; confirm the vendor uses true announcement dates.
- `warning` `NO_FINANCIAL_DISCLOSURE_LAG`: Factor capital_adequacy_ratio has zero disclosure lag; confirm the vendor uses true announcement dates.
- `warning` `NO_FINANCIAL_DISCLOSURE_LAG`: Factor provision_coverage_ratio has zero disclosure lag; confirm the vendor uses true announcement dates.

## Notes

This scaffold run validates the strategy contract and records artifacts. Real factor computation, rolling validation, and executable backtests are intentionally not mocked.
