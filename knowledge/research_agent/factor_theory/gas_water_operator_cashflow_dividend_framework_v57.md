# Gas / Water Operator Cash-Flow Dividend Framework V5.7

Date: 2026-07-18

Owner:

```text
Research Agent
```

Status:

```text
research_knowledge_packet
needs_pit_panel_before_quant_validation
```

## PM Position

Gas / water operators are the preferred next formal research target after V5.7 screening.

Reason:

```text
They are closest to the V5.1 utilities golden template, but their value traps are different enough that a separate knowledge and data gate is required.
```

## Core Economic Logic

Gas and water operators can fit the V5 dividend low-vol OCF basket because they often have:

- local monopoly or quasi-monopoly service areas;
- regulated or policy-linked prices;
- recurring demand;
- infrastructure-like asset duration;
- potential dividend support from stable operating cash flow.

But the sector cannot be treated as automatically safe. The first-pass report screen highlights:

- water tariff reform is gradual, so revenue improvement may lag cost pressure;
- government payment and receivables can distort apparent earnings quality;
- debt expansion can support projects while weakening future dividend capacity;
- cross-region expansion can become a value trap if local fiscal strength is weak;
- project, construction or environmental-engineering revenue must be separated from true operation.

## Research Hypotheses

### H1: OCF Yield Is More Robust Than Raw FCF

Hypothesis:

```text
High operating_cash_flow_yield predicts better risk-adjusted returns among true gas / water operators.
```

Rationale:

```text
OCF captures recurring cash generation before capex distortions. Raw FCF can punish legitimate network expansion or accidentally reward underinvestment.
```

Quant test:

```text
OCF-only baseline
OCF + dividend support
OCF + receivables guard
OCF + debt guard
```

### H2: Receivables And Debt Are Value-Trap Guards

Hypothesis:

```text
High dividend or high OCF stocks should be filtered when receivables and debt pressure deteriorate.
```

Candidate guards:

```text
receivables_to_revenue
receivables_growth_minus_revenue_growth
net_debt_to_ocf
interest_bearing_debt_growth
cash_short_debt_ratio
```

### H3: FCF Is Conditional, Not Universal

Hypothesis:

```text
FCF becomes useful only after distinguishing maintenance capex from expansion / project capex.
```

Research decision:

```text
FCF starts as fcf_support_candidate, not fcf_core_candidate.
```

## Required PIT Fields

Before Quant Agent may run formal validation:

```text
code
trade_date
report_period
visible_date
operator_purity
water_revenue_share
gas_revenue_share
project_or_engineering_revenue_share
operating_cash_flow_yield
free_cash_flow_yield
dividend_yield
dividend_payout_ratio
receivables_to_revenue
net_debt_to_ocf
capex_to_ocf
asset_liability_ratio
```

## Data Route

Preferred source order:

1. JoinQuant / DataJQ for daily prices, dividends, PIT financial fields and industry membership.
2. Eastmoney/F10 for first-layer segment clues.
3. Annual reports / interim reports for original business-purity review.
4. Tushare / TCER-style disclosure dates for announcement cross-check.
5. Reports for business logic and field discovery only.

## PM Gate

Gas / water can enter formal validation only after:

```text
operator_purity PIT panel exists
receivables/debt fields have visible dates
dividend and OCF fields are sourced from PIT financial data
FCF remains support unless capex-quality gate passes
```

## Source Register

- [5462617 - 2026年水务行业分析：水价改革渐进式推进，关注水务企业盈利承压、债务扩张与回款风险](https://www.fxbaogao.com/view?id=5462617)
- [5337413 - 公用事业行业深度跟踪：年报初窥，现金流改善分红提升，公用事业化加速推进](https://www.fxbaogao.com/view?id=5337413)

Reports are hypothesis sources only. Formal data must be PIT audited.
