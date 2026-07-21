# Food / Beverage Cash-Flow Quality Framework V5a.4

Date: 2026-07-21  
Owner: Research Agent  
Status: research_framework; data_gate_not_passed; not_quant_ready

## PM Starting View

Food and beverage is one of the best second-pass candidates for a dividend low-volatility, OCF and sector-approved FCF enhanced ETF because demand can be defensive and cash conversion can be strong.

But it cannot be treated as one homogeneous sector. Liquor, dairy, condiments, packaged food, beer and soft drinks have different inventory cycles, pricing power, channel structures and valuation regimes.

## Core Question

```text
Does the company convert durable brand / channel power into cash, or is reported cash flow temporarily boosted by channel stocking, working-capital release or delayed investment?
```

## Economic Logic

Potential fit:

- recurring consumption demand;
- brand and channel moat;
- stable gross margin;
- high OCF conversion;
- moderate capex;
- dividend capacity;
- lower earnings volatility than cyclical sectors.

Failure modes:

- inventory builds before demand weakens;
- receivables or channel financing hide distributor pressure;
- high valuation overwhelms cash-flow quality;
- one-off price increases inflate margins temporarily;
- FCF improves because capex or marketing investment is delayed;
- subsector composition drives the factor, not company quality.

## Research Hypotheses

### H1: OCF Yield + Margin Stability Is The First Mainline

Hypothesis:

```text
Within mature food / beverage companies, high OCF yield works only when gross margin and cash conversion are stable.
```

Candidate fields:

```text
operating_cash_flow_yield
gross_margin_stability_3y
ocf_to_net_profit
ocf_to_revenue
revenue_growth_stability
```

### H2: Working Capital Is The Main Value-Trap Guard

Hypothesis:

```text
Inventory and receivable deterioration predicts future factor failure better than raw valuation.
```

Candidate guards:

```text
inventory_growth_minus_revenue_growth
receivables_growth_minus_revenue_growth
contract_liability_growth_state
channel_pressure_proxy
```

### H3: FCF Can Be Promoted After Capex / Marketing Investment Review

Hypothesis:

```text
FCF yield is useful when capex and selling expense investment are not being artificially suppressed.
```

Required checks:

```text
capex_to_depreciation
capex_to_revenue
selling_expense_to_revenue
brand_or_channel_reinvestment_stability
```

## Factor Role Decision

| Factor | Role | Promotion Rule |
| --- | --- | --- |
| `operating_cash_flow_yield` | primary candidate | PIT panel and subsector split required |
| `low_volatility_score` | primary risk-quality gate | 60/120/252d factors required |
| `dividend_yield` | support variable | Requires cash-flow coverage |
| `free_cash_flow_yield` | enhancement candidate | Requires capex / reinvestment gate |
| `low_price_to_book` | not mainline | Food/beverage value often not book-asset driven |
| `momentum` | support candidate | May capture brand/repricing trend; turnover audit required |
| `mean_reversion` | support only | Requires inventory/channel trap guard |

## Quant Handoff Conditions

Do not run formal validation until:

1. PIT subsector split exists.
2. Working-capital fields are available with visible dates.
3. OCF, dividend and low-vol factors exist for the same panel.
4. FCF is only used after capex/reinvestment gate.
5. Liquor-heavy results are separated from broad food/beverage results.

Historical performance alone is never sufficient evidence for accepting a strategy.

