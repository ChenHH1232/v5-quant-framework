# V5.9 Enhanced ETF Expansion Batch Screening PM Decision V1

Date: 2026-07-21

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
data_availability_gate
pm_decision_gate
research_pit_validation
```

## Scope

This packet starts the next enhanced ETF expansion cycle after V5.7f was frozen.

It does not:

```text
change V5.7f
run JoinQuant
write JoinQuant code
promote accepted_strategy
add any new sector to the live basket
```

It does:

```text
batch-screen candidate dividend / low-vol / OCF / sector-approved FCF sectors
repair missing research knowledge artifacts
route sectors through PM lanes
run one allowed Quant validation refresh for Gas / Water
```

## Research Knowledge Gate

Previously missing knowledge artifacts were repaired for:

| Sector | New knowledge artifacts | Status |
| --- | --- | --- |
| Consumer staples cash-flow | `consumer_staples_source_collection_plan.md`, `consumer_staples_cashflow_framework.md` | knowledge gate seed completed |
| Pharma / medical services | `pharma_source_collection_plan.md`, `pharma_cashflow_framework.md` | knowledge gate seed completed |
| Environmental / project operators | `environmental_operator_source_collection_plan.md`, `environmental_cashflow_trap_framework.md` | blocked framework completed |

FxBaogao report discovery outputs:

```text
research_reports_v59_expansion/consumer_staples/report_candidates.csv
research_reports_v59_expansion/pharma_medical/report_candidates.csv
research_reports_v59_expansion/environmental_project_operators/report_candidates.csv
```

PM rule:

```text
Research reports are knowledge sources only. They cannot become PIT factor data.
```

## Data Availability Gate Result

Screening output:

```text
validation_formal_v57_sector_coverage/sector_screening_summary.json
validation_formal_v57_sector_coverage/sector_screening_results.csv
```

Decision counts:

| Decision | Count |
| --- | ---: |
| `ready_for_basket_shadow_pool` | 4 |
| `ready_for_batch_initial_validation` | 1 |
| `platform_replication_pending_before_basket` | 1 |
| `archived_strategy_candidate_failed` | 1 |
| `needs_manual_research_before_formal` | 2 |
| `basket_observation_only` | 2 |
| `blocked_by_data_gate` | 1 |
| `blocked_by_cycle_data_gate` | 1 |

## Sector Routing

| Sector | PM lane | Decision |
| --- | --- | --- |
| Bank | basket core shadow pool | Keep refreshed; no tuning |
| Utilities / Electricity | basket core shadow pool | Golden template |
| Highway Infrastructure | basket core shadow pool | Keep refreshed; no tuning |
| Port / Rail Infrastructure | basket core shadow pool | Eligible, platform/benchmark review pending |
| Gas / Water Operators | Quant validation queue | Data repaired enough for batch validation refresh, but not formal candidate |
| Oil / Gas Pipeline and Integrated Energy | observation / platform pending | Wait for platform exports and remaining source gates |
| Airport / Transport Operators | archived strategy candidate failed | Restart only with new ex-ante domain data |
| Consumer Staples Cash-Flow Leaders | manual research before formal | Knowledge seed done; PIT universe and working-capital gate needed |
| Pharma / Medical Services | manual research before formal | Knowledge seed done; subsector and policy/R&D gates needed |
| Telecom Operators | observation only | Small sample sleeve policy needed |
| Insurance | observation only | Specialist EV/NBV/P/EV sleeve, not generic FCF |
| Environmental / Project Operators | blocked data repair | Receivable/project trap gate required |
| Coal | blocked cycle data gate | Commodity cycle-state gate required |

Roadmap output:

```text
roadmaps_v58_sector_replication/sector_replication_roadmap_summary.json
roadmaps_v58_sector_replication/agent_queues/
```

## Gas / Water Quant Refresh

Because Gas / Water passed the updated knowledge and data gate, Quant Validation Agent reran the PIT validation refresh:

```text
validation_formal_v59_expansion_batch/gas_water_value_serviceability_v57b/formal_validation_summary.json
```

Key evidence:

| Check | Result |
| --- | --- |
| PIT leakage audit | pass |
| Rows / dates | 746 rows / 20 rebalance dates |
| Composite cumulative return | 90.09% |
| Equal-weight gas/water baseline | 42.59% |
| High-dividend top10 baseline | 51.35% |
| Low-PB safe top10 baseline | 72.96% |
| Rolling 2023 | 16.55% |
| Rolling 2024 | 12.61% |
| Rolling 2025 | 25.95% |
| Rolling 2026 | -9.60% |

Interpretation:

```text
Gas / Water has a real research signal, but the 2026 failure and weak-to-moderate IC / RankIC prevent immediate formal-candidate promotion.
```

Important ablation note:

```text
Dropping capex_burden_safe improved cumulative return, so capex_burden_safe should be treated as a research question, not accepted alpha evidence.
```

Manifest note:

```text
The V5.9 validation RUN_MANIFEST correctly records pre_run dirty=true because this packet was generated while the batch screening code, config and knowledge cards were being edited. This is transparent provenance, not a frozen candidate packet.
```

## PM Decision

Current status:

```text
enhanced_etf_expansion_batch_screening_completed
research_knowledge_gate_seed_completed
data_availability_gate_routed
gas_water_research_pit_validation_refreshed
no_new_formal_strategy_candidate
```

Next actions:

1. Keep V5.7f frozen and out of tuning.
2. Do not add Gas / Water to the ETF basket yet; require 2026 failure attribution and ex-ante state hypothesis review first.
3. Consumer Staples and Pharma remain Research Agent tasks: build PIT universe, subsector split, working-capital/R&D/policy gates.
4. Environmental remains blocked until receivable/project exposure is PIT-tagged.
5. Oil / Gas remains pending platform exports and source gate repair; no basket inclusion.
6. Airport remains archived until new domain data appears.

## Hard Rule

Historical performance alone is never sufficient evidence for accepting a strategy.
