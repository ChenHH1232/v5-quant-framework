# Telecom Operator Cash-Flow Dividend Observation Framework V5.7

Date: 2026-07-18

Owner:

```text
Research Agent
```

Status:

```text
research_knowledge_packet
observation_sleeve_only
small_sample_policy_required
```

## PM Position

Telecom operators fit the dividend cash-flow theme economically, but the A-share universe is too small for normal standalone IC / RankIC acceptance.

Current status:

```text
basket_observation_only
```

## Core Economic Logic

Telecom operators may be useful in a future basket because they have:

- recurring service revenue;
- large operating cash flow;
- policy-supported digital infrastructure role;
- relatively visible dividend plans;
- potential capex moderation after 5G peak investment.

But the sector has special risks:

- only a few A-share listed operators;
- capex cycle can dominate FCF;
- AI/cloud investment may shift cash-flow use from shareholder return to growth capex;
- depreciation and amortization can distort accounting profit;
- broad IC tests are statistically weak with such a narrow universe.

## Research Hypotheses

### H1: Telecom Is A Basket Sleeve, Not A Standalone Sector Strategy

Hypothesis:

```text
Telecom operator exposure may improve basket dividend stability and cash-flow quality, but should be judged at basket level.
```

PM implication:

```text
Do not promote telecom as a formal standalone model without a small-sample sleeve policy.
```

### H2: FCF Must Be Capex-Cycle Aware

Hypothesis:

```text
FCF yield is useful only after controlling for capex-to-OCF and capex-cycle phase.
```

Candidate variables:

```text
operating_cash_flow_yield
free_cash_flow_yield
capex_to_ocf
dividend_yield
dividend_payout_ratio
depreciation_amortization_to_revenue
service_revenue_growth
```

### H3: Low Volatility Is More Useful As Allocation Guard

Hypothesis:

```text
Telecom low volatility should control basket sleeve risk, not act as alpha proof.
```

## Required PIT Fields

```text
code
trade_date
report_period
visible_date
operator_purity
operating_cash_flow_yield
free_cash_flow_yield
capex_to_ocf
dividend_yield
dividend_payout_ratio
depreciation_amortization_to_revenue
service_revenue_growth
volatility_120d
max_drawdown_120d
beta_120d
```

## Validation Rules

Quant Agent may run:

```text
basket-level contribution test
small-sample diagnostic baseline
stress-period attribution
capex-cycle bucket diagnostic
```

Quant Agent must not report:

```text
broad-sector IC acceptance
standalone accepted strategy
formal_strategy_candidate
```

unless PM first approves a small-sample sleeve policy.

## Source Register

- [5442278 - 中国电信2025年报及2026年一季报点评：算力规模显著提升，Token经营迈入新台阶](https://www.fxbaogao.com/view?id=5442278)

The current telecom report search has high noise. Future searches should focus on individual operators and annual reports:

```text
中国移动 年报 分红 资本开支 经营现金流
中国电信 年报 分红 资本开支 经营现金流
中国联通 年报 分红 资本开支 经营现金流
```
