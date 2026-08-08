# V5 Startup Warmup Agent Execution Rules

- Do not modify the original frozen V57f config.
- Do not modify V57f sleeves, factors, weights, caps, target count, or rebalance frequency.
- Use only pre-deployment PIT-visible warmup data for deployment-day factors.
- Do not fabricate missing high_limit, low_limit, paused, or minute bars.
- Do not start JoinQuant, BaoStock, Tushare, or other external data pulls without explicit user authorization.
- Do not mark ERC, L2, L3, L4, or the startup shadow config as accepted.
- Do not start V5e until the startup warmup blocker is resolved and reviewed.
