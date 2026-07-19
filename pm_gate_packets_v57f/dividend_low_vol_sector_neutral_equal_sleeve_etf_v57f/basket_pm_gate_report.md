# Basket PM Gate: dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f

- Status: `formal_candidate_pending_platform_exports`
- Blockers: `0`
- Needs review: `3`

## Metrics Snapshot

- local_strategy_return: `0.8141640295000003`
- local_benchmark_return: `0.510118790617593`
- local_excess_return: `0.3040452388824073`
- local_max_drawdown: `0.11748909353603587`
- local_trade_count: `709`
- local_dividend_count: `128`
- formal_signal_count: `19`
- formal_panel_row_count: `3371`
- platform_status: `pending_attribution`

## Checks

- `pass` formal_validation: Formal validation completed with 19 signals.
- `needs_review` weak_year_analysis: Weak years still need monitoring/diagnosis: 2021, 2026.
- `pass` local_daily_simulation: Local daily simulation produced 709 trades.
- `pass` dividend_accounting: Cash dividend accounting applied 128 events.
- `pass` drawdown_control: Max drawdown is 11.75%.
- `pass` overfit_audit: Overfit audit has no blockers.
- `needs_review` overfit_review_items: Overfit audit has 1 review items.
- `pass` ablation: Ablation completed without blocked cases.
- `needs_review` platform_replication: Platform replication is waiting for JoinQuant exports.
- `pass` paper_trading: Paper trading signal exists with 28 selected stocks.

## PM Rules

- Historical performance alone is never sufficient evidence for accepting a strategy.
- Platform replication and clean forward records are required before any acceptance decision.