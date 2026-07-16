# Insurance Source Collection Plan

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

Status:

```text
research_preparation
```

## Source Order

1. Company annual reports, interim reports and solvency reports.
2. Exchange announcements and report disclosure dates.
3. JoinQuant / DataJQ price, valuation, dividend and financial fields.
4. Regulatory or industry statistics for premium growth and insurance market state.
5. Bond-yield and equity-index market data for external state.
6. Eastmoney F10 and similar vendor pages as first-pass structure only.
7. Tushare announcement links for report-date cross-checking.

## Source Tags

Use one of:

```text
official
company_disclosure
vendor
market_proxy
manual_review
not_pit_usable_until_audited
```

## Required Metadata

Each collected row should carry:

```text
security
field
period
value
source_name
source_url_or_file
source_publication_date
visible_date
review_status
pit_usable
```

## Crawling / Access Guardrails

- Do not force scraping protected or rate-limited pages.
- Prefer official downloadable reports, exchange announcements and APIs already available in V5.
- Vendor pages may provide structure, but formal validation requires publication-date review.
- Manual import templates are acceptable when official data is hard to automate.

