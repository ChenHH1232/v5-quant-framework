# V5 Agent Operating Protocol V1

Date: 2026-07-19

Owner: Project Manager Agent

Purpose: govern exploratory V5 agent work so agents do not interrupt the user after every ordinary step, but also do not run indefinitely or drift away from the approved objective.

## Core Rule

Exploratory tasks use timeboxed autonomous loops, not fixed task-by-task user approval.

Default behavior:

```text
Continue within the approved objective.
Do not ask the user after ordinary progress.
Stop at the timebox, a stage gate, a blocker, a direction change, or a no-new-evidence rule.
Produce a checkpoint or blocker packet before continuing to the next loop.
```

## Default Timebox

| Work type | Default timebox | PM action at timebox |
| --- | ---: | --- |
| Normal research / quant / engineering loop | 30 minutes | Produce checkpoint and decide continue / narrow / stop |
| User-approved deep exploration | 60 minutes | Produce checkpoint and justify continuation |
| External data collection or long-running runner | Task-specific | Produce progress log and resource note |

The timebox is not a request for user confirmation. It is a PM checkpoint.

## Agent Action Classes

### Class 1: Continue Without Asking

Allowed when the agent is still inside the same approved objective and the next action is reversible or routine.

Examples:

- continue collecting data for the same hypothesis;
- repair field names, paths, encodings, dates, or runner inputs;
- rerun a failed runner after fixing an implementation issue;
- produce validation, attribution, audit, status, or checkpoint files;
- continue testing an already approved candidate within the same experiment layer;
- update documentation to reflect confirmed outputs.

Required output:

```text
Short progress note during the loop.
Checkpoint or artifact at the timebox or completion.
```

### Class 2: Report But Do Not Ask

Allowed when PM changes the immediate next action but remains inside the same approved objective.

Examples:

- a sector is blocked by missing PIT data and PM moves to data availability audit;
- a hypothesis fails and Quant returns it to Research for revision;
- Engineering finds platform mismatch and moves to attribution;
- a runner cannot use a skill, but non-skill execution works and the result can become a new skill candidate;
- a branch is marked observation-only or blocked-by-data without opening a new strategy line.

Required output:

```text
Checkpoint packet explaining the decision, evidence, and next owner.
No user question unless a mandatory-user-decision trigger is hit.
```

### Class 3: Must Ask User

The agent must ask the user before proceeding when any of these triggers occurs:

- change research direction or open a new sector / new strategy line;
- promote a strategy state, including `formal_strategy_candidate`, `platform_replication_passed`, `paper_trading`, `accepted_strategy`, or `live_trading_approved`;
- use paid external resources, manual user data, credentials in a new way, or long-running external services;
- delete, overwrite, or restructure large parts of the repository;
- change frozen strategy logic, weights, guards, universe, benchmark, or execution contract;
- continue after two consecutive loops with no new evidence;
- resolve a blocker that requires user-owned information or external action.

Required output before asking:

```text
Decision packet with options, evidence, risk, and PM recommendation.
```

## Stop Rules

An agent loop must stop and create a checkpoint or blocker packet when:

- the timebox ends;
- the approved hypothesis is rejected;
- required PIT data is unavailable or not legally / ethically collectible;
- the same blocker repeats in two consecutive loops;
- two consecutive loops produce no new evidence;
- results start mixing experiment layers;
- work would require a mandatory user decision;
- Engineering would need to change frozen research logic.

Stopping does not mean failure. It means PM has a reliable point to decide whether to continue, narrow, archive, or ask the user.

## Output Types

| Output type | Purpose | User confirmation required |
| --- | --- | --- |
| `progress_note` | Short loop update | No |
| `checkpoint_packet` | Timebox or loop summary | No, unless it contains a stage gate |
| `blocker_packet` | Explain why work cannot continue safely | Sometimes |
| `failure_return_packet` | Quant returns failed hypothesis to Research | No |
| `stage_gate_decision` | Promote / freeze / open / accept / live approve | Yes |
| `external_resource_request` | Paid data, manual data, credential use change | Yes |

## Required Checkpoint Packet

Every checkpoint must include:

| Field | Required content |
| --- | --- |
| `objective` | Approved objective for this loop |
| `agent` | PM, Research, Quant, or Engineering |
| `experiment_layer` | One V5 experiment layer |
| `elapsed_timebox` | 30m / 60m / custom |
| `artifacts_created` | Paths to files, reports, runners, logs, or tables |
| `evidence_found` | New evidence or `none` |
| `decision` | continue / narrow / return / stop / ask_user |
| `next_owner` | Agent responsible for the next loop |
| `stop_rule_status` | Whether a stop rule has fired |
| `user_decision_required` | yes / no, with reason |

Implementation:

```text
python -m v5.cli agent-loop-packet --packet-type checkpoint_packet ...
```

The runner is implemented in `src/v5/agent_loop_packet_runner.py`.

## Required Blocker Packet

Every blocker packet must include:

| Field | Required content |
| --- | --- |
| `blocker_type` | data / source / method / platform / engineering / governance |
| `what_was_tried` | Concrete attempts |
| `why_blocked` | Evidence-based reason |
| `can_continue_without_user` | yes / no |
| `allowed_next_action` | continue data audit / return to research / archive / ask user |
| `restart_condition` | What must change before this branch can restart |
| `skill_status_change` | none / limited / disabled / new skill candidate |

Implementation:

```text
python -m v5.cli agent-loop-packet --packet-type blocker_packet ...
```

## Two-Loop No-New-Evidence Rule

If two consecutive loops produce no new evidence, PM must stop the branch.

PM may choose one:

- archive as failed or data-blocked;
- narrow the hypothesis;
- request external data from the user;
- explicitly approve one more timebox with a changed method.

PM must not allow silent indefinite exploration.

## Agent-Specific Enforcement

### Project Manager Agent

- Owns timeboxes, checkpoints, stage gates, and status registry.
- Blocks mixed experiment layers.
- Blocks user interruption after ordinary progress.
- Blocks indefinite loops with no new evidence.
- Decides whether a branch continues, narrows, returns, archives, or asks the user.

### Research Agent

- Learns domain knowledge and proposes hypotheses.
- Revises hypotheses only after Quant failure packets.
- Must not choose factors from backtest returns.
- Must stop after repeated no-new-evidence loops or source/data blockers.

### Quant Validation Agent

- Tests Research hypotheses with PIT evidence.
- Returns failed hypotheses to Research with failure packets.
- Must not invent financial theory or tune strategy logic.
- Must stop when data coverage, leakage, instability, or robustness blocks formal validation.

### Engineering Agent

- Receives only frozen candidates or approved engineering tasks.
- Builds local simulation, platform attribution, runners, and audits.
- Must not modify research conclusions, weights, or theory.
- Must stop if platform mismatch requires changing frozen logic.

## PM Decision Language

Allowed PM decisions:

```text
continue_same_loop
continue_next_timebox
narrow_scope
return_to_research
return_to_quant
return_to_engineering
freeze_candidate
start_platform_replication
start_paper_trading
archive_branch
disable_or_revise_skill
ask_user_for_stage_gate
ask_user_for_external_input
```

## Governance Rule

Historical performance alone is never sufficient evidence for accepting a strategy.

This protocol controls agent behavior only. It does not approve any strategy, factor, sector, or live-trading action by itself.
