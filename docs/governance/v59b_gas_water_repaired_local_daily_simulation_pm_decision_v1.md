# V59b Gas/Water Repaired Local Daily Simulation PM Decision

Date: 2026-07-21

## Scope

Engineering reran the local daily simulation for the frozen `gas_water_v57b_text_debt_state_guard_v59b` candidate using the repaired 2021-07 PIT panel.

No factor tuning, guard threshold tuning, selection-count tuning, JoinQuant code generation, or platform replication was performed.

## Inputs

- Frozen spec: `examples/gas_water_v57b_text_debt_state_guard_v59b_strategy.json`
- Repaired PIT panel: `数据库/processed/gas_water_2021_07_pit_repair_v59b/panel_with_true_operating_state_repaired_2021_07.csv`
- Real unadjusted daily prices: `数据库/processed/gas_water_v57b_joinquant_real_daily_prices.csv`
- Real cash dividends: `数据库/processed/gas_water_v57b_joinquant_cash_dividends.csv`
- Benchmark: `数据库/processed/gas_water_v57b_same_pool_equal_weight_benchmark.csv`

## Outputs

Packet:

`local_daily_backtests_v59b_gas_water_state_guard_repaired_2021_07/gas_water_v57b_text_debt_state_guard_v59b/`

Key files:

- `summary.json`
- `daily_returns.csv`
- `holdings.csv`
- `trades.csv`
- `dividends.csv`
- `rebalance_signals.csv`
- `guard_decisions.csv`
- `rebalance_coverage_audit.csv`
- `rebalance_order_health.csv`

## Result

Status: `engineering_local_daily_simulation_passed_ready_for_platform_preparation`

Metrics:

- Strategy return: 76.49%
- Annualized return: 12.36%
- Benchmark return: 32.69%
- Excess return: 43.79%
- Max drawdown: 24.39%
- Sharpe: 0.7172

## Coverage Health

- Expected rebalance dates: 20
- Executed signal dates: 20
- Coverage-skipped dates: 0
- 2021-07-01 coverage: 32 / 40
- Required coverage: 32 / 40

The previous 2021-07 coverage blocker is resolved.

## Order Health

- Rebalance signal count: 20
- Normal rebalance dates: 13
- Intentional guard cash blocks: 7
- Unexpected rebalance issues: 0
- Missing daily rebalance rows: 0
- First executed order date: 2021-07-01
- First position date: 2021-07-01

Guard-blocked dates:

- 2023-07-03
- 2024-04-01
- 2024-10-08
- 2025-01-02
- 2025-10-09
- 2026-01-05
- 2026-04-01

The additional 2023-07-03 guard block is expected because the repaired 2021-07 signal adds one earlier point to the expanding-history guard sequence. This is not parameter tuning.

## PM Decision

The repaired local daily simulation passed the Engineering gate.

Allowed next state:

`engineering_local_daily_simulation_passed`

Still not allowed without a separate PM gate:

- JoinQuant code generation
- JoinQuant platform replication
- accepted strategy status
- live trading

Next gate:

`pm_decide_platform_preparation_or_paper_trading_only`
