# Coal Data Field Map

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Status:

```text
research_preparation
```

## Field Map

| Group | Field | Initial source candidate | PIT route | Status |
| --- | --- | --- | --- | --- |
| market | open, close, volume | JoinQuant / DataJQ price API | trade date | required |
| market | market cap | JoinQuant valuation | trade date | required |
| market | ST, suspension, limit status | JoinQuant / DataJQ | trade date | required |
| valuation | PB | JoinQuant valuation | trade-date visible | required |
| valuation | PE | JoinQuant valuation | trade-date visible | required |
| valuation | EV / EBITDA | vendor or derived | announcement-date visible | optional |
| valuation | operating cash-flow yield | cash-flow statement + market cap | announcement-date visible | required |
| valuation | free-cash-flow yield | OCF - capex + market cap | announcement-date visible | optional until capex quality passes |
| dividend | cash dividend | JoinQuant finance / dividend data | announcement, ex-date, payment date separated | required |
| dividend | dividend yield | derived or vendor | trade-date visible | required |
| dividend | payout ratio | dividend / net profit | announcement-date visible | required |
| dividend | dividend continuity | historical dividend records | visible after each announcement | required |
| cycle profitability | revenue YoY | financial statements | announcement-date visible | required |
| cycle profitability | net profit YoY | financial statements | announcement-date visible | required |
| cycle profitability | gross margin | financial statements | announcement-date visible | optional |
| cycle profitability | ROE / ROA | financial statements | announcement-date visible | required |
| cash flow | operating cash flow | cash-flow statement | announcement-date visible | required |
| cash flow | capex | cash-flow statement or derived purchase of fixed assets | announcement-date visible | required if reliable |
| cash flow | free cash flow | OCF - capex | announcement-date visible | optional |
| cash flow | OCF / net profit | derived | announcement-date visible | required |
| leverage | asset-liability ratio | balance sheet | announcement-date visible | required |
| leverage | interest coverage | income statement + finance expense | announcement-date visible | optional |
| leverage | debt / OCF | balance sheet + cash flow | announcement-date visible | optional |
| external state | thermal coal price | NBS / MOFCOM / CCTD / exchange proxy | source publication date -> visible date | required |
| external state | coking coal price | NBS / MOFCOM / CCTD / exchange proxy | source publication date -> visible date | required |
| external state | inventory or output | NBS / CCTD / coal association / NDRC | source publication date -> visible date | required |
| external state | coal-power spread | coal price + electricity price or tariff proxy | source publication date -> visible date | required |

## Date Rules

Financial statement fields must use:

```text
report_period + announcement_date + conservative_visible_date
```

Dividend fields must keep separate:

```text
announcement_date
ex_dividend_date
cash_payment_date
```

External state fields must keep separate:

```text
state_date
source_publication_date
visible_date
```

## Missing-Data Rules

- Missing required stock-level factor: drop that security on that rebalance date.
- Missing required external state: block the rebalance date for state-conditioned models.
- Missing optional field: allow baseline run but report coverage.
- Mixed-company tag missing: classify as `manual_review_required` and run exclusion sensitivity.

## Data Quality Risks

- using current industry classification for old dates;
- using future annual reports to classify mixed business before report publication;
- using annual coal output or price data before release date;
- using futures prices as if they were spot coal prices;
- using dividend yield without separating announcement, ex-date, and payment date;
- treating high dividend at cycle peak as quality without cash-flow coverage.
