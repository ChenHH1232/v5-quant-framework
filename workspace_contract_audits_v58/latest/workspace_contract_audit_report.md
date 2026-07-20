# Workspace Contract Audit

- Status: `passed`
- Blockers: `0`
- Warnings: `1`
- Root: `D:\hh\codex\v5`

## Checks

- `pass` config_validation: passed=16, failed=0, warnings=0
- `warning` example_validation: passed=50, failed=0, warnings=4
- `pass` status_registry: missing_paths=0, missing_fields=0, accepted_violations=0

## Config Validation

- agent_operating_protocol: `1`
- sector_replication_roadmap_config: `1`
- basket_runtime_config: `11`
- sector_screening_config: `2`
- project_context: `1`

## Example Validation

- legacy_strategy_spec: `41`
- research_candidate_spec: `9`

## PM Rule

Workspace contract audit is a read-only governance check; it does not run backtests, refresh data, tune models, or call JoinQuant.