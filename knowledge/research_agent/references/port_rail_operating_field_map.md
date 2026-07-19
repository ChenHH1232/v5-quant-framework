# Port / Rail Operating Field Map

Date: 2026-07-18

Owner:

```text
Research Agent
```

## V5.5b Fields

| Field | Source | PIT visibility | Use |
| --- | --- | --- | --- |
| dividend_yield | JoinQuant valuation.dividend_ratio | trade_date vendor PIT | shareholder return |
| low_price_to_book | JoinQuant valuation.pb_ratio | trade_date vendor PIT | valuation |
| operating_cash_flow_yield | cash_flow.net_operate_cash_flow / market_cap | trade_date vendor PIT | cash-flow value |
| free_cash_flow_yield | OCF - capex / market_cap | trade_date vendor PIT | distributable cash proxy |
| revenue_growth_yoy | JoinQuant indicator.inc_revenue_year_on_year | trade_date vendor PIT | demand / utilization proxy |
| total_revenue_growth_yoy | JoinQuant indicator.inc_total_revenue_year_on_year | trade_date vendor PIT | demand / utilization proxy |
| ocf_to_revenue | JoinQuant indicator.ocf_to_revenue | trade_date vendor PIT | cash conversion |
| cash_collection_quality | JoinQuant indicator.goods_sale_and_service_to_revenue | trade_date vendor PIT | revenue collection quality |
| interest_coverage | income operating profit or OCF / interest or financial expense | trade_date vendor PIT | debt serviceability |
| capex_burden | cash paid for fixed / intangible assets / OCF | trade_date vendor PIT | capex pressure |
| asset_liability_ratio | total_liability / total_assets | trade_date vendor PIT | leverage pressure |

## Required Future Manual / External Fields

| Field | Preferred source | Status |
| --- | --- | --- |
| cargo throughput | annual reports, port company operating data, official port statistics | needed before Engineering |
| container throughput | annual reports, official port statistics | needed before Engineering |
| railway freight volume | annual reports, railway statistics | needed before Engineering |
| rail passenger volume | annual reports, railway statistics | optional by subgroup |
| tariff / pricing policy | company announcements, regulator policy | needed before Engineering |
| port / rail revenue share | annual reports / segment table | needed before Engineering |

## Data Warning

V5.5b uses financial-statement operating proxies because they are fully covered and PIT-queryable.

They are not the same as real operating volume.

Before a strategy is accepted or deployed, Research Agent must decide whether the financial proxies are sufficient or whether original throughput / freight fields must be reviewed.

