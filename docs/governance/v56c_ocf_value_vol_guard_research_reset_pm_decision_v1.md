# V5.6c OCF Value + Volatility Guard Basket PM Decision V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent, Research Agent, Quant Validation Agent, Engineering Agent
```

Experiment layers:

```text
research_pit_validation
engineering_smoke_test
```

Status:

```text
research_reset_successful
formal_validation_completed_not_acceptance
overfit_audit_no_blockers_needs_review
not_platform_replication
not_paper_trading_ready
not_accepted_strategy
```

## Why V5.6 Was Returned

V5.6 was originally framed as a dividend + low-vol + FCF / low-PB enhanced basket. The evidence did not support that full story:

- `operating_cash_flow_yield` was the strongest stable cash-flow support factor.
- Low-volatility evidence was useful, but better treated as risk control / coverage discipline.
- `low_price_to_book` had weak or negative basket-level evidence.
- `free_cash_flow_yield` had weak incremental contribution and lower usable coverage.

PM therefore returned the low PB / FCF narrative to Research and Quant instead of allowing return-based tuning.

## Research Reset

New main hypothesis:

```text
Stable cash-flow sectors should be ranked primarily by operating cash-flow yield,
while volatility and drawdown act as risk controls and dividend yield supports
shareholder-return discipline.
```

Core score:

| Factor | Role | Weight |
| --- | --- | ---: |
| operating_cash_flow_yield | primary cash-flow value | 0.38 |
| volatility_120d | volatility guard | 0.20 |
| max_drawdown_120d | drawdown guard | 0.18 |
| dividend_yield | shareholder-return support | 0.16 |
| capex_burden | capital-intensity risk | 0.08 |

Excluded from core score:

| Factor | PM treatment |
| --- | --- |
| low_price_to_book | removed from basket mainline |
| free_cash_flow_yield | downgraded to future diagnostic |
| low_vol_score | used as risk / data-coverage gate, not positive alpha score |

## Engineering Fix

During V5.6c testing, Engineering found that the basket constructor renormalized weights after capped selection. When OCF-required candidates selected fewer than 30 names, this could push realized sector weights above the 35% cap.

Fix:

```text
Do not renormalize selected weights after cap-constrained selection. Unallocated weight remains cash.
```

Regression test:

```text
tests/test_basket_constructor_runner.py::test_basket_constructor_does_not_renormalize_past_sector_cap_when_selection_is_short
```

## Local Daily Simulation

Output:

```text
local_daily_backtests_v56c_basket/v56c_ocf_value_vol_guard_basket
```

| Metric | V5.6 | V5.6b | V5.6c |
| --- | ---: | ---: | ---: |
| Strategy return | 74.98% | 77.13% | 86.38% |
| Annualized return | 13.35% | 13.66% | 14.97% |
| Excess return | 23.97% | 26.12% | 35.37% |
| Max drawdown | 13.46% | 12.24% | 13.43% |
| Sharpe | 0.884 | 0.855 | 0.935 |
| Information ratio | 0.308 | 0.393 | 0.542 |

V5.6c is stronger than V5.6 and V5.6b on local same-pool comparison, but this remains 2021-2026 platform-confirmation context.

## Formal Validation

Output:

```text
validation_formal_v56c_basket/v56c_ocf_value_vol_guard_basket
```

PIT candidate panel:

```text
2590 rows
```

Key evidence:

| Evidence | Value |
| --- | ---: |
| Composite mean IC | 0.1047 |
| Composite mean RankIC | 0.1574 |
| Composite positive IC ratio | 73.68% |
| OCF yield mean RankIC | 0.0856 |
| Volatility 120d mean RankIC | 0.1358 |
| Max drawdown 120d mean RankIC | 0.0995 |
| Dividend yield mean RankIC | 0.0803 |
| Capex burden mean RankIC | 0.0393 |

Rolling result:

| Year | Strategy | Benchmark | Excess |
| --- | ---: | ---: | ---: |
| 2021 | 2.61% | -0.74% | 3.34% |
| 2022 | 6.12% | -2.89% | 9.01% |
| 2023 | 10.93% | 4.53% | 6.39% |
| 2024 | 30.47% | 17.65% | 12.82% |
| 2025 | 9.29% | 12.91% | -3.63% |
| 2026 | 8.22% | 12.81% | -4.59% |

## Ablation Read

Output:

```text
validation_ablation_v56c_basket/v56c_ocf_value_vol_guard_basket
```

Common-window result:

- Dropping `operating_cash_flow_yield` reduces return from 86.38% to 58.55%; OCF remains essential.
- Dropping `dividend_yield` reduces return to 81.59%; dividend yield is useful but not the primary driver.
- Dropping `max_drawdown_120d` has a small negative effect.
- Dropping `volatility_120d` raises return slightly but increases drawdown; keep it as a risk guard for now.
- Raising sector cap to 100% raises return but increases concentration risk and is not approved.

## Failure Attribution

Output:

```text
validation_attribution_v56c_basket/v56c_ocf_value_vol_guard_basket
```

2025 and 2026 remain relative weak years:

- 2025 excess return: -3.63%;
- 2026 excess return: -4.59%.

Cash drag is not the cause in the weak years:

- 2025 mean cash weight: 1.18%;
- 2026 mean cash weight: 0.83%.

Main diagnosis:

```text
The basket still misses high-elasticity utilities winners that do not match the OCF / dividend / volatility-guard profile.
This is a style boundary, not a signal failure by itself.
```

## Overfit Audit

Output:

```text
validation_overfit_v56c_basket/v56c_ocf_value_vol_guard_basket
```

Result:

```text
blockers = 0
needs_review = 2
passes = 12
```

Needs review:

- 2021-2026 is still a platform-confirmation window, not clean accepted-strategy evidence.
- Selected count varies between 24 and 30 because OCF + low-vol coverage is stricter.

## PM Decision

Approved:

```text
v56_low_pb_fcf_narrative_rejected
v56c_ocf_value_vol_guard_mainline_selected
v56c_formal_validation_completed_not_acceptance
v56c_overfit_audit_no_blockers_needs_review
v56c_constructor_sector_cap_fix_completed
```

Not approved:

```text
accepted_strategy
platform_replication_passed
paper_trading_ready
live_trading_approved
sector_cap_100_concentration_variant
```

Next gate:

```text
Extend fresh PIT panels beyond 2026-04-01 and start V5.6c forward / paper-trading records.
```

Hard rule:

```text
Historical performance alone is never sufficient evidence for accepting the basket.
```
