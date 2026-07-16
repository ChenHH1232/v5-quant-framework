# Governance Record: v52b_coal_final_pm_decision_v1

Date: 2026-07-16

Project:

```text
V5.2b Coal Cash-Flow Cycle Value / Capex Policy
```

PM decision:

```text
workflow_replication_passed_strategy_candidate_failed
```

## Decision

Project Manager Agent closes V5.2b Coal as a process-portability success and strategy-candidate failure.

## Rationale

The V5 agent workflow worked:

- Research Agent reframed the coal thesis from dividend to cash-flow value.
- Quant Validation Agent ran baseline, IC / RankIC, rolling, ablation, robustness, state bucket and weak-year checks.
- Engineering Agent added source templates, PIT disclosure-date tooling, capex-policy tooling and validation gates.
- Project Manager Agent blocked premature platform replication.

The strategy candidate did not pass:

- official raw-coal output / inventory history remains incomplete;
- coal business segment evidence remains empty;
- 2018 remains a severe failure year;
- overfit audit remains `needs_review` without daily strategy artifacts;
- historical return is not sufficient evidence.

## Frozen Status

```text
V5.2b Coal = archived_not_formal_candidate
```

Allowed future work:

- fill NBS historical rows;
- fill company segment evidence;
- use V5.2b only as a research memory case.

Disallowed work:

- JoinQuant strategy code;
- local platform replication;
- paper trading;
- accepted-strategy labeling.

## Next PM Recommendation

Move to either:

1. V5.3 nearby-sector process test; or
2. shared data-collection tooling improvement before the next cyclical sector.
