# V5c Sleeve-Level Risk Attribution

This packet reconstructs daily sleeve returns and PnL for the frozen V57f core. It does not modify V57f and does not test a new overlay.

## Status

- Baseline: `dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f`
- Window: `{'start_date': '2021-05-01', 'end_date': '2026-05-31'}`
- V57f core modified: `False`
- Risk budget readiness: `blocked_before_risk_budget_overlay`
- Aggregation max return gap: `0.005841397135`

## Sleeve Metrics

| Sleeve | Local return | Local volatility | Max drawdown | Corr with V57f | Avg weight |
|---|---:|---:|---:|---:|---:|
| bank | 64.91% | 15.19% | 13.91% | 0.7252 | 24.62% |
| utilities_electricity | 184.71% | 23.53% | 25.82% | 0.8063 | 24.63% |
| highway_infrastructure | 106.71% | 19.16% | 19.29% | 0.8508 | 23.62% |
| port_rail_infrastructure | 82.56% | 20.38% | 21.94% | 0.8490 | 24.75% |

## Risk Contribution

| Sleeve | Standalone vol risk share | Contribution vol risk share | Covariance risk contribution |
|---|---:|---:|---:|
| bank | 19.41% | 19.54% | 17.53% |
| utilities_electricity | 30.07% | 30.55% | 30.18% |
| highway_infrastructure | 24.49% | 23.45% | 24.62% |
| port_rail_infrastructure | 26.03% | 26.46% | 27.66% |

## Official Max Drawdown Contribution

| Sleeve | PnL contribution | Share |
|---|---:|---:|
| bank | -11610.9380 | 5.13% |
| utilities_electricity | -89617.5538 | 39.59% |
| highway_infrastructure | -69398.2347 | 30.66% |
| port_rail_infrastructure | -55735.8701 | 24.62% |

## Readiness

- `daily_sleeve_returns_complete`: `pass` - All four core sleeve return columns are present.
- `sleeve_mapping_auditable`: `pass` - Mapping uses rebalance_signals sector_id plus carried position sector.
- `aggregation_consistent_with_v57f`: `blocked` - {"max_abs_return_gap": 0.005841397134556678, "max_abs_value_gap": 0.0}
- `drawdown_contribution_explainable`: `blocked` - Official V57f drawdown interval can be decomposed by sleeve PnL.
- `ready_for_fixed_rule_risk_budget_spec`: `blocked` - Allowed next step is fixed-rule Quant spec only; no parameter search.

## Still Blocked

- `sleeve_level_attribution_readiness`: One or more sleeve attribution readiness checks failed.
- `dividend_safety_and_fcf_ocf_reducer_engineering`: Still requires PIT dividend announcement dates and financial statement lag contracts.
- `valuation_and_crowding_overheat_engineering`: Still lacks audited PIT valuation percentile and crowding datasets.
- `risk_budget_parameter_search`: Sweeping windows, caps or risk budgets against 2021-2026 would overfit.
