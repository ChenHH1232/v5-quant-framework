# Utilities Data Field Map

Date: 2026-07-16

Owner:

Research Agent

Project:

```text
V5.1 Utilities Sector Process-Portability Test
```

Status:

```text
research_preparation
```

## Purpose

This map defines the fields needed before Quant Validation Agent can run V5.1 `research_pit_validation`.

Each field must later be checked for point-in-time visibility, missing-data risk, and source consistency.

## Market Data

| Field | Candidate source | PIT route | Required? | Risk |
| --- | --- | --- | --- | --- |
| unadjusted open | JoinQuant / DataJQ | trading-day data visible on day | required for platform replication | execution price mismatch |
| unadjusted close | JoinQuant / DataJQ | trading-day data visible after close | required | adjustment mismatch |
| volume / turnover | JoinQuant / DataJQ | trading-day data | required | liquidity filters may overfit |
| market cap | JoinQuant / DataJQ | daily valuation table | required | source-definition mismatch |
| suspension / ST | JoinQuant / DataJQ | daily status | required | survivorship and tradability bias |

## Valuation

| Field | Candidate source | PIT route | Required? | Risk |
| --- | --- | --- | --- | --- |
| PB | JoinQuant valuation / DataJQ | date-indexed valuation | required | book-value update visibility |
| PE | JoinQuant valuation / DataJQ | date-indexed valuation | optional | negative earnings handling |
| EV / EBITDA | financial statements + market cap + debt + cash | statement pubDate + daily market data | exploratory | formula and availability risk |
| operating cash-flow yield | cash-flow statement + market cap | statement pubDate + daily market data | required candidate | annual vs quarterly comparability |
| free-cash-flow yield | OCF - capex over market cap | statement pubDate | optional | capex field mapping risk |

## Dividend

| Field | Candidate source | PIT route | Required? | Risk |
| --- | --- | --- | --- | --- |
| cash dividend per share | JoinQuant / Tushare / exchange disclosure | announcement date and ex-dividend date | required | announcement vs payment-date confusion |
| dividend yield | dividend per share / price | dividend visible date + price date | required candidate | look-ahead if future dividend used |
| payout ratio | dividend / net profit | dividend plan visible date + statement pubDate | optional | negative profit handling |
| dividend continuity | prior visible dividend records | visible historical records only | required candidate | IPO and missing-history bias |
| dividend coverage by OCF | cash dividend / OCF | dividend visible date + cash-flow pubDate | required candidate | per-share vs total amount mismatch |

## Profitability Quality

| Field | Candidate source | PIT route | Required? | Risk |
| --- | --- | --- | --- | --- |
| ROE | financial statements | statement pubDate | required candidate | diluted / weighted ROE definitions |
| gross margin | financial statements | statement pubDate | optional | utilities subgroup comparability |
| operating margin | income statement | statement pubDate | required candidate | fuel-cost cycle sensitivity |
| earnings volatility | historical visible statements | rolling visible window | optional | window choice risk |
| ROIC | constructed field | statement pubDate | exploratory | formula consistency risk |

## Cash Flow

| Field | Candidate source | PIT route | Required? | Risk |
| --- | --- | --- | --- | --- |
| operating cash flow | cash-flow statement | statement pubDate | required | quarterly seasonality |
| capital expenditure | cash-flow statement | statement pubDate | required candidate | field sign convention |
| free cash flow | OCF - capex | statement pubDate | required candidate | negative FCF may be normal during capex cycles |
| OCF / net profit | statements | statement pubDate | required candidate | negative earnings handling |
| capex intensity | capex / revenue or assets | statement pubDate | optional | subgroup comparability |

## Debt-Service Capacity

| Field | Candidate source | PIT route | Required? | Risk |
| --- | --- | --- | --- | --- |
| asset-liability ratio | balance sheet | statement pubDate | required candidate | high debt may be normal |
| interest expense | income statement / notes if available | statement pubDate | required candidate | field availability |
| interest coverage | EBIT / interest expense | statement pubDate | required candidate | low or missing interest expense |
| debt / OCF | balance sheet + cash-flow statement | statement pubDate | required candidate | short-term OCF volatility |
| cash after interest, capex, dividend | constructed | statement + dividend visible dates | exploratory | multiple-date alignment |

## Data Collection Gate

Before formal validation starts, Engineering Agent or Quant Validation Agent must confirm:

- each required field has a source;
- each financial field has a usable visible date;
- raw field names are mapped to normalized field names;
- missing-data behavior is explicit;
- dividend announcement, ex-dividend, and payment dates are not mixed.
