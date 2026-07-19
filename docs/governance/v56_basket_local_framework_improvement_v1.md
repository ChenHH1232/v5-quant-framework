# V5.6 Basket Local Framework Improvement V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent, Quant Validation Agent, Engineering Agent
```

Status:

```text
local_framework_improved
not_platform_replication
not_accepted_strategy
```

## Completed Improvements

1. Local daily simulation now supports both cash dividends and stock dividends / transfer shares.
2. Basket same-pool benchmark now includes available cash dividends and stock-action total-return adjustment.
3. True basket ablation now re-runs basket construction and daily simulation for every case.
4. Ablation output now includes common-window metrics, using the base case window from 2021-10-08 to 2026-05-29.
5. Failure attribution runner now produces 2025 / 2026 diagnostics from local daily returns, signals, prices, dividends and stock actions.
6. Test coverage was added for the failure attribution runner and updated for stock-action handling.

## Latest Local Daily Result

Output:

```text
local_daily_backtests_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

| Metric | Value |
| --- | ---: |
| Strategy return | 74.98% |
| Annualized return | 13.35% |
| Same-pool benchmark return | 51.01% |
| Excess return | 23.97% |
| Max drawdown | 13.46% |
| Sharpe | 0.884 |
| Information ratio | 0.308 |
| Dividend events credited | 144 |
| Stock-action events credited | 1 |

## Ablation Read

Output:

```text
validation_ablation_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

Common-window evidence says:

- `operating_cash_flow_yield` is important: dropping it reduces strategy return from 74.98% to 56.59%.
- `free_cash_flow_yield` is not yet decisive in the current data: dropping it changes return only slightly.
- `low_price_to_book` is currently a drag in this basket layer: dropping it improves return and drawdown in the 2021-2026 confirmation window.
- `sector_cap_100` looks stronger but increases concentration risk, so it cannot be accepted without exposure and robustness review.
- `value_cashflow_no_low_vol` is stronger than base on the common window, but it weakens the low-volatility mandate and must be treated as a research reset candidate, not an automatic upgrade.

## Failure Attribution Read

Output:

```text
validation_attribution_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

The 2025 and 2026 underperformance is not caused by idle cash:

- 2025 mean cash weight: 1.31%;
- 2026 mean cash weight: 0.88%.

Main local diagnosis:

- 2025 weakest selected sleeve: `highway_infrastructure`;
- 2026 weakest selected sleeve: `bank`;
- The basket missed several high-elasticity utilities names that did not fit the dividend / low-vol / stable OCF profile.

## PM Decision

Approved:

```text
v56_local_company_action_ledger_completed
v56_true_basket_ablation_completed
v56_common_window_ablation_policy_completed
v56_2025_2026_failure_attribution_completed
```

Not approved:

```text
accepted_strategy
platform_replication_passed
paper_trading_ready
low_pb_fcf_enhanced_etf_proxy_claim
```

Next action:

```text
Do not tune on 2021-2026 returns. Either start basket paper-trading records, or send the low-PB / FCF narrative back to Research and Quant for a clean hypothesis reset.
```
