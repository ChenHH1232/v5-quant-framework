# V5a.3 Theory-Gated Preliminary Validation PM Decision

Date: 2026-07-21  
Layer: research_pit_prevalidation  
Status: completed_initial_prevalidation_not_strategy_acceptance  
Owner: Project Manager Agent

## Decision

V5a.3 completed a full first-pass theory-gated preliminary validation over 33 broad A-share sector candidates.

This is not a formal Quant validation packet, not a platform replication packet and not strategy acceptance. It is the routing layer that prevents V5 from exploring sectors one by one without a common theory and data contract.

## What Was Executed

1. Loaded all sectors from `config/v5a.1_broad_sector_coarse_screening.json`.
2. Applied V5a.2 theory gates:
   - value investing,
   - operating cash-flow quality,
   - free-cash-flow comparability,
   - dividend sustainability,
   - low volatility,
   - momentum support,
   - mean-reversion support.
3. Produced a theory-gated sector prevalidation CSV, JSON summary and PM report.
4. Re-ran the sector replication batch after the theory gate to keep agent queues aligned.

## Key Result

| Decision | Count | PM Meaning |
| --- | ---: | --- |
| `passed_prevalidation_shadow_basket_refresh` | 3 | Existing candidates can be refreshed by Engineering without changing logic. |
| `research_gate_before_quant_initial_validation` | 7 | Research Agent must complete knowledge/data/capex-quality gates before Quant. |
| `specialist_or_small_sample_observation_before_initial_validation` | 2 | Needs special sample policy or specialist model; do not apply broad IC standards. |
| `low_priority_observation_before_initial_validation` | 7 | Watchlist only; no Quant/Engineering time before higher-priority lanes. |
| `observation_waiting_platform_or_local_attribution` | 1 | Keep observation until attribution inputs are complete. |
| `blocked_by_cycle_data_gate_before_initial_validation` | 4 | Commodity/cycle state data gate blocks modeling. |
| `blocked_by_data_gate_before_initial_validation` | 2 | Hard data quality gate blocks modeling. |
| `excluded_before_initial_validation` | 7 | Outside current dividend low-volatility OCF/FCF mandate. |

## Full Sector Routing Table

| Sector | Primary theory | Factor priority | V5a.3 decision | Next agent |
| --- | --- | --- | --- | --- |
| Bank | `sector_specific_value_and_balance_sheet_quality` | `sector_specific_value>dividend_sustainability>low_volatility` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Utilities / Electricity | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Highway Infrastructure | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Port / Rail Infrastructure | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `research_gate_before_quant_initial_validation` | `Research Agent` |
| Gas / Water Operators | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `research_gate_before_quant_initial_validation` | `Research Agent` |
| Telecom Operators | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `specialist_or_small_sample_observation_before_initial_validation` | `Project Manager Agent` |
| Insurance | `sector_specific_value_and_balance_sheet_quality` | `sector_specific_value>dividend_sustainability>low_volatility` | `specialist_or_small_sample_observation_before_initial_validation` | `Project Manager Agent` |
| Securities / Brokerage | `sector_specific_value_and_balance_sheet_quality` | `sector_specific_value>dividend_sustainability>low_volatility` | `low_priority_observation_before_initial_validation` | `Project Manager Agent` |
| Oil / Gas Pipeline and Integrated Energy | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `observation_waiting_platform_or_local_attribution` | `Project Manager Agent` |
| Coal | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `blocked_by_cycle_data_gate_before_initial_validation` | `Research Agent` |
| Steel | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `blocked_by_cycle_data_gate_before_initial_validation` | `Research Agent` |
| Nonferrous Metals | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `blocked_by_cycle_data_gate_before_initial_validation` | `Research Agent` |
| Basic Chemicals | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `low_priority_observation_before_initial_validation` | `Project Manager Agent` |
| Building Materials / Cement | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `research_gate_before_quant_initial_validation` | `Research Agent` |
| Construction Engineering | `cash_conversion_and_receivables_trap_detection` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `blocked_by_data_gate_before_initial_validation` | `Research Agent` |
| Environmental / Project Operators | `cash_conversion_and_receivables_trap_detection` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `blocked_by_data_gate_before_initial_validation` | `Research Agent` |
| Real Estate | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Consumer Staples Cash-Flow Leaders | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `research_gate_before_quant_initial_validation` | `Research Agent` |
| Food / Beverage | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `research_gate_before_quant_initial_validation` | `Research Agent` |
| Home Appliances | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `research_gate_before_quant_initial_validation` | `Research Agent` |
| Textile / Apparel | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `low_priority_observation_before_initial_validation` | `Project Manager Agent` |
| Pharma / Medical Services | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `research_gate_before_quant_initial_validation` | `Research Agent` |
| Agriculture / Forestry / Fishery | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Logistics / Express Delivery | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `low_priority_observation_before_initial_validation` | `Project Manager Agent` |
| Shipping | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `blocked_by_cycle_data_gate_before_initial_validation` | `Research Agent` |
| Retail / Commerce | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `low_priority_observation_before_initial_validation` | `Project Manager Agent` |
| Media / Entertainment | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Computer / Software | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Electronics / Semiconductor | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Auto and Parts | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `low_priority_observation_before_initial_validation` | `Project Manager Agent` |
| Machinery / Equipment | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `low_priority_observation_before_initial_validation` | `Project Manager Agent` |
| Power Equipment / New Energy | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Military / Defense | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |

## PM Interpretation

V5 can now traverse broad sectors in one batch. The process result is:

- Core refresh lane: bank, utilities/electricity and highway infrastructure.
- Research-before-Quant lane: port/rail, gas/water, building materials/cement, consumer staples, food/beverage, home appliances and pharma/medical services.
- Specialist/small-sample observation lane: telecom and insurance.
- Cycle/data blocked lane: coal, steel, nonferrous metals, shipping, construction engineering and environmental/project operators.
- Excluded lane: real estate, agriculture, media, software, electronics/semiconductor, power equipment/new energy and military/defense.

The most useful next Research Agent targets are:

1. Consumer staples / food beverage.
2. Home appliances.
3. Building materials / cement only if cycle state data is available.
4. Pharma / medical services after policy/R&D gate.
5. Port / rail and gas/water only as refresh/repair lanes, because they already have prior work.

## Output Paths

- V5a.3 workflow: `docs/governance/v5a.3_theory_gated_preliminary_validation_workflow.md`
- V5a.3 config: `config/v5a.3_theory_gated_sector_prevalidation.json`
- Theory-gated CSV: `sector_replication_batches_v5a3/theory_gated_prevalidation_current/theory_gated_sector_prevalidation.csv`
- Theory-gated summary: `sector_replication_batches_v5a3/theory_gated_prevalidation_current/theory_gated_sector_prevalidation_summary.json`
- Theory-gated report: `sector_replication_batches_v5a3/theory_gated_prevalidation_current/theory_gated_sector_prevalidation_pm_report.md`
- Replication batch packet: `sector_replication_batches_v5a3/replication_batch_after_theory_gate/sector_replication_batch_packet.json`
- Replication batch report: `sector_replication_batches_v5a3/replication_batch_after_theory_gate/sector_replication_batch_pm_report.md`
- Agent queues: `sector_replication_batches_v5a3/replication_batch_after_theory_gate/roadmap/agent_queues/`

## Next Gate

Proceed to Research Agent batch repair for the seven `research_gate_before_quant_initial_validation` sectors. Quant validation should start only after those sectors have explicit industry knowledge, PIT data and capex/FCF comparability gates.

