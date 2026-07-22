# Forward Paper Gate: dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f

- Status: `pending_clean_future_rebalance`
- As of date: `2026-07-21`
- Last recorded signal date: `2026-04-01`
- Last record type: `late_recorded_initialization`
- Next quarter start: `2026-07-01`
- Next rebalance date: `2026-10-08`
- Date source: `manual_override`
- PM gate status: `formal_candidate_paper_tracking_started_needs_review`

## Required Inputs

- Fresh PIT sector panels for all included sleeves, with every row visible on or before the signal generation date.
- Updated daily unadjusted open/close prices through the prior trading day for low-volatility calculation.
- Updated cash dividend files with 20% tax-adjusted net_cash_per_share where applicable.
- Explicit stale-fallback audit for any bank quality field; refreshed PIT bank fundamentals are preferred.
- Trading calendar confirmation for the next rebalance date.

## Execution Rules

- Do not change V5.7f factor weights, sector weights, target count or guards.
- Do not use 2021-2026 platform-confirmation results to tune parameters.
- Generate the paper signal on or before the actual rebalance date, not after the fact.
- Record selected stocks, sleeve weights, factor fields, stale fallback usage and data sources.
- After JoinQuant exports are available, run platform daily/transaction/position attribution before any promotion.

## Blocked Actions

- `accepted_strategy`
- `live_trading_approved`
- `return_tuning`
- `adding_new_sleeves_without_research_pit_validation`

## Command Templates

- `construct_clean_signal`: `python -m v5.cli construct-dividend-low-vol-fcf-basket --config config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_paper_<yyyymm>.json --out paper_trading_signals/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/2026-10-08`
- `run_local_monitoring`: `python -m v5.cli daily-backtest-dividend-low-vol-fcf-basket --config config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_paper_<yyyymm>.json --signals paper_trading_signals/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/2026-10-08/basket_rebalance_signals.csv --out paper_trading_signals/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/2026-10-08/local_monitoring`
- `refresh_pm_gate_after_signal`: `python -m v5.cli basket-pm-gate --strategy-id dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f --formal-summary validation_formal_v57f_etf/<strategy>/basket_formal_validation_summary.json --daily-summary local_daily_backtests_v57f_etf/<strategy>/summary.json --overfit-summary validation_overfit_v57f_etf/<strategy>/overfit_audit_summary.json --ablation-summary validation_ablation_v57f_etf/<strategy>/basket_ablation_summary.json --platform-packet platform_replication_packets_v57f_etf/<strategy>/platform_replication_packet.json --paper-signal-summary paper_trading_signals/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/2026-10-08/basket_construction_summary.json --out pm_gate_packets_v57f`