# V5i Translation Constraints

## 1. V5i Is Execution Research, Not A New Exit Strategy

The existing system first decides that a sell is required and fixes the stock, direction, quantity, and governing event. V5i can evaluate an alternate execution timestamp for that same scheduled sell. It cannot create a sell event, cancel a governing sell, change quantity, add a new buy, or change the selected pool.

For a sell, execution alpha is a positive improvement in realized executable sell price relative to a pre-declared reference execution convention, after costs and non-fill treatment. Predictive alpha is a claim that the technical feature forecasts a future decline or should create a new exit. V5i initial scope allows research on the former only; the latter is blocked.

## 2. PIT And Fill Contract

For any feature at time `t`:

1. Use only bars timestamped at or before `t`.
2. Compute VWAP, high-so-far, RSI, trend state, volume, and amount from observed data only.
3. Execute no earlier than a specified next executable bar after signal formation. Same-bar close fills require an explicit and separately justified fill convention.
4. Keep future outcomes in evaluation columns only, physically separate from feature construction.
5. Do not use final-day high, low, close, VWAP, volume, amount, daily range, or a future rebalance schedule value that was not known at `t`.
6. Preserve raw intraday executable prices separately from adjusted total-return research series; dividends and corporate actions must not be silently applied to intraday sell prices.

## 3. Data Limits

The current V5h data gate covers cleaned 1-minute OHLCV, volume, and amount. It does not provide bid, ask, bid/ask sizes, trade direction, order-book imbalance, cancellation messages, queue position, or actual market impact.

Therefore, V5i may call `amount_pressure` an observed price-and-amount diagnostic. It must not call it net buyer pressure, seller exhaustion, institutional flow, or a liquidity guarantee. Any exact fill, spread, or impact statement remains an execution-assumption scenario until L2 or broker-fill data are supplied.

## 4. Baseline And Measurement Contract

Each research event needs all of the following before a later test:

- Immutable event identifier and original sell reason.
- Original scheduled execution convention and alternate execution convention.
- Feature timestamp, decision timestamp, and earliest eligible fill timestamp.
- Raw price, available volume/amount, suspension/limit-state flags, and assumed costs.
- A positive sell-price improvement sign convention.
- Separate metrics for price improvement, implementation shortfall, non-fill/limit risk, turnover, and cost.
- Results split by year, sleeve, liquidity tier, event family, and pre-2021 versus formal 2021-05-01 to 2026-05-31 scope.

An execution rule does not earn promotion merely because average price improves. It must show that the result is not a small-sample artifact, a single-regime effect, a non-fill artifact, or a result of a more favorable but non-executable price convention.

## 5. V5 Governance Constraints

- V57f repaired baseline remains unchanged.
- V5f mainline remains unchanged.
- V5e profit-lock logic remains unchanged.
- No re-entry before the next formal rebalance.
- No cross-sleeve cash transfer and no cash-proxy purchase.
- No new stock selection, new buy signal, leverage, shorting, or intraday trade-frequency increase.
- No parameter scan, accepted status, live approval, JoinQuant, or QMT activity in this research/spec stage.
- The 2021-05-01 to 2026-05-31 period is formal backtest scope, not a feature-training pool. Pre-2021 work is separate validation and must retain its own data-availability and pool-coverage audit.

## 6. Initial Feature Family Boundary

The only initial feature families suitable for a future fixed-spec review are:

- Price versus observed intraday VWAP.
- Observed trend failure after an intraday rise.
- High-so-far pullback with a next-bar execution contract.
- Observed volume/amount intensity and pressure confirmation.
- RSI or another fixed oscillator as a secondary diagnostic, not a sole trigger.

MACD, visual chart patterns, and any indicator with a threshold selected from 2021-2026 remain blocked pending an independent specification and evidence gate.
