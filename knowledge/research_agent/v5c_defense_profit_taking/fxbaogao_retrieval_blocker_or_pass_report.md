# fxbaogao Seed Report Retrieval Blocker Or Pass Report

As of 2026-07-26.

## Scope

V5c defense / profit-taking / rebalancing overlay research. This run used seed-report driven retrieval only. It did not modify V57f, did not run backtests, did not start JoinQuant, and did not tune parameters.

## Retrieval Rule

- API search used only documented fields: `keywords`, `orgNames`, `endTime`.
- Stage 1 used local title filtering with required seed title terms.
- Stage 1 exclusions: 日报, 周报, 月报, 晨会, 财报点评, 业绩点评, 快评, 估值表, 新发基金, 基金净值.
- Stage 2 fetched paragraphs only for Stage 1 accepted reports.
- PDF download was attempted only after paragraph pass.
- No A/B knowledge card is allowed until PDF original review is completed.

## Result

- Seed searches: 10
- Raw candidate rows: 200
- Unique candidate keys: 187
- Stage 1 title accepted: 54
- Stage 2 paragraph passed: 41
- PDFs downloaded for later original review: 41
- API/search errors: 0
- Final status: `pass_source_leads_downloaded_pdf_review_required_before_cards`

## Decision

Some source leads reached PDF download. They remain source leads until manual/PDF original review; no A/B cards were created in this run.

## Blockers / Errors

- None beyond the final status above.

## Output Files

- `seed_report_search_plan.csv`
- `seed_report_candidates.csv`
- `seed_report_filter_results.csv`
- `seed_report_paragraph_pdf_results.csv`
- `fxbaogao_retrieval_blocker_or_pass_report.md`
