# V59b Gas/Water PM Gate After Repaired Local Daily Simulation

Date: 2026-07-21

## Decision Context

The repaired local daily simulation for `gas_water_v57b_text_debt_state_guard_v59b` has passed Engineering.

Confirmed:

- 2021-07-01 PIT coverage was repaired from 28 to 32 securities.
- All 20 expected rebalance dates generated signals.
- First executed order date was 2021-07-01.
- First position date was 2021-07-01.
- Unexpected rebalance order issues: 0.
- Intentional guard cash-block dates: 7.
- Real daily open/close prices and cash dividends were used.

Key evidence:

- `docs/governance/v59b_gas_water_2021_07_pit_coverage_repair_pm_decision_v1.md`
- `docs/governance/v59b_gas_water_repaired_local_daily_simulation_pm_decision_v1.md`
- `local_daily_backtests_v59b_gas_water_state_guard_repaired_2021_07/gas_water_v57b_text_debt_state_guard_v59b/summary.json`

## Gate Decision

PM decision:

`start_paper_trading_preparation`

Do not enter JoinQuant platform replication in this step.

Reason:

The user asked to continue after local Engineering passed, but did not explicitly approve platform replication or JoinQuant code generation. The safer next layer is forward / paper-trading preparation, because it preserves V5 discipline without turning a local engineering result into a deployment claim.

## Allowed

- Open a forward / paper-trading log.
- Prepare the next clean future rebalance checklist.
- Record required PIT inputs for the next signal.
- Record that 2026-07 is not clean forward evidence because this PM gate is dated 2026-07-21.
- Wait for the next clean future rebalance window.

## Blocked

- JoinQuant code generation.
- JoinQuant platform replication.
- Retuning factor weights, guard thresholds, selection count, rebalance months, or coverage threshold.
- Accepted strategy status.
- Live trading approval.

## Next Clean Rebalance

Expected next clean rebalance window:

`2026-10-08` subject to final A-share trading-calendar confirmation.

This date must be confirmed before signal generation. If the actual exchange calendar differs, the first valid trading day of the quarter should be used.

## Required Before First Paper Signal

- Refresh PIT gas/water universe as of the signal date.
- Refresh latest visible financial fields using notice-date / trade-date visibility rules.
- Refresh true operating-state text evidence only if the source documents are visible before the signal date.
- Refresh real daily prices through the previous trading day.
- Refresh cash dividend events and 20% tax-adjusted `net_cash_per_share`.
- Generate the signal on or before the rebalance date.
- Save selected codes, factor fields, guard decision, coverage, expected weights, and data sources.

## Status

`paper_trading_preparation_started_not_platform_replication`
