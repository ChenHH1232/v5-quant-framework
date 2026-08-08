# V5c Fixed Risk Budget Overlay Engineering Comparison

This packet runs only the fixed ERC and fixed volatility-cap specs admitted by PM. It does not modify V57f, scan parameters, add sleeves, or start JoinQuant.

## Comparison

| Variant | Return | Max DD | Vol | Trades | Order health | Delta return | Delta DD | Delta risk HHI | PM conclusion |
|---|---:|---:|---:|---:|---|---:|---:|---:|---|
| v57f_official_frozen_baseline | 109.25% | 11.93% | 15.62% | 783 | pass |  |  |  | official_frozen_reference |
| equal_reference | 109.25% | 11.93% | 15.62% | 783 | pass | 0.00% | 0.00% | 0.000000 | equal_reference_for_engineering_comparison |
| erc_fixed_covariance | 109.44% | 11.93% | 15.52% | 784 | pass | 0.18% | -0.00% | -0.007578 | effective_risk_budget_diagnostic_needs_pm_quant_review_not_accepted |
| volatility_cap_reducer | 110.89% | 11.93% | 15.74% | 785 | pass | 1.64% | -0.00% | -0.001887 | effective_risk_budget_diagnostic_needs_pm_quant_review_not_accepted |

## Risk Budget Snapshot

### equal_reference

| Sleeve | Covariance risk contribution | Avg weight | DD loss share |
|---|---:|---:|---:|
| bank | 17.53% | 24.62% | 5.13% |
| utilities_electricity | 30.18% | 24.63% | 39.59% |
| highway_infrastructure | 24.62% | 23.62% | 30.66% |
| port_rail_infrastructure | 27.66% | 24.75% | 24.62% |

### erc_fixed_covariance

| Sleeve | Covariance risk contribution | Avg weight | DD loss share |
|---|---:|---:|---:|
| bank | 22.34% | 29.41% | 5.13% |
| utilities_electricity | 27.60% | 23.15% | 39.59% |
| highway_infrastructure | 24.69% | 23.51% | 30.66% |
| port_rail_infrastructure | 25.37% | 22.57% | 24.62% |

### volatility_cap_reducer

| Sleeve | Covariance risk contribution | Avg weight | DD loss share |
|---|---:|---:|---:|
| bank | 17.81% | 25.08% | 5.13% |
| utilities_electricity | 28.22% | 23.76% | 39.59% |
| highway_infrastructure | 26.27% | 25.09% | 30.66% |
| port_rail_infrastructure | 27.71% | 24.70% | 24.62% |

## Order Health

- `equal_reference`: needs_review `False`, normal `21/21`
- `erc_fixed_covariance`: needs_review `False`, normal `21/21`
- `volatility_cap_reducer`: needs_review `False`, normal `21/21`

## PM Decision

erc_fixed_covariance is effective diagnostic; promote to PM/Quant review only, not V57f replacement

## Still Blocked

- `v57f_core_replacement`: Any risk budget overlay changes allocation behavior and cannot rewrite frozen V57f without a new PM gate.
- `parameter_scan`: Changing lookback, floor, cap, max-change, relative-vol threshold or reducer after seeing results would overfit.
- `drawdown_contribution_reducer`: Needs a prior-only boundary memo before engineering; historical max drawdown leader cannot be used directly.
