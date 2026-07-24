# Enhanced ETF Governance Summary

Status: `v57f_core_and_observation_governance_completed`

## Mainline

V57f remains the frozen mainline. This package does not change sleeves, factors, weights, timing, or any future paper runner.

| Type | Sector | Status | Return | Drawdown | Order health | Next gate |
| --- | --- | --- | ---: | ---: | --- | --- |
| `mainline_basket` | `enhanced_etf_basket` | `formal_etf_candidate_frozen_not_accepted` | 81.42% | 11.75% | `passed` | `engineering_local_refresh_ready_wait_until_2026_10_or_user_supplies_platform_exports` |
| `core_sleeve` | `bank` | `core_frozen_refresh_only` |  |  | `covered_by_mainline_order_health` | `core_refresh_only` |
| `core_sleeve` | `highway_infrastructure` | `core_frozen_refresh_only` |  |  | `covered_by_mainline_order_health` | `core_refresh_only` |
| `core_sleeve` | `port_rail_infrastructure` | `core_frozen_refresh_only` |  |  | `covered_by_mainline_order_health` | `core_refresh_only` |
| `core_sleeve` | `utilities_electricity` | `core_frozen_refresh_only` |  |  | `covered_by_mainline_order_health` | `core_refresh_only` |

## Observation Sleeves

| Sector | Class | Stage | Promotion decision | Return | Drawdown | Paper | Required next evidence |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| `gas_water_operators` | `observation_basket` | `engineering_local_refresh_passed` | `remain_observation_needs_forward_or_sidecar_evidence` | 70.07% | 12.15% | `paper_artifact_exists` | show IR contribution is not materially worse than V57f |
| `telecom_operators` | `small_sample_capped_observation` | `paper_tracking_ready_waiting` | `capped_observation_only` | 80.12% | 11.11% | `paper_artifact_exists` | PM-approved capped/specialist sleeve policy |
| `home_appliances` | `observation_paper_tracking_candidate` | `research_or_data_repair` | `research_data_repair_required` | 106.37% | 30.18% | `paper_artifact_exists` | show drawdown does not worsen V57f materially in sidecar / forward evidence;complete research/data-gate repair before any promotion audit |
| `insurance` | `specialist_small_sample_observation` | `local_summary_available_needs_pm_review` | `engineering_repair_required` | 29.89% | 34.20% | `paper_artifact_exists` | repair or explain rebalance_order_health;show drawdown does not worsen V57f materially in sidecar / forward evidence;PM-approved capped/specialist sleeve policy;close specialist/cycle-state industry data gate ex ante |
| `oil_gas_pipeline_integrated` | `cycle_state_observation` | `research_or_data_repair` | `research_data_repair_required` | 99.79% | 21.78% | `not_applicable_or_missing` | create paper tracking packet after engineering blockers are closed;show drawdown does not worsen V57f materially in sidecar / forward evidence;show IR contribution is not materially worse than V57f;complete research/data-gate repair before any promotion audit;close specialist/cycle-state industry data gate ex ante |
| `food_beverage` | `engineering_review_or_research_repair` | `engineering_local_refresh_passed` | `engineering_repair_required` | 11.58% | 43.16% | `not_applicable_or_missing` | repair or explain rebalance_order_health;create paper tracking packet after engineering blockers are closed;show drawdown does not worsen V57f materially in sidecar / forward evidence;show IR contribution is not materially worse than V57f |
| `coal` | `archived_data_gate_failed` | `archived_or_failed` | `archived_or_data_gate_failed` | 133.69% | 28.11% | `not_applicable_or_missing` | repair or explain rebalance_order_health;create paper tracking packet after engineering blockers are closed;show drawdown does not worsen V57f materially in sidecar / forward evidence;show IR contribution is not materially worse than V57f;complete research/data-gate repair before any promotion audit;close specialist/cycle-state industry data gate ex ante |

## Next Queue

| Rank | Owner | Task | Gate |
| ---: | --- | --- | --- |
| 1 | Project Manager Agent | Keep V57f frozen and use this governance summary as the single status entry point. | `governance_reference_only` |
| 2 | Project Manager Agent | When a separate simulation/paper workflow is opened, use this table to decide which sleeves are eligible for refresh. | `external_or_future_window_only` |

## Rules

- Historical performance alone cannot promote an observation sleeve.
- Observation sleeves cannot enter V57f core without a separate PM stage gate.
- This run does not update or generate the 2026-10 paper runner.
- Platform replication and accepted/live statuses remain blocked unless their own evidence gates pass.
