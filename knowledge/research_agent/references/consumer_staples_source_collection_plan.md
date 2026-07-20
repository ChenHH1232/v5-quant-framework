# Consumer Staples Source Collection Plan V5.9

Date: 2026-07-21

Owner:

```text
Research Agent
```

Status:

```text
research_knowledge_gate_seed
not_quant_ready
```

## Research Boundary

Consumer staples can be considered for the dividend low-volatility OCF basket only when the business is mature, recurring and cash-generative.

Initial inclusion focus:

```text
food and beverage leaders
household and personal-care cash-flow leaders
stable distribution or brand companies with recurring demand
```

Initial exclusions or downgrade cases:

```text
fashion-cycle discretionary consumption
inventory-heavy retailers
high-growth brands with unstable margins
companies relying on channel stuffing or one-off working-capital release
```

## Source Priority

1. JoinQuant / DataJQ PIT financial statements, dividends and daily prices.
2. Annual reports for segment purity, channel structure and working-capital notes.
3. Eastmoney/F10 for first-layer segment and business description clues.
4. Tushare / exchange disclosure dates for original announcement visibility.
5. Research reports for industry logic, field discovery and value-trap vocabulary only.

## FxBaogao Search Seed

Local search output:

```text
research_reports_v59_expansion/consumer_staples/report_candidates.csv
```

Useful first-pass candidates:

| Report ID | Title | Link | Use |
| --- | --- | --- | --- |
| 5415880 | Food and beverage industry report: free cash flow and recovery trend | https://www.fxbaogao.com/view?id=5415880 | FCF interpretation and sector recovery context |
| 5421725 | Multi-industry dividend asset monthly report using FCF | https://www.fxbaogao.com/view?id=5421725 | Cross-industry FCF screening vocabulary |
| 5460725 | CSI 800 free cash-flow ETF investment value analysis | https://www.fxbaogao.com/view?id=5460725 | Basket-level FCF product framing only |

## Required Data Before Quant Validation

```text
PIT universe
visible_date
operating_cash_flow_yield
free_cash_flow_yield
dividend_yield
cash_dividend_coverage_by_ocf
gross_margin_stability
inventory_turnover
receivables_to_revenue
working_capital_change_to_revenue
capex_to_ocf
real daily open / close prices
cash dividends
```

## Anti-Crawling / Access Policy

- FxBaogao API search is allowed for report discovery.
- Do not scrape report pages aggressively.
- Paragraph extraction is allowed for screening; PDF/original report review is required before any formal hypothesis cites a report.
- Research reports cannot become factor data.

## PM Gate

Consumer staples may move from `needs_manual_research_before_formal` to `ready_for_batch_initial_validation` only after:

```text
business-quality universe rule exists
working-capital trap guard exists
PIT financial fields and visible dates are mapped
FCF is classified as core / support / rejected by subsector
```
