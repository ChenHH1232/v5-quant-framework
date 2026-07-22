# V5 Enhanced ETF Production Line

Created at UTC: `2026-07-22T02:08:23+00:00`

## PM Decision

Status: `engineering_local_refresh_ready_not_platform_replication`

V57f remains frozen. This production line refreshes and routes sleeves; it does not change the strategy.

## Active Core Sleeves

| Sleeve | Engineering gate | Data files |
| --- | --- | --- |
| `bank` | `ready_for_local_refresh` | panel=yes, price=yes, dividend=yes |
| `highway_infrastructure` | `ready_for_local_refresh` | panel=yes, price=yes, dividend=yes |
| `port_rail_infrastructure` | `ready_for_local_refresh` | panel=yes, price=yes, dividend=yes |
| `utilities_electricity` | `ready_for_local_refresh` | panel=yes, price=yes, dividend=yes |

## Observation / Repair Routing

| Sector | Lane | Next agent | Gate |
| --- | --- | --- | --- |
| `gas_water_operators` | `observation_refresh_only` | `Engineering Agent` | `not_core_engineering_observation_only` |
| `insurance` | `observation_refresh_only` | `Engineering Agent` | `not_core_engineering_observation_only` |
| `consumer_staples_cashflow` | `research_repair_queue` | `Research Agent` | `not_engineering_handoff` |
| `food_beverage` | `research_repair_queue` | `Research Agent` | `not_engineering_handoff` |
| `home_appliances` | `research_repair_queue` | `Research Agent` | `not_engineering_handoff` |
| `logistics_express` | `research_repair_queue` | `Research Agent` | `not_engineering_handoff` |
| `oil_gas_pipeline_integrated` | `research_repair_queue` | `Research Agent` | `not_engineering_handoff` |
| `securities_brokerage` | `research_repair_queue` | `Research Agent` | `not_engineering_handoff` |
| `telecom_operators` | `research_repair_queue` | `Research Agent` | `not_engineering_handoff` |
| `textile_apparel` | `research_repair_queue` | `Research Agent` | `not_engineering_handoff` |
| `construction_engineering` | `data_gate_blocked` | `Research Agent` | `blocked_before_modeling` |
| `environmental_project_operators` | `data_gate_blocked` | `Research Agent` | `blocked_before_modeling` |
| `nonferrous_metals` | `data_gate_blocked` | `Research Agent` | `blocked_before_modeling` |
| `pharma_medical_services` | `data_gate_blocked` | `Research Agent` | `blocked_before_modeling` |
| `shipping` | `data_gate_blocked` | `Research Agent` | `blocked_before_modeling` |
| `steel` | `data_gate_blocked` | `Research Agent` | `blocked_before_modeling` |
| `auto_and_parts` | `archived_or_rejected` | `Project Manager Agent` | `archived_not_engineering` |
| `building_materials_cement` | `archived_or_rejected` | `Project Manager Agent` | `archived_not_engineering` |
| `chemical_materials` | `archived_or_rejected` | `Project Manager Agent` | `archived_not_engineering` |
| `coal` | `archived_or_rejected` | `Project Manager Agent` | `archived_not_engineering` |
| `machinery_equipment` | `archived_or_rejected` | `Project Manager Agent` | `archived_not_engineering` |
| `retail_commerce` | `archived_or_rejected` | `Project Manager Agent` | `archived_not_engineering` |
| `agriculture_forestry_fishery` | `excluded_from_current_mandate` | `Project Manager Agent` | `excluded_not_engineering` |
| `computer_software` | `excluded_from_current_mandate` | `Project Manager Agent` | `excluded_not_engineering` |
| `electronics_semiconductor` | `excluded_from_current_mandate` | `Project Manager Agent` | `excluded_not_engineering` |
| `media_entertainment` | `excluded_from_current_mandate` | `Project Manager Agent` | `excluded_not_engineering` |
| `military_defense` | `excluded_from_current_mandate` | `Project Manager Agent` | `excluded_not_engineering` |
| `power_equipment_new_energy` | `excluded_from_current_mandate` | `Project Manager Agent` | `excluded_not_engineering` |
| `real_estate` | `excluded_from_current_mandate` | `Project Manager Agent` | `excluded_not_engineering` |

## Refresh Plan

| # | Stage | Owner | Status | Gate |
| ---: | --- | --- | --- | --- |
| 1 | `freeze_check` | `Project Manager Agent` | `completed_by_runner` | `no_new_sleeves` |
| 2 | `signal_refresh` | `Engineering Agent` | `completed_existing_output` | `quarterly_signal_file_exists` |
| 3 | `local_daily_refresh` | `Engineering Agent` | `completed_existing_output` | `rebalance_order_health_passed` |
| 4 | `formal_validation_refresh` | `Quant Validation Agent` | `completed_existing_output` | `formal_validation_completed` |
| 5 | `failure_attribution` | `Quant Validation Agent` | `completed_existing_output` | `diagnosis_not_tuning` |
| 6 | `ablation_refresh` | `Quant Validation Agent` | `completed_existing_output` | `no_blocked_cases` |
| 7 | `overfit_audit` | `Engineering Agent` | `completed_existing_output` | `blocker_count_zero` |
| 8 | `pm_gate` | `Project Manager Agent` | `completed_existing_output` | `blocker_count_zero` |
| 9 | `forward_paper_gate` | `Project Manager Agent` | `completed_existing_output` | `pending_clean_future_rebalance` |
| 10 | `dashboard` | `Project Manager Agent` | `completed_existing_output` | `blocked_actions_visible` |
| 11 | `action_route` | `Project Manager Agent` | `completed_existing_output` | `no_tuning_no_platform_claim` |

## Engineering Boundary

- Engineering may rerun local daily simulation, real dividend accounting, holdings, trades, cash logs and `rebalance_order_health`.
- Engineering must not tune returns, change factors, add sleeves, or mark platform replication passed.
- Next clean paper signal remains gated by the future rebalance window.

## Hard Rule

Historical performance alone is never sufficient evidence for accepting a strategy.
