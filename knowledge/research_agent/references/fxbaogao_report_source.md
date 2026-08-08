# Fxbaogao Report Source

Date: 2026-07-17

Status:

```text
available_for_research_agent_knowledge_collection
```

## Purpose

Fxbaogao is now available as a V5 Research Agent report-discovery source.

Use it for:

- industry research discovery;
- company research discovery;
- report paragraph screening;
- locating annual-report / solvency-report references;
- forming Research Agent knowledge cards.

Do not use it directly as:

- PIT financial data;
- accepted factor evidence;
- strategy acceptance evidence;
- a substitute for original announcement dates.

## V5 Runner

Search:

```text
python -m v5.cli research-report-search --keywords-file research_reports/fxbaogao_insurance_ev_nbv_probe/keywords.txt --end-time last1year --out research_reports/fxbaogao_insurance_ev_nbv_probe
```

Paragraph fetch:

```text
python -m v5.cli research-report-paragraphs <report_id> --keyword "内含价值" --out research_reports/fxbaogao_insurance_ev_nbv_probe
```

Stage 1 local filtering:

```text
python -m v5.cli research-report-filter <report_candidates.csv...> --out research_reports/fxbaogao_filtered --include-all "红利低波" --include-any "回撤" --include-any "风险预算"
```

The filter writes:

- `filtered_report_candidates.csv`
- `rejected_report_candidates.csv`
- `filter_manifest.json`

Filtered rows are source leads only. They are not evidence cards until paragraph or PDF review is complete.

V5c seed-report retrieval:

```text
python -m v5.cli v5c-fxbaogao-seed-retrieval --root D:\hh\codex\v5 --end-time last1year
```

This V5c runner uses the fixed seed list from `v5c_fxbaogao_seed_retrieval_runner.py`, applies local title filtering, fetches paragraphs only for Stage 1 accepted reports, and downloads PDFs only for paragraph-passed source leads. Downloaded PDFs still require original-text review before A/B knowledge cards are allowed.

## V5c Two-Stage Retrieval Policy

For V5c defense / profit-taking / rebalancing overlay research, broad keywords produced noisy recall. Until the API provider confirms advanced filtering support, Research Agent must use:

1. Narrow keyword search.
2. Local title filter with explicit exclusions for daily, weekly, monthly, morning-note, company-report and valuation-table noise.
3. Paragraph or PDF review for accepted source leads.
4. Local rerank before any report can become a knowledge card.

Only PDF-original-checked thematic research, financial-engineering, strategy, fund-research or asset-allocation reports can become A/B evidence.

Current local API documentation only confirms:

- `keywords`
- `orgNames`
- `startTime`
- `endTime`

Do not assume undocumented parameters such as `reportTypes`, `titleKeywords`, `excludeKeywords`, `searchFields`, `sortBy`, `pageSize` or `page` are supported until the API provider confirms them.

## Credential Policy

The API key is stored outside the repository in the local vault.

Output files must never persist:

```text
FXBAOGAO_API_KEY
Authorization header
raw credential text
```

## Insurance Use Case

For V5.3 insurance, Fxbaogao should be used first to find reports on:

- insurance company embedded value;
- new business value;
- P/EV valuation;
- life insurance franchise value;
- solvency and asset-liability management;
- 2021 / 2022 / 2026 insurance weak-year explanations.

Research reports may help identify useful variables, but formal PIT validation still requires original report announcement date and field-definition review.
