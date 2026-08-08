# Rejected Or Unsafe V5c Ideas

## Rejected

- Use 2021-2026 to search the best drawdown threshold.
- Use the 2024-09-24 rebound to design an exit or re-entry date.
- Convert Xueqiu or blog profit-taking habits directly into rules.
- Use book principles as numeric parameters.
- Add gas/water, telecom, home appliances or any observation sleeve to V57f core.
- Change V57f stock selection, factor weights, sleeve weights, rebalance frequency or execution timing.
- Use minute-level timing or intraday trend signals.
- Use leverage, options or shorting.
- Use current ETF holdings to explain or reconstruct historical exposure.
- Replace cash with another asset without a separate PM asset-eligibility and benchmark policy.

## Unsafe Unless Reworked

- Macro forecast models with many variables: likely overfit and hard to keep PIT-safe.
- Multi-parameter defensive overlays: too easy to fit to 2021-2026.
- Stock-level stop profit / stop loss: conflicts with ETF-like low-turnover sleeve logic.
- Discretionary recovery after a defensive cut: creates untestable manual timing.
- Full cash exits after every drawdown: may create severe cash drag and missed rebounds.

## Safe Direction

Prefer simple, pre-registered, portfolio-level overlays with observable PIT data:

- portfolio drawdown state;
- broad-market trend state;
- realized volatility state;
- sleeve drift / risk-budget rebalancing;
- dividend and cash-flow safety state;
- explicit cash restoration rule.
