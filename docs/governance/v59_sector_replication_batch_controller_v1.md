# V59 Sector Replication Batch Controller

Date: 2026-07-21

## Purpose

The nearby-sector replication workflow is now runnable as one batch controller instead of being pushed sector by sector manually.

This is not strategy acceptance and not JoinQuant platform replication. It is a PM routing layer that classifies all dividend low-volatility / operating-cash-flow / sector-approved FCF candidate sectors into agent lanes.

## Command

```bash
python -m v5.cli run-sector-replication-batch --out sector_replication_batches_v59/current
```

## Current Batch Result

- Sector count: 13
- Core shadow basket lane: 4
- Manual research before formal validation: 3
- Observation only: 3
- Blocked data repair: 3

## Current Routing

Core shadow basket:

- Bank
- Utilities / Electricity
- Highway Infrastructure
- Port / Rail Infrastructure

Manual research before formal validation:

- Gas / Water Operators
- Consumer Staples Cash-Flow Leaders
- Pharma / Medical Services

Observation only:

- Telecom Operators
- Insurance
- Oil / Gas Pipeline and Integrated Energy

Blocked data repair:

- Airport / Transport Operators
- Environmental / Project Operators
- Coal

## Agent Rules

- Research Agent must pass industry knowledge and data availability gates before Quant validation.
- Quant Validation Agent must run baseline, IC / RankIC, rolling, ablation and robustness before Engineering handoff.
- Engineering Agent only receives frozen candidates and must output local daily simulation, dividends, trades, cash, holdings and rebalance_order_health.
- No sector can be promoted because historical return looks good.
- Two consecutive loops without new evidence must produce a blocker or failure-return packet.

## Skill Status

This is currently implemented as a repo-native runner and CLI command. It is skill-ready, but not yet packaged as a Codex external skill.

The correct progression is:

1. Keep it as a tested V5 runner.
2. Use it as the default PM entry for batch sector traversal.
3. Later package it as a custom Codex skill if we want it callable outside this repository.

## Evidence

- Runner: `src/v5/sector_replication_batch_runner.py`
- CLI: `run-sector-replication-batch`
- Test: `tests/test_sector_replication_batch_runner.py`
- Packet: `sector_replication_batches_v59/current/sector_replication_batch_packet.json`
- Report: `sector_replication_batches_v59/current/sector_replication_batch_pm_report.md`
- Agent queues: `sector_replication_batches_v59/current/roadmap/agent_queues/`
