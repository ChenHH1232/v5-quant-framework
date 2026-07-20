# Consumer Staples Cash-Flow Framework V5.9

Date: 2026-07-21

Owner:

```text
Research Agent
```

Status:

```text
research_framework
data_gate_not_passed
not_quant_ready
```

## PM Starting View

Consumer staples are a possible expansion sleeve for a dividend low-volatility OCF enhanced basket, but they are not automatically comparable to utilities or toll roads.

The central question is:

```text
Does reported cash flow reflect durable brand / channel earning power, or temporary working-capital release?
```

## Economic Logic

The sector can fit V5 if a company has:

- recurring demand;
- pricing power or resilient brand moat;
- stable gross margin;
- moderate capex burden;
- cash conversion that supports dividends;
- low volatility because earnings and demand are less cyclical.

The sector can become a value trap when:

- inventory builds faster than revenue;
- receivables rise because channels are stressed;
- gross margin stability breaks;
- high dividend is funded by balance sheet, not OCF;
- FCF rises only because maintenance investment is deferred.

## Research Hypotheses

### H1: OCF Yield Is The First Mainline

Hypothesis:

```text
Among mature consumer staples, higher operating_cash_flow_yield predicts better risk-adjusted return than raw valuation alone.
```

Quant tests:

```text
OCF baseline
OCF + low-volatility
OCF + dividend support
OCF + working-capital guard
```

### H2: FCF Is Conditional On Working Capital And Capex Quality

Hypothesis:

```text
FCF yield is useful only when inventory, receivables and capex behavior do not imply underinvestment or channel pressure.
```

Candidate guards:

```text
inventory_growth_minus_revenue_growth
receivables_growth_minus_revenue_growth
working_capital_change_to_revenue
capex_to_ocf
gross_margin_stability
```

### H3: Dividend Is Support, Not Standalone Alpha

Hypothesis:

```text
Dividend yield supports the basket only when covered by OCF and stable margins.
```

Candidate fields:

```text
dividend_yield
dividend_payout_ratio
cash_dividend_coverage_by_ocf
three_year_dividend_continuity
```

## Factor Role Decision

| Factor | Initial role | Promotion rule |
| --- | --- | --- |
| `operating_cash_flow_yield` | primary candidate | PIT panel and IC/RankIC required |
| `low_volatility_score` | primary risk-quality candidate | Can be built from daily prices |
| `free_cash_flow_yield` | support candidate | Requires working-capital and capex-quality gate |
| `dividend_yield` | support variable | Requires OCF coverage |
| `low_price_to_book` | not mainline | Only subsector diagnostic if justified |

## Quant Handoff Conditions

Do not start formal validation until:

1. PIT universe excludes unstable discretionary and retail inventory traps.
2. Cash-flow, dividend and working-capital fields have visible-date route.
3. Low-volatility factors exist for the same PIT panel.
4. FCF has a sector-specific capex / working-capital quality gate.

Historical performance alone is never sufficient evidence for accepting a strategy.
