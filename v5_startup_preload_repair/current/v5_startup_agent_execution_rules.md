# V5 Startup Preload Agent Execution Rules

1. Do not modify V57f core sleeves, factors, weights, target count, sector cap, single-stock cap, or regular rebalance frequency.
2. Do not use data after deployment_date to compute deployment-day signals.
3. Warmup data may be loaded before deployment_date only for PIT-visible factor computation.
4. If required PIT fields are unavailable on first_tradable_date, block initial_rebalance_event instead of fabricating signals.
5. Do not silently lift backtest start_date to first_signal_date.
6. ERC/L2/L3/L4 must read the repaired signal schedule when it exists, but remain not accepted.
7. V5b remains sidecar/data-gate only.
8. V5e must not start until startup preload blockers are resolved.
