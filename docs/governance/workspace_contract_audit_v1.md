# Workspace Contract Audit V1

## Purpose

`audit-workspace-contract` is the default PM entry check before new strategy promotion, platform-replication marking, paper-signal generation, or new sector formal-candidate freeze.

It verifies that V5's control-plane evidence is internally consistent before agents continue.

## Scope

The audit checks:

- `config/*.json` typed validation.
- `examples/*.json` typed validation.
- `docs/governance/status_registry.json` required strategy fields.
- Evidence paths referenced by each registry strategy.
- `accepted_strategy` status cannot appear without platform and paper evidence.

## Current Result

- Status: `passed`
- Config files: `16 passed, 0 failed`
- Example files: `49 passed, 0 failed`
- Registry: `31 strategies, 0 missing paths, 0 missing required fields, 0 accepted-status violations`
- Warnings: legacy or diagnostic specs still carry non-blocking validation reminders.

## Evidence

- Runner: `src/v5/workspace_contract_audit_runner.py`
- Tests: `tests/test_workspace_contract_audit_runner.py`
- Latest summary: `workspace_contract_audits_v58/latest/workspace_contract_audit_summary.json`
- Latest report: `workspace_contract_audits_v58/latest/workspace_contract_audit_report.md`

## PM Rule

This is a read-only governance check. It must not run backtests, refresh data, tune models, call JoinQuant, or generate signals.

If this audit is blocked, the PM Agent must repair the workflow contract before allowing:

- strategy state promotion
- platform replication passed marking
- paper-trading signal generation
- new sector formal-candidate freeze
