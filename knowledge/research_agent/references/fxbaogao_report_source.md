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
