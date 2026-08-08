# V5e Daily Momentum Exit Diagnostic Brief

Status: research addendum  
Date: 2026-07-29  
Applies to: V5e holding-period profit-lock / exit diagnostics  
Not an accepted strategy, not a V57f replacement, and not a full-market momentum stock-selection model.

## PM Conclusion

Daily momentum is a reasonable diagnostic lens for V5e because it can test whether profit-lock exits are selling medium-term winners too early. It must remain inside the V57f/V5e value, dividend, low-volatility and sleeve-selected pool. It cannot add new stocks, change V57f selection, change sleeve weights, or become a standalone alpha model.

## Research Boundary

Allowed pool:

- V57f repaired baseline historical holdings.
- V5e-affected V57f holdings.
- If candidate-layer diagnostics are needed, only the V57f point-in-time candidate pool that already passed the original value/dividend/low-volatility/sleeve filters.

Blocked uses:

- Full-market momentum selection.
- Adding a stock because momentum is strong.
- Removing a stock permanently from the V57f pool because momentum is weak.
- Reentry before the next V57f official rebalance.
- Threshold search using 2021-05-01 to 2026-05-31 results.
- Treating a diagnostic return spread as acceptance.

## Theory Notes

Intermediate-horizon momentum has academic support as a tendency for recent winners to continue for a while. In V5, this is not enough to make momentum a primary factor because V57f is built around dividend sustainability, operating cash-flow quality, valuation discipline, low volatility and industry sleeve construction.

The clean V5e use case is narrower:

- If a stock has already been selected by V57f and has already reached a profit-lock state, daily momentum can diagnose whether selling immediately tends to miss further trend continuation.
- If daily momentum is weak after a profit-lock trigger, it can diagnose whether the existing exit is protecting gains.
- If evidence is mixed, momentum should remain a failure-attribution tool, not a trading rule.

## Preferred Diagnostic Features

Use fixed, pre-registered daily features:

- `ret_5d`: prior 5 trading-day return, visible after the prior close.
- `ret_10d`: prior 10 trading-day return, visible after the prior close.
- `ret_20d`: prior 20 trading-day return, visible after the prior close.
- `ret_60d`: prior 60 trading-day return, visible after the prior close.
- `ret_20d_vs_sleeve_mean`: stock 20-day return minus same-sleeve V57f holding mean 20-day return.
- `ret_20d_vs_portfolio_holding_mean`: stock 20-day return minus V57f holding mean 20-day return.
- `above_ma20`: previous close above trailing 20-day moving average.
- `above_ma60`: previous close above trailing 60-day moving average.

These are diagnostic features only. They are not a parameter grid and must not be chosen by historical performance.

## Daily Momentum Hypothesis Map

| Hypothesis | Diagnostic question | Expected use | Promotion limit |
| --- | --- | --- | --- |
| `H1_continuation_after_profit_lock` | After a V5e profit-lock trigger, do high daily-momentum stocks keep rising over the next 5/10/20/60 trading days? | Identify possible early sale of winners. | Counterfactual only unless a separate Quant spec is approved. |
| `H2_weak_momentum_confirms_exit` | After a V5e profit-lock trigger, do weak daily-momentum stocks underperform after the exit date? | Explain when immediate exit is risk-protective. | Does not create a new stop rule. |
| `H3_all_held_stock_noise_check` | Does daily momentum work across all V57f held stock-days, or only around V5e exits? | Separate broad held-pool effect from exit-specific effect. | Held-pool effect cannot become full-market selection. |
| `H4_sleeve_relative_trend` | Is momentum stronger when measured relative to same-sleeve holdings? | Diagnose sleeve-specific continuation or reversal. | Does not alter sleeve weights or ERC. |

## Allowed Pool And PIT Contract

The allowed pool is fixed before any momentum calculation:

- Use V57f repaired historical holdings for held-stock-day diagnostics.
- Use V5e historical exit actions for trigger-overlay diagnostics.
- Use V57f PIT candidate pools only if a later spec explicitly requires candidate-layer diagnostics.

The PIT contract is:

- A daily momentum feature observed on date `T` uses close data through `T` only when the hypothetical decision is after `T` close and execution is no earlier than `T+1`.
- If an execution assumption uses `T` open, the feature must use data only through `T-1` close.
- Forward 5/10/20/60-day returns and until-next-rebalance returns are labels, never signal inputs.
- The same historical window cannot be used to choose a new threshold, new lookback, or new stock pool.

## Exit Delay Counterfactual Design

The clean V5e counterfactual is not "buy more winners." It is:

- Existing V5e profit-lock rule triggers.
- Daily momentum state is measured using the fixed feature set.
- Diagnostic asks whether the sold fraction would have done better if held for a fixed evaluation window.
- The output is value-attribution only: `missed_gain`, `avoided_loss`, or `mixed`.

This design can show whether V5e sometimes sells winners early, but it does not authorize delayed execution. Any delayed-sell rule needs a separate Quant spec with its own PIT, T+1, cash, reentry and NAV checks.

## PIT Rule

For any decision date `T`, daily momentum features must use prices through `T-1` close if the simulated action would occur at `T` open, or through `T` close only if the action is explicitly after close and execution is `T+1`.

Forward returns are evaluation labels only. They cannot be used to choose windows, thresholds, rebalance timing, or candidate stocks.

## Quant Validation Requirements

- State price adjustment and dividend treatment.
- Report by feature and by pre-registered bucket: positive, neutral, negative; top, middle, bottom tercile for diagnostics only.
- Report forward 5/10/20/60 trading-day returns and until-next-rebalance return.
- Separate V5e trigger events from all held stock-days.
- Test whether positive momentum after V5e trigger means delayed selling would have helped.
- Test whether negative momentum after V5e trigger means immediate sell protection was useful.
- Run NAV-level comparison only as a diagnostic proxy, not as acceptance.

## Expected Decision Labels

Allowed:

- `diagnostic_only_no_trading_value`
- `diagnostic_positive_but_nav_failed`
- `diagnostic_positive_ready_for_separate_quant_spec_not_accepted`

Blocked:

- `accepted`
- `live_approved`
- `V57f replacement`
- `best momentum strategy by historical return`
- `optimized threshold`
- `new buy signal`

## Decision Labels And Non-Acceptance Rules

Daily momentum can only change the research queue:

- If held-stock-day and exit-event evidence are both weak, close as `diagnostic_only_no_trading_value`.
- If exit-event evidence is positive but portfolio/NAV evidence fails, label `diagnostic_positive_but_nav_failed`.
- If event evidence is stable and NAV evidence is not contradicted, it may become `diagnostic_positive_ready_for_separate_quant_spec_not_accepted`.

It cannot directly change:

- V57f selected stocks.
- V57f target weights.
- V57f rebalance calendar.
- V5e profit-lock threshold or sell fraction.
- V5e accepted/live status.
