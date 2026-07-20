# Environmental / Project Operators Source Collection Plan V5.9

Date: 2026-07-21

Owner:

```text
Research Agent
```

Status:

```text
blocked_data_repair_seed
not_quant_ready
```

## Research Boundary

Environmental / project operators are not eligible for formal modeling yet. They are a value-trap watchlist until V5 can distinguish true operating cash-flow assets from project, construction, equipment and PPP receivable exposure.

Initial inclusion focus only after repair:

```text
waste incineration operators
water / sewage treatment operators
solid-waste operation platforms
```

Initial exclusions or downgrade cases:

```text
engineering / EPC companies
equipment manufacturers
PPP project-heavy companies with receivable pressure
companies dependent on subsidy arrears or local-government repayment
```

## Source Priority

1. Annual reports for segment split, project revenue and receivable notes.
2. JoinQuant / DataJQ PIT financial fields, dividends and daily prices.
3. Eastmoney/F10 as first-layer business clues only.
4. Tushare / exchange disclosure dates for announcement visibility.
5. Research reports for identifying receivable, subsidy and cash-conversion risks.

## FxBaogao Search Seed

Local search output:

```text
research_reports_v59_expansion/environmental_project_operators/report_candidates.csv
```

Useful first-pass candidates:

| Report ID | Title | Link | Use |
| --- | --- | --- | --- |
| 5497436 | Hidden-debt replacement quota and environmental cash-flow improvement | https://www.fxbaogao.com/view?id=5497436 | Receivable and cash-flow repair context |
| 5505542 | Environmental industry mid-year strategy | https://www.fxbaogao.com/view?id=5505542 | Dividend and operating-risk vocabulary |
| 5193123 | Tianjin Capital Environmental receivables recovery comment | https://www.fxbaogao.com/view?id=5193123 | Company-level receivable risk example |

## Required Data Before Any Modeling

```text
PIT business-purity split
visible_date
operator_revenue_share
EPC_or_construction_revenue_share
equipment_revenue_share
PPP_project_exposure
receivables_to_revenue
receivables_ageing
government_receivable_share_if_available
operating_cash_flow_yield
free_cash_flow_yield
capex_to_ocf
dividend_yield
cash_dividend_coverage_by_ocf
real daily open / close prices
cash dividends
```

## PM Gate

Environmental / project operators stay `blocked_by_data_gate` until:

```text
business-purity split exists
receivable trap guard exists
project / EPC exposure is PIT-tagged
cash conversion is audited
```
