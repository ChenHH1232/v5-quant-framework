# V5.5b Port / Rail Operating-State Repair Workflow V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Status:

```text
research_agent_workflow_ready
quant_agent_waiting_for_repaired_panel
engineering_agent_blocked
```

## Trigger

V5.5a tested three similar-sector initial models:

```text
telecom_operators
gas_water_operators
port_rail_infrastructure
```

PM selected port / rail infrastructure for the next Research -> Quant loop because it had the strongest initial evidence:

```text
Composite return exceeded equal-weight and high-dividend baselines.
Rolling 2024 and 2025 were positive.
2026 was negative in absolute terms but outperformed equal-weight and low-PB baselines.
IC / RankIC signals were more coherent than the other two sectors.
```

This is still not a formal strategy candidate.

## Objective

Repair the missing operating-state layer before any Engineering handoff.

The next hypothesis must explain:

```text
Why port / rail cash-flow value should work.
When it fails.
Which operating states make valuation and dividend signals reliable or unreliable.
```

## Research Agent Tasks

Research Agent must build these artifacts before Quant Agent reruns validation:

| Artifact | Required path |
| --- | --- |
| Port / rail operating-state framework | `knowledge/research_agent/factor_theory/port_rail_operating_state_framework.md` |
| Port / rail value-trap framework | `knowledge/research_agent/factor_theory/port_rail_value_trap_framework.md` |
| Port / rail operating field map | `knowledge/research_agent/references/port_rail_operating_field_map.md` |
| Port / rail source collection plan | `knowledge/research_agent/references/port_rail_source_collection_plan.md` |
| Port / rail validation handoff | `knowledge/research_agent/references/port_rail_validation_handoff.md` |

## Required Operating Fields

| Field group | Examples | PIT requirement |
| --- | --- | --- |
| Port throughput | cargo throughput, container throughput, bulk cargo mix | report publish date or official data visible date |
| Rail volume | freight volume, passenger volume, ton-km where available | report publish date or official data visible date |
| Trade / freight state | export/import state, freight index, cargo demand proxy | official publication date or conservative visible date |
| Tariff / pricing policy | regulated price, port fee adjustment, railway freight pricing policy | announcement / policy publish date |
| Business purity | port / rail operating revenue share, logistics / property / finance contamination | annual / interim report publish date |
| Capex burden | expansion capex, maintenance capex, major project commitments | report publish date |

## Research Rules

Research Agent must not:

```text
Use V5.5a return to choose new factors.
Invent a theory after Quant results.
Use current business structure to label historical membership.
Treat investor articles as verified operating data.
```

Research Agent may use articles / research reports only to generate hypotheses.

## Quant Agent Next Tests

After Research Agent creates the repaired panel, Quant Agent must rerun:

```text
baseline
IC / RankIC
rolling validation
ablation
robustness
state bucket validation
2026 failure analysis
port-only vs rail-only subgroup analysis
```

## Engineering Block

Engineering Agent must not write JoinQuant code or local daily strategy simulation until PM approves:

```text
formal_strategy_candidate
```

Allowed Engineering work only:

```text
manual import template
data quality checker
PIT visible-date checker
benchmark availability probe
```

## PM Acceptance For Next Gate

V5.5b can move to formal candidate review only if:

```text
Operating-state data has PIT visible dates.
Composite evidence still beats equal-weight and high-dividend baselines.
At least one operating-state bucket explains when the model works.
Port-only and rail-only behavior is not contradictory, or submodels are split.
Robustness does not depend on one selection count or one year.
```

Historical performance alone remains insufficient.

