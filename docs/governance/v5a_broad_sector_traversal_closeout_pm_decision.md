# V5a Broad Sector Traversal Closeout

Date: 2026-07-21

## Decision

V5a broad sector traversal has covered all configured sectors for the dividend low-volatility OCF/FCF enhanced ETF roadmap. This is PM routing, not strategy acceptance.

## Bucket Counts

| Bucket | Count |
| --- | ---: |
| `archived_or_rejected` | 6 |
| `blocked_by_cycle_data_gate` | 3 |
| `blocked_by_data_gate` | 2 |
| `blocked_by_specialist_data_gate` | 1 |
| `core_or_observation_refresh_no_tuning` | 6 |
| `excluded_from_current_mandate` | 7 |
| `research_repair_only` | 8 |

## PM Routing Table

| Sector | Bucket | Basket eligibility | Next agent |
| --- | --- | --- | --- |
| `bank` | `core_or_observation_refresh_no_tuning` | `eligible_or_existing_sleeve_refresh_only` | `Engineering Agent` |
| `utilities_electricity` | `core_or_observation_refresh_no_tuning` | `eligible_or_existing_sleeve_refresh_only` | `Engineering Agent` |
| `highway_infrastructure` | `core_or_observation_refresh_no_tuning` | `eligible_or_existing_sleeve_refresh_only` | `Engineering Agent` |
| `port_rail_infrastructure` | `core_or_observation_refresh_no_tuning` | `eligible_or_existing_sleeve_refresh_only` | `Engineering Agent` |
| `gas_water_operators` | `core_or_observation_refresh_no_tuning` | `eligible_or_existing_sleeve_refresh_only` | `Engineering Agent` |
| `telecom_operators` | `research_repair_only` | `not_eligible_until_repair_passes` | `Research Agent` |
| `insurance` | `core_or_observation_refresh_no_tuning` | `eligible_or_existing_sleeve_refresh_only` | `Engineering Agent` |
| `securities_brokerage` | `research_repair_only` | `not_eligible_until_repair_passes` | `Research Agent` |
| `oil_gas_pipeline_integrated` | `research_repair_only` | `not_eligible_until_repair_passes` | `Research Agent` |
| `coal` | `archived_or_rejected` | `not_eligible` | `Project Manager Agent` |
| `steel` | `blocked_by_cycle_data_gate` | `not_eligible` | `Research Agent` |
| `nonferrous_metals` | `blocked_by_cycle_data_gate` | `not_eligible` | `Research Agent` |
| `chemical_materials` | `archived_or_rejected` | `not_eligible` | `Project Manager Agent` |
| `building_materials_cement` | `archived_or_rejected` | `not_eligible` | `Project Manager Agent` |
| `construction_engineering` | `blocked_by_data_gate` | `not_eligible` | `Research Agent` |
| `environmental_project_operators` | `blocked_by_data_gate` | `not_eligible` | `Research Agent` |
| `real_estate` | `excluded_from_current_mandate` | `not_eligible` | `Project Manager Agent` |
| `consumer_staples_cashflow` | `research_repair_only` | `not_eligible_until_repair_passes` | `Research Agent` |
| `food_beverage` | `research_repair_only` | `not_eligible_until_repair_passes` | `Research Agent` |
| `home_appliances` | `research_repair_only` | `not_eligible_until_repair_passes` | `Research Agent` |
| `textile_apparel` | `research_repair_only` | `not_eligible_until_repair_passes` | `Research Agent` |
| `pharma_medical_services` | `blocked_by_specialist_data_gate` | `not_eligible` | `Research Agent` |
| `agriculture_forestry_fishery` | `excluded_from_current_mandate` | `not_eligible` | `Project Manager Agent` |
| `logistics_express` | `research_repair_only` | `not_eligible_until_repair_passes` | `Research Agent` |
| `shipping` | `blocked_by_cycle_data_gate` | `not_eligible` | `Research Agent` |
| `retail_commerce` | `archived_or_rejected` | `not_eligible` | `Project Manager Agent` |
| `media_entertainment` | `excluded_from_current_mandate` | `not_eligible` | `Project Manager Agent` |
| `computer_software` | `excluded_from_current_mandate` | `not_eligible` | `Project Manager Agent` |
| `electronics_semiconductor` | `excluded_from_current_mandate` | `not_eligible` | `Project Manager Agent` |
| `auto_and_parts` | `archived_or_rejected` | `not_eligible` | `Project Manager Agent` |
| `machinery_equipment` | `archived_or_rejected` | `not_eligible` | `Project Manager Agent` |
| `power_equipment_new_energy` | `excluded_from_current_mandate` | `not_eligible` | `Project Manager Agent` |
| `military_defense` | `excluded_from_current_mandate` | `not_eligible` | `Project Manager Agent` |

## Mainline Read

Current enhanced ETF mainline should keep relying on already passed or frozen sleeves: bank, utilities/electricity, highway, port/rail, gas/water observation and the frozen V5.7f basket process.

New broad sectors screened in V5a.10-V5a.11 do not enter Engineering. Pharma is blocked by specialist R&D/policy data. Securities has a research signal but is a financial-market-cycle specialist, not a stable cash-flow sleeve. Auto, machinery, chemicals and retail are rejected or archived for the current mandate.

## Output Paths

- Master CSV: `docs\governance\v5a_broad_sector_coverage_master_table.csv`
- Master summary: `docs\governance\v5a_broad_sector_coverage_master_summary.json`
