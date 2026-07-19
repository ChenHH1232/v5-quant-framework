# V5.8 Workflow Freeze Archive V1

## Freeze Purpose

This freeze records the point where V5 became a workflow-governed research system rather than a folder of isolated sector strategy tests.

The frozen scope covers:

- PM operating protocol and agent loop packets.
- Typed config validation.
- Workspace contract audit.
- Strategy state promotion gate.
- V5.7f dashboard, action router, paper refresh queue and platform export intake controls.
- Nearby-sector replication artifacts through V5.8.

## Commit Layers

Recommended layered commits:

1. `workflow`: source code, tests, CLI entry points and dependency declarations.
2. `governance`: status registry, protocol docs, PM decisions and knowledge-base updates.
3. `evidence`: lightweight structured outputs, checkpoint packets, configs, examples and JoinQuant script exports.

## Local-Only Archive

The following directories are intentionally treated as local cache/source archive and should not be committed:

- `tmp/`
- `research_reports/`

They contain large PDF/source materials used for research extraction. The reproducible evidence should be the structured CSV/JSON/Markdown outputs and source-register notes committed elsewhere.

## Current Governance Snapshot

- Workspace contract audit: `passed`
- Config validation: `16 passed, 0 failed`
- Example validation: `49 passed, 0 failed`
- Status registry audit: `31 strategies, 0 missing evidence paths, 0 accepted-status violations`
- V5.7f accepted-strategy gate: `blocked`
- V5.7f next gate: `wait_until_refresh_window_or_user_supplies_platform_exports`

## PM Rule

After this freeze, new strategy work should start only after the default PM entry checks pass:

1. `audit-workspace-contract`
2. strategy-specific dashboard/action route when applicable
3. `strategy-state-gate` before any registry status promotion
4. checkpoint/blocker/failure-return packet at the end of the timebox
