# V5.6 Basket Formal Validation + Overfit Audit PM Decision V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent, Quant Validation Agent, Engineering Agent
```

Experiment layers:

```text
research_pit_validation
engineering_smoke_test
```

Status:

```text
formal_validation_completed_not_acceptance
overfit_audit_no_blockers_needs_review
local_daily_simulation_completed
not_platform_replication
not_paper_trading_ready
not_accepted_strategy
```

## Purpose

This step repairs the two V5.6 basket data gaps before running basket-level validation:

- Bank V3 real daily open/close prices;
- Utilities/electricity real cash-dividend events.

Then it runs:

- cross-sector basket signal reconstruction;
- local JoinQuant-like daily simulation;
- basket-level formal validation;
- Engineering Agent overfit audit.

## Data Repair

| Dataset | Result |
| --- | ---: |
| Bank V3 real daily stock prices | 51,576 rows |
| Bank V3 512800 benchmark prices | 1,228 rows |
| Bank V3 cash dividends / stock actions | 265 events |
| Utilities cash dividends | 549 events |
| Highway cash dividends / stock actions | 102 events |
| Port / rail cash dividends / stock actions | 130 events |

Cash dividends use:

```text
net_cash_per_share = cash_per_share * (1 - 20% tax)
```

Stock dividends and transfer shares are now handled as share-position adjustments on ex-date.

## Basket Scope

| Sleeve | Status |
| --- | --- |
| Bank V3 | included after real daily price repair |
| Utilities / electricity V5.1f | included after dividend repair |
| Highway infrastructure V5.4h | included |
| Port / rail infrastructure V5.5j | included |

Basket constructor output:

```text
validation_formal_v56_basket_constructor/basket_rebalance_signals.csv
```

Signal dates:

```text
19
```

Holding signals:

```text
570
```

## Local Daily Simulation

Output:

```text
local_daily_backtests_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

Metrics:

| Metric | Value |
| --- | ---: |
| Strategy return | 74.98% |
| Annualized return | 13.35% |
| Same-pool benchmark return | 51.01% |
| Excess return | 23.97% |
| Max drawdown | 13.46% |
| Sharpe | 0.884 |
| Information ratio | 0.308 |
| Strategy volatility | 15.56% |
| Benchmark volatility | 17.63% |
| Dividend cash events credited | 144 |
| Stock dividend / transfer actions credited | 1 |

## Formal Validation

Output:

```text
validation_formal_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

Combined PIT candidate panel:

```text
3343 rows
```

Key evidence:

| Evidence | Result |
| --- | ---: |
| Composite mean IC | 0.0729 |
| Composite mean RankIC | 0.1102 |
| Composite positive IC ratio | 63.16% |
| Low-vol mean RankIC | 0.1418 |
| Operating cash-flow yield mean RankIC | 0.0856 |
| Dividend yield mean RankIC | 0.0208 |
| Low PB mean RankIC | -0.1346 |

Rolling result:

| Year | Strategy | Benchmark | Excess |
| --- | ---: | ---: | ---: |
| 2021 | 2.41% | -0.78% | 3.19% |
| 2022 | 2.51% | -4.05% | 6.56% |
| 2023 | 13.19% | 3.79% | 9.40% |
| 2024 | 25.12% | 16.51% | 8.62% |
| 2025 | 8.09% | 12.61% | -4.52% |
| 2026 | 7.89% | 12.64% | -4.75% |

PM interpretation:

```text
The basket improves return and drawdown versus the same-pool benchmark in 2021-2024,
but underperforms in 2025-2026. Low-vol and operating cash-flow yield currently carry
more statistical support than low PB or raw dividend yield.
```

## Overfit Audit

Output:

```text
validation_overfit_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

Result:

```text
status = needs_review
blockers = 0
needs_review = 1
passes = 13
```

The only needs-review item is intentional governance:

```text
2021-05 to 2026-05 is platform-confirmation context, not clean OOS acceptance evidence.
```

Passed checks include:

- PIT universe flag;
- visible-date leakage audit;
- full-sample normalization guard;
- factor as-of policy;
- accepted-strategy marker guard;
- random-window stability;
- execution timing shift proxy;
- parameter perturbation contract;
- selected-count stability.

## Basket Ablation

Output:

```text
validation_ablation_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

The ablation runner now re-runs real basket construction and local daily simulation for every case. It also reports a common-window comparison from 2021-10-08 to 2026-05-29, avoiding false conclusions from earlier-starting variants.

Common-window observations:

| Case | Strategy return | Excess return | Max drawdown | PM interpretation |
| --- | ---: | ---: | ---: | --- |
| base | 74.98% | 23.97% | 13.46% | Current frozen shadow basket |
| sector_cap_100 | 92.89% | 41.88% | 13.73% | Higher concentration; needs exposure review |
| value_cashflow_no_low_vol | 86.91% | 34.81% | 14.06% | Better return, but weakens low-vol mandate |
| drop_low_price_to_book | 83.71% | 32.70% | 11.10% | Low PB currently appears to drag basket evidence |
| drop_operating_cash_flow_yield | 56.59% | 5.58% | 12.70% | OCF is a key support factor |

PM interpretation:

```text
V5.6 should be described as low-volatility + operating cash-flow + stable cash-flow asset basket.
It should not yet be described as a proven low-PB / FCF-enhanced dividend ETF proxy.
```

## 2025 / 2026 Failure Attribution

Output:

```text
validation_attribution_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

Yearly attribution:

| Year | Strategy | Same-pool benchmark | Excess | Main local explanation |
| --- | ---: | ---: | ---: | --- |
| 2025 | 8.10% | 12.91% | -4.82% | Highway sleeve and selected port / rail names lagged |
| 2026 | 7.89% | 12.81% | -4.92% | Bank sleeve lagged; some high-beta utilities were missed |

Cash drag check:

```text
2025 mean cash weight = 1.31%; max cash weight = 2.19%
2026 mean cash weight = 0.88%; max cash weight = 1.03%
```

PM interpretation:

```text
The 2025-2026 underperformance is not caused by cash idling. It is mainly a style trade-off:
the basket favors dividend / low-vol / stable OCF names and intentionally misses non-dividend,
high-elasticity utility winners. This is a model boundary, not an immediate reason to tune returns.
```

## PM Decision

Approved:

```text
v56_bank_data_repair_completed
v56_utilities_dividend_repair_completed
v56_basket_formal_validation_completed
v56_overfit_audit_no_blockers_needs_review
v56_cash_dividend_and_stock_action_ledger_completed
v56_true_basket_ablation_completed_common_window_required
v56_2025_2026_failure_attribution_completed
```

Not approved:

```text
accepted_strategy
platform_replication_passed
paper_trading_ready
live_trading_approved
accepted_low_pb_fcf_enhanced_etf_proxy
```

Next gate:

```text
v56_basket_forward_paper_trading_design_or_factor_research_reset
```

Hard rule:

```text
Historical performance alone is never sufficient evidence for accepting the basket.
```
