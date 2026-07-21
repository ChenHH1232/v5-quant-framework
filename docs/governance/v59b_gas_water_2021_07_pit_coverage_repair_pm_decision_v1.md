# V59b Gas/Water 2021-07 PIT Coverage Repair PM Decision

Date: 2026-07-21

## Scope

This repair only addresses the 2021-07-01 PIT universe coverage-contract gap found during local daily simulation.

No factor weights, guard threshold, selection count, execution rule, or JoinQuant code was changed.

## Problem

The frozen daily simulation required 80% rebalance-date coverage.

- Max date coverage: 40 securities
- Required 80% coverage: 32 securities
- Original 2021-07-01 coverage: 28 securities

Therefore the local daily simulation skipped 2021-07-01 and first entered positions on 2021-10-08.

## Repair Method

Research/Quant repaired only rows that had evidence visible no later than 2021-07-01.

2021 semiannual reports and later evidence were not used.

The repair used:

- Source PIT industry panel: `数据库/processed/similar_sector_pit_panel_v55/gas_water_operators/panel.csv`
- Current true operating-state panel: `数据库/processed/gas_water_true_operating_state_panel_v59/panel_with_true_operating_state.csv`
- CNINFO annual report text evidence: `research_reports/gas_water_true_operating_state_v59_history_2020_2025/gas_water_true_operating_state_candidates.csv`
- Eastmoney segment evidence where available: `数据库/processed/gas_water_operating_evidence_v57/gas_water_segment_business_evidence_eastmoney.csv`

## Repair Output

- Repaired panel: `数据库/processed/gas_water_2021_07_pit_repair_v59b/panel_with_true_operating_state_repaired_2021_07.csv`
- Repair audit: `数据库/processed/gas_water_2021_07_pit_repair_v59b/repair_audit_2021_07.csv`
- Repair manifest: `数据库/processed/gas_water_2021_07_pit_repair_v59b/repair_manifest_2021_07.json`

Added codes:

- `600008.XSHG`
- `600461.XSHG`
- `600635.XSHG`
- `601139.XSHG`

Excluded codes:

- `000421.XSHE`
- `000605.XSHE`
- `000685.XSHE`
- `600642.XSHG`
- `603393.XSHG`
- `603689.XSHG`
- `603706.XSHG`

Reason for exclusions:

The excluded names either lacked original visible segment evidence before 2021-07-01, or their latest visible evidence showed property, heat, engineering, coal/power, upstream coalbed gas, long-distance pipeline, or other non-core exposure dominating the business.

## Coverage Result

After repair:

- 2021-07-01 coverage: 32 securities
- Required coverage: 32 securities
- Coverage status: passed

Signal-layer check:

- Rebalance signal count: 20
- First signal date: 2021-07-01
- 2021-07-01 selected count: 10

## Quant Recheck

The state-guard validation was rerun on the repaired panel.

Validation packet:

`validation_state_v59b_gas_water_true_operating_guard_repaired_2021_07/gas_water_v57b_text_debt_state_guard_v59b/state_guard_validation_packet.json`

Result:

- Base V57b cumulative return: 84.53%
- V59b state guard cumulative return: 85.02%
- Base 2026 return: -9.60%
- V59b 2026 return: 0.00%
- Blocked periods: 7 / 20
- Status: `engineering_can_start_local_daily_simulation`

Important change:

Adding the 2021-07-01 rebalance point changes the expanding history. The guard now also blocks `2023-07-03`. This is expected from the PIT repair and is not parameter tuning.

## PM Decision

The 2021-07 coverage-contract blocker is repaired.

V59b may return to Engineering for local daily simulation using the repaired panel.

Still prohibited:

- No factor tuning.
- No guard threshold tuning.
- No JoinQuant code.
- No platform replication.

Next gate:

`engineering_local_daily_simulation_on_repaired_panel`
