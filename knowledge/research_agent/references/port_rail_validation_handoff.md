# Port / Rail Validation Handoff

Date: 2026-07-18

Owner:

```text
Research Agent -> Quant Validation Agent
```

## Hypothesis

Port / rail infrastructure stocks should be selected by cash-flow value and dividend discipline only when operating state is acceptable.

## Test Model

V5.5b should test:

```text
dividend_yield
operating_cash_flow_yield
free_cash_flow_yield
low_price_to_book
operating_state_score
capex_burden
```

Where operating_state_score is built from:

```text
revenue_growth_yoy
ocf_to_revenue
cash_collection_quality
interest_coverage
asset_liability_ratio
capex_burden
```

## Required Quant Tests

```text
baseline
IC / RankIC
rolling validation
ablation
robustness
state bucket validation
port-only subgroup validation
rail-only subgroup validation
2026 failure analysis
```

## Falsification Conditions

Reject or return to Research if:

```text
the repaired model does not beat equal-weight or high-dividend baselines;
operating_state_score has weak or contradictory IC evidence;
2026 failure worsens materially;
port-only and rail-only behavior contradicts the combined model;
results depend on one selection_count setting;
```

