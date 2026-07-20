# Pharma / Medical Services Cash-Flow Framework V5.9

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

Pharma / medical services may add diversification to the enhanced ETF basket, but it is not a clean dividend low-volatility sleeve unless the model separates mature cash-flow businesses from R&D and policy-sensitive businesses.

## Economic Logic

Potential fit:

- mature products or services with recurring demand;
- stable cash conversion;
- moderate policy pressure;
- dividend backed by operating cash flow;
- lower volatility because demand is defensive.

Main risks:

- centralized procurement and reimbursement pressure;
- R&D pipeline failure;
- capitalized R&D and acquisition distortions;
- inventory and receivable pressure;
- one-off licensing or impairment effects;
- high valuation despite weak cash conversion.

## Research Hypotheses

### H1: Subsector Split Comes Before Factor Testing

Hypothesis:

```text
Generic pharma-wide IC/RankIC is unreliable unless subsectors are separated.
```

Required buckets:

```text
mature_pharma
medical_services
testing_services
medical_devices
innovation_or_pipeline_heavy
```

### H2: OCF Yield May Work Only In Mature / Service Buckets

Hypothesis:

```text
OCF yield has economic meaning in mature pharma and medical services, but is weaker for innovation-heavy companies.
```

### H3: FCF Needs R&D And Capex Adjustment

Hypothesis:

```text
Raw FCF can punish research investment or reward underinvestment, so it cannot be a basket-wide mainline.
```

Candidate guards:

```text
R&D_to_revenue
capitalized_R&D_ratio
inventory_growth_minus_revenue_growth
receivables_to_revenue
gross_margin_stability
procurement_pressure_state
```

## Factor Role Decision

| Factor | Initial role | Promotion rule |
| --- | --- | --- |
| `operating_cash_flow_yield` | conditional candidate | Only after PIT subsector split |
| `low_volatility_score` | risk-quality candidate | Allowed if daily prices pass |
| `free_cash_flow_yield` | diagnostic | Needs R&D/capex adjustment |
| `dividend_yield` | support variable | Requires OCF coverage |
| `policy_state` | risk-control / state variable | Mandatory before promotion |

## Quant Handoff Conditions

Do not run formal validation until:

1. PIT subsector split exists.
2. R&D, policy and working-capital fields have visible-date route.
3. Mature cash-flow bucket has enough sample size.
4. FCF is explicitly adjusted or downgraded to diagnostic.

Historical performance alone is never sufficient evidence for accepting a strategy.
