# V5 Sleeve Promotion Queue

Generated at: 2026-07-22T11:04:38.124276+00:00

## Purpose

This PM packet ranks expansion sleeve candidates by minimum completion cost and dividend / low-volatility / operating-cash-flow fit. It does not rank by historical returns.

Historical performance alone is never sufficient evidence for accepting a strategy.

## Flow Table

| Stage | Owner | Input | Action | Output | Gate |
| --- | --- | --- | --- | --- | --- |
| 1. Load production registry | PM Agent | `sleeve_registry.csv` | Read current active, observation and repair lanes | Candidate universe | Stop if registry missing |
| 2. Load strategy evidence | PM Agent | `status_registry.json` | Collect evidence paths, blockers and next gates by sector | Evidence corpus | Ignore historical return ranking |
| 3. Build gap checklist | PM Agent | Candidate rows + evidence corpus | Check PIT, dividends, low-vol, state variables, local daily, order health and sample size | `sleeve_promotion_queue.csv` | Any missing item becomes a gate, not a reason to tune |
| 4. Score candidates | PM Agent | Gap checklist | Score cash-flow fit minus completion cost and risk | Ranked queue | Do not use return metrics |
| 5. Select first candidate only | PM Agent | Ranked queue | Route only rank 1 to next agent | `promotion_agent_queues/selected_candidate_agent_queue.csv` | Other candidates stay parked |
| 6. Agent handoff | PM Agent | Selected candidate task | Send Research / Quant / Engineering a bounded next task | Checkpoint packet | No V57f config changes |

## Ranked Candidates

| Rank | Sector | Lane | Score | Fit | Cost | Risk | Next Owner | Gate |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | gas_water_operators | observation_paper_tracking | 89.0 | 94.0 | 0.0 | 5.0 | Engineering Agent | paper_tracking_only_no_core_inclusion |
| 2 | home_appliances | observation_paper_tracking | 60.0 | 82.0 | 9.0 | 13.0 | Engineering Agent | paper_tracking_only_no_core_inclusion |
| 3 | oil_gas_pipeline_integrated | external_event_wait | 42.0 | 76.0 | 9.0 | 25.0 | Project Manager Agent | wait_for_external_platform_or_forward_event |
| 4 | insurance | research_repair | 3.0 | 70.0 | 24.0 | 43.0 | Research Agent | research_data_gate_repair |
| 5 | consumer_staples_cashflow | research_repair | -7.0 | 72.0 | 56.0 | 23.0 | Research Agent | research_data_gate_repair |
| 6 | telecom_operators | external_event_wait | -8.0 | 62.0 | 31.0 | 39.0 | Project Manager Agent | wait_for_external_platform_or_forward_event |
| 7 | food_beverage | research_repair | -9.0 | 68.0 | 38.0 | 39.0 | Research Agent | research_data_gate_repair |

## Selected Agent Queue

| Rank | Sector | Owner | Task | Gate |
| --- | --- | --- | --- | --- |
| 1 | gas_water_operators | Engineering Agent | Keep gas_water_operators as an observation sleeve; refresh paper-trading inputs and wait for the next clean forward signal. Do not add it to frozen V57f. | paper_tracking_only_no_core_inclusion |

## Hard Rules

- Only the first-ranked candidate enters the next agent queue.
- Do not modify frozen V57f.
- Do not add observation sleeves into V57f without a separate PM stage gate.
- Do not tune returns, factor weights, selection count, timing or sector caps.
- Do not claim platform replication without JoinQuant daily, transaction, position and log attribution.
