# V59b Gas/Water State Guard Local Daily Simulation PM Decision

Date: 2026-07-21

## Scope

Engineering Agent only performed local daily simulation for the frozen `gas_water_v57b_text_debt_state_guard_v59b` candidate.

No factor tuning, no parameter tuning, no JoinQuant strategy code, and no platform replication were performed.

## Inputs

- Frozen strategy spec: `examples/gas_water_v57b_text_debt_state_guard_v59b_strategy.json`
- PIT signal panel: `数据库/processed/gas_water_true_operating_state_panel_v59/panel_with_true_operating_state.csv`
- Real unadjusted daily prices: `数据库/processed/gas_water_v57b_joinquant_real_daily_prices.csv`
- Real cash dividends: `数据库/processed/gas_water_v57b_joinquant_cash_dividends.csv`
- Benchmark: `数据库/processed/gas_water_v57b_same_pool_equal_weight_benchmark.csv`

## Outputs

- Packet: `local_daily_backtests_v59b_gas_water_state_guard/gas_water_v57b_text_debt_state_guard_v59b/`
- Daily returns: `daily_returns.csv`
- Holdings: `holdings.csv`
- Trades: `trades.csv`
- Dividends: `dividends.csv`
- Rebalance signals: `rebalance_signals.csv`
- Guard decisions: `guard_decisions.csv`
- Rebalance order health: `rebalance_order_health.csv`
- Summary: `summary.json`

## Result

Status: `engineering_local_daily_simulation_needs_review`

The local daily execution engine generated real daily open/close execution, 20% tax-adjusted cash dividend handling, cash, holdings, trades, guard decisions, and rebalance order health.

Headline metrics for the executed local daily window:

- Strategy return: 33.29%
- Benchmark return: 32.69%
- Excess return: 0.60%
- Max drawdown: 26.55%
- Sharpe: 0.4263

## Order Health

The executed rebalance dates did not show accidental order failure.

- Rebalance signals: 19
- Normal rebalance dates: 13
- Intentional guard cash blocks: 6
- Unexpected rebalance issues: 0
- Missing daily rebalance rows: 0
- First executed order date: 2021-10-08
- First position date: 2021-10-08

Guard-blocked dates are intentional cash-defense dates:

- 2024-04-01
- 2024-10-08
- 2025-01-02
- 2025-10-09
- 2026-01-05
- 2026-04-01

## Blocking Issue

The expected rebalance calendar contains 20 dates, but only 19 generated executable signals.

Skipped date:

- 2021-07-01

Reason:

- The frozen coverage rule requires 80% of max date coverage.
- Max date coverage is 40 securities.
- Required coverage is 32 securities.
- 2021-07-01 only has 28 securities in the PIT panel.

This means the daily engineering simulation does not fully match the formal validation calendar. The issue is a coverage-contract mismatch, not a trade execution bug.

## PM Decision

Do not enter JoinQuant platform replication yet.

Return the specific 2021-07 coverage issue to Research/Quant for one of the following evidence-safe resolutions:

1. Backfill missing 2021-07 PIT gas/water rows with valid visible dates.
2. Freeze a revised formal validation packet that applies the same 80% coverage rule as the daily simulation.
3. Explicitly approve 2021-07 as a documented warm-up / coverage-skip period, then rerun local daily simulation and update the acceptance packet.

Until one of these is completed, V59b remains:

`engineering_local_daily_simulation_needs_review`
