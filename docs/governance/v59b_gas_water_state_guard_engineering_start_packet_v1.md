# V5.9b Gas / Water State Guard Engineering Start Packet

Date: 2026-07-21

Strategy id: `gas_water_v57b_text_debt_state_guard_v59b`

Decision: `engineering_can_start_local_daily_simulation`

## PM Conclusion

Gas / water can now enter the Engineering Agent stage for local daily simulation.

This is not acceptance, not JoinQuant code approval, and not platform replication. The next action is only to check whether the frozen research logic can be reproduced under daily execution constraints.

## Frozen Logic

Base selector:

`gas_water_value_serviceability_v57b`

Added defensive layer:

- Field: `true_financing_debt_density_per_10k`
- Source: latest visible CNINFO annual / semiannual report PDF text
- PIT rule: report `visible_date <= rebalance_date`
- Guard rule: block new equity exposure when current value is above its own expanding historical 75th percentile
- Minimum history: `8` rebalance observations
- Defensive asset: cash

Frozen spec:

`examples/gas_water_v57b_text_debt_state_guard_v59b_strategy.json`

## Evidence

True operating-state evidence:

`research_reports/gas_water_true_operating_state_v59_history_2020_2025/gas_water_true_operating_state_candidates.csv`

PIT panel:

`DATABASE_DIR/processed/gas_water_true_operating_state_panel_v59/panel_with_true_operating_state.csv`

Text operating-state diagnostic:

`validation_formal_v59_gas_water_true_operating_state/gas_water_true_operating_state_diagnostic_v59/formal_validation_summary.json`

State guard validation:

`validation_state_v59_gas_water_true_operating_guard/gas_water_v57b_text_debt_state_guard_v59b/state_guard_validation_packet.json`

## Quant Evidence Summary

Base V57b on true-state panel:

- cumulative return: `90.09%`
- 2026 return: `-9.60%`
- positive period ratio: `75%`

V59b primary state guard:

- cumulative return: `90.60%`
- 2026 return: `0.00%`
- blocked periods: `7 / 20`
- positive period ratio: `50%`

Robustness:

- Same guard field at 67%, 75%, and 80% expanding thresholds all keeps 2026 non-negative.
- Same guard field has no major cumulative-return damage versus base V57b.
- Receivables text guard and sector receivables state also block 2026, but they reduce participation more heavily.

## Why Engineering Can Start

The guard is ex-ante:

- It uses only prior rebalance history for the expanding percentile.
- It uses only reports visible before the rebalance date.
- It does not change the V57b stock scoring weights.
- It addresses the specific 2026 failure mode without direct return tuning.

## Engineering Task

Engineering Agent should now run local daily simulation only:

1. Reproduce V57b stock selection.
2. Apply the V59b state guard before each rebalance.
3. Use real daily open / close execution data where available.
4. Include true cash dividend handling.
5. Output daily NAV, cash, holdings, transactions and rebalance order health.
6. Confirm whether guard-blocked rebalance dates produce intentional no-order / cash behavior.

## Hard Blocks

- Do not write JoinQuant strategy code yet.
- Do not tune the guard threshold.
- Do not use 2021-2026 platform results to change weights.
- Do not promote to `platform_replication` until local daily simulation and rebalance order health pass.

## Next Gate

`engineering_local_daily_simulation`
