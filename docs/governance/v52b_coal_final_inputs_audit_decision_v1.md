# Governance Record: v52b_coal_final_inputs_audit_decision_v1

Date: 2026-07-16

Project:

```text
V5.2b Coal Cash-Flow Cycle Value / Capex Policy
```

PM decision:

```text
do_not_promote_engineering_inputs_repaired_external_state_blocked
```

## Decision

Project Manager Agent confirms that the final Engineering input blocker has been repaired, but V5.2b Coal still cannot be promoted.

## Evidence

Engineering Agent produced:

- daily returns;
- rebalance signals;
- daily holdings / trades / dividends;
- JoinQuant-like local simulation summary;
- overfit audit rerun with daily artifacts.

Quant Validation Agent reran:

- formal validation;
- IC / RankIC;
- rolling validation;
- baseline;
- ablation;
- robustness;
- cycle-state validation;
- 2018 failure analysis.

## Remaining Blocker

The coal external state panel still lacks official PIT-ready raw-coal output or inventory history.

The current formal-state manifest has only one usable `coal_inventory_or_output_state` observation, which is not enough to explain 2018 ex ante or accept a cyclical value strategy.

## Classification

```text
workflow_replication_passed_strategy_candidate_failed
```

with updated sub-status:

```text
engineering_audit_inputs_repaired
external_state_history_still_blocked
research_pit_validation_completed_not_acceptance
```

## Governance Rule

For cyclical commodity sectors, price state alone is not sufficient. Formal promotion requires PIT-ready production, inventory, or supply-demand state evidence.

Historical return and post-hoc commodity-cycle explanation are not enough.

