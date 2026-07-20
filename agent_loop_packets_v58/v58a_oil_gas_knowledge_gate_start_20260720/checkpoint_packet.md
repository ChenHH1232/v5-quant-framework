# Agent Loop Packet: checkpoint_packet

- Objective: Start V5.8a oil gas pipeline integrated sector knowledge and data availability gate
- Agent: `Project Manager Agent`
- Experiment layer: `data_availability_gate`
- Timebox: `30 minutes`
- Decision: `return_to_research`
- Next owner: `Research Agent`
- Stop rule status: `data_gate_blocked_before_quant`
- User decision required: `False`

## Artifacts

- `docs\governance\v58a_oil_gas_knowledge_gate_pm_checkpoint_v1.md`
- `knowledge\research_agent\references\oil_gas_source_collection_plan.md`
- `knowledge\research_agent\factor_theory\oil_gas_cashflow_framework.md`
- `knowledge\research_agent\references\oil_gas_v58_source_register.md`
- `docs\governance\status_registry.json`

## Evidence

- research_reports\fxbaogao_v58_oil_gas_fcf_dividend\business_cashflow_capex\collection_manifest.json
- research_reports\fxbaogao_v58_oil_gas_fcf_dividend\external_state_price_tariff\collection_manifest.json
- workspace_contract_audits_v58\latest\workspace_contract_audit_summary.json

## Blockers

- PIT oil gas universe is not built
- Commodity price and refining spread state panels are missing
- Business exposure PIT tags are missing
- FCF cannot be promoted before capex cycle review

## Continuation

- Allowed next action: `research_agent_build_pit_universe_business_exposure_and_cycle_state_data_gate`
- Restart condition: `PIT universe plus oil/gas/spread state source path exists`
- Skill status change: `none`