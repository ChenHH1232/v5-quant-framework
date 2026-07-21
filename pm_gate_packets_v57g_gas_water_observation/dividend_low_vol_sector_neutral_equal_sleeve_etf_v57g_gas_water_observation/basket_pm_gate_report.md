# Basket PM Gate: dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation

- Status: `formal_candidate_needs_pm_review`
- Blockers: `0`
- Needs review: `5`

## Metrics Snapshot

- local_strategy_return: `0.7006712184799968`
- local_benchmark_return: `0.5300706121547445`
- local_excess_return: `0.1706006063252523`
- local_max_drawdown: `0.12149194663011453`
- local_trade_count: `709`
- local_dividend_count: `130`
- formal_signal_count: `19`
- formal_panel_row_count: `4089`
- platform_status: `None`

## Checks

- `pass` formal_validation: Formal validation completed with 19 signals.
- `needs_review` weak_year_analysis: Weak years still need monitoring/diagnosis: 2021, 2026.
- `pass` local_daily_simulation: Local daily simulation produced 709 trades.
- `pass` rebalance_order_health: All 19 rebalance signals have executable order/holding evidence; first order=2021-10-08, first position=2021-10-08.
- `pass` dividend_accounting: Cash dividend accounting applied 130 events.
- `pass` drawdown_control: Max drawdown is 12.15%.
- `pass` overfit_audit: Overfit audit has no blockers.
- `needs_review` overfit_review_items: Overfit audit has 1 review items.
- `needs_review` ablation: Ablation has blocked cases: drop_div_yield_decimal, drop_low_vol_score, value_cashflow_no_low_vol.
- `needs_review` platform_replication: Platform replication packet is missing.
- `needs_review` paper_trading: Paper trading signal summary is missing.

## PM Rules

- Historical performance alone is never sufficient evidence for accepting a strategy.
- Platform replication and clean forward records are required before any acceptance decision.