# Agent Loop Packet: checkpoint_packet

- Objective: v58g_oil_gas_core_source_repaired_formal_validation
- Agent: `Project Manager Agent`
- Experiment layer: `research_pit_validation`
- Timebox: `30 minutes`
- Decision: `return_to_research`
- Next owner: `Research Agent`
- Stop rule status: `not_triggered`
- User decision required: `False`

## Artifacts

- `src/v5/oil_gas_source_gate_runner.py`
- `src/v5/oil_gas_state_conditioned_panel_runner.py`
- `examples/oil_gas_state_conditioned_ocf_v58g_strategy.json`
- `数据库/processed/oil_gas_source_gate_v58e/oil_gas_tushare_futures_state_v58g.csv`
- `数据库/processed/oil_gas_source_gate_v58e/oil_gas_official_state_formal_candidate.csv`
- `数据库/processed/oil_gas_state_conditioned_panel_v58g/oil_gas_state_conditioned_ocf_v58g/panel.csv`
- `validation_formal_v58g_oil_gas/oil_gas_state_conditioned_ocf_v58g/formal_validation_summary.json`
- `docs/governance/v58g_oil_gas_core_source_repaired_validation_pm_decision_v1.md`

## Evidence

- Core source gate repaired: crude, bitumen, gas/liquid and refining-spread proxy cover 18/18 V5.8d rebalance dates.
- Formal validation completed with PIT leakage audit pass.
- State-conditioned OCF composite outperformed equal-weight, raw OCF and raw low-vol baselines in the research window.

## Blockers

- Promotion source gate remains incomplete: inventory/demand and pipeline tariff/policy states are missing.
- Business exposure is still industry-proxy based, not reviewed annual-report segment evidence.
- Cash dividend events remain unrepaired; no Engineering handoff is allowed.

## Continuation

- Allowed next action: `Research Agent repairs promotion state, reviewed business exposure and cash dividend event evidence before PM can consider Engineering preparation.`
- Restart condition: `Promotion data gate repaired and rerun formal validation confirms stable evidence without changing V5.8g weights.`
- Skill status change: `none`