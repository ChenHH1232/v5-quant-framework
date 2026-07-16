# Governance Record: v52b_coal_suspended_data_gate_v1

Date: 2026-07-17

Status:

```text
blocked_by_manual_research_data
```

## PM Decision

Coal V5.2b is suspended as a strategy-optimization project.

It remains useful as a workflow replication and cyclical-sector data-gate case, but it must not proceed to factor tuning, platform replication, JoinQuant code, or paper trading.

## Blocking Data

Coal requires a data model that V5 has not yet fully built:

- official or reviewed commodity price state;
- raw-coal production / inventory state;
- coal-power or coal-chemical spread state;
- PIT company business segment exposure;
- reviewed annual-report / interim-report segment data.

If these are not available through clean structured sources, the correct status is not "bad strategy". The correct status is:

```text
data_gate_not_passed
```

## Allowed Work

- Build manual import templates.
- Add reviewed annual-report evidence.
- Record source gaps.
- Mark unavailable company disclosures as business-quality risk if Research Agent can justify it.

## Blocked Work

- New factor optimization.
- Return-driven rule changes.
- JoinQuant code export.
- Platform replication.
- Paper trading.

## Reopen Condition

Coal can reopen only after the PM Agent confirms:

```text
cyclical_sector_data_gate_passed
```
