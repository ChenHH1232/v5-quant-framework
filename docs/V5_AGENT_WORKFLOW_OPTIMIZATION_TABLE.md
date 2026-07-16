# V5 Agent Workflow Optimization Table

Date: 2026-07-16

Owner: Project Manager Agent

Purpose: reduce Agent handoff interruptions, prevent silent stalls, and make long-running research loops auditable.

## Core Rule Update

The previous working loop used short informal progress checks. Going forward, V5 uses a formal 30-minute PM review window:

```text
If an Agent loop runs for 30 minutes without producing a usable artifact, PM must review the cause before work continues.
```

A usable artifact can be:

- research memo;
- data availability table;
- validation result;
- runner output;
- JoinQuant code;
- blocker report;
- decision log.

## Optimization Table

| Problem Observed | Risk | New Rule | Owner | Required Artifact | PM Action After 30 Minutes |
|---|---|---|---|---|---|
| Research Agent and Quant Agent loop can silently stall | Repeated idea testing without decision | Every research loop must state hypothesis, required data, stop rule, and next handoff before starting | PM + Research | Research task sheet | Stop, continue, or narrow scope |
| Quant Agent can repeatedly reject models without explaining next information need | User sees `model failed` but not why | Every rejection must classify cause: no signal, bad interaction, weak data, unstable window, or missing external state | Quant | Rejection reason table | Decide whether Research must add data or archive branch |
| Engineering can start platform work before candidate is frozen | Platform tests waste time and mix layers | Engineering starts JoinQuant/local replication only after PM opens the exact gate | PM + Engineering | Gate approval record | Block unauthorized platform work |
| Long-running loops exceed user patience | Work feels invisible | Any loop expected to exceed 30 minutes must create an interim checkpoint | Active Agent | 30-minute checkpoint note | PM reviews progress and blockers |
| Data source/API failure can be hidden by fallback logic | Strategy trades on degraded or blank data | Fallback must be explicit: allowed, blocked, or research-only | Engineering | Source status and fallback table | Disable skill, limit skill, or create replacement skill |
| Platform replication and research validation can be mixed | False acceptance from confirmation window | Every runner output must include experiment layer | PM + Engineering | Layer label in output | Reject mixed-layer evidence |
| Paper trading can accidentally backfill history | Forward record loses meaning | Paper trading starts from log-open date only; no retrospective edits to signals | PM | Paper-trading log entry | Reject backfilled evidence |
| JoinQuant scripts may lack pre-start lookback data | First rebalance can be blank or wrong | Separate `backtest_start_date` and `data_warmup_start_date`; preload required history | Engineering | Warm-up coverage log | Block trading if warm-up coverage fails |
| Live factor recompute may differ from frozen-signal test | Platform pass may overstate readiness | Keep frozen-signal replication and live-recompute smoke tests as separate statuses | Engineering + PM | Two separate governance records | Promote only the tested capability |
| Strategy performance dominates discussion | Overfitting and narrative chasing | Every candidate must pass overfit audit before promotion | Engineering + Quant | Overfit audit report | Resolve blockers; review warnings |

## Standard Agent Handoff Checklist

Before handing off to the next Agent, each Agent must provide:

| Field | Required Content |
|---|---|
| Current status | `passed`, `failed`, `blocked`, `needs_review`, or `ready_for_next_agent` |
| Evidence path | File path to report, CSV, runner output, script, or log |
| Blocking issue | Data/API/method/contract issue if any |
| Next owner | PM, Research, Quant, or Engineering |
| Stop rule | Condition that stops the next loop |
| Timebox | Default 30 minutes unless PM approves longer |

## 30-Minute Blocker Report Template

If a loop reaches 30 minutes without a usable artifact, PM must request:

```text
Agent:
Task:
Elapsed time:
Current artifact:
What is blocked:
What was tried:
Most likely cause:
Can continue without user input: yes/no
Recommended next action:
Skill status change needed: none/limited/disabled/new skill candidate
```

## PM Decision Language

Allowed PM decisions:

- `continue_same_loop`;
- `narrow_scope`;
- `return_to_research`;
- `return_to_quant`;
- `return_to_engineering`;
- `freeze_candidate`;
- `archive_branch`;
- `start_paper_trading`;
- `disable_or_revise_skill`;
- `ask_user_for_external_input`.

## V5.1 Immediate Application

For V5.1f:

- paper trading is now open;
- live JoinQuant recompute has a separate smoke-test script;
- platform frozen-signal pass remains valid but separate;
- V5.1f is still not accepted;
- the next 30-minute PM review applies to any attempt to run live JoinQuant recompute or produce the next paper-trading signal.
