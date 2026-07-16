# Insurance Data Field Map

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
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
| valuation | P/EV | annual report / company disclosure / vendor | report publication date | optional until audited |
| valuation | dividend yield | dividend records + price | announcement / ex-date / payment date separated | required |
| franchise | premium income growth | company reports / regulator statistics | publication date | required if available |
| franchise | embedded value growth | annual report | report publication date | optional |
| franchise | new business value growth | annual report / interim report | report publication date | optional |
| P&C quality | combined ratio | annual / interim report | report publication date | required for P&C if available |
| P&C quality | claim ratio, expense ratio | annual / interim report | report publication date | optional |
| investment | investment yield | annual / interim report | report publication date | required if available |
| investment | total investment income | financial statements | report publication date | required |
| solvency | comprehensive solvency adequacy ratio | solvency report / company disclosure | publication date | required if available |
| solvency | core solvency adequacy ratio | solvency report / company disclosure | publication date | required if available |
| shareholder return | cash dividend | JoinQuant / exchange / company announcement | announcement, ex-date, pay-date separated | required |
| shareholder return | payout ratio | dividend / net profit | report publication date | required |
| external state | 10Y government bond yield | bond market data / JoinQuant / official market source | trade date or publication date | required |
| external state | yield-curve slope | derived from bond yields | trade date | required |
| external state | equity-market state | broad index / insurance index | trade date | required |
| external state | credit spread | bond index or market proxy | trade date or publication date | optional |
| external state | industry premium growth | regulator / industry statistics | publication date | optional |

## Date Rules

Financial and insurance operating fields must use:

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

- Missing required market or valuation fields: drop that security on that rebalance date.
- Missing optional insurance-specific fields: allow baseline run but report coverage.
- Missing solvency / EV / NBV fields: do not infer from future reports.
- Missing subgroup tag: classify as `manual_review_required` and run sensitivity excluding it.

## Data Quality Risks

- treating life insurance and P&C insurance as identical;
- using current business structure for historical dates;
- using embedded value before report publication;
- mixing investment gains with operating insurance quality;
- treating high dividend as quality without solvency and cash-flow support;
- overfitting to rate or equity-market rebounds.

