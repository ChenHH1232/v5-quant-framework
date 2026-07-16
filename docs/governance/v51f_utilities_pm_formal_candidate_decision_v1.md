# Governance Record: v51f_utilities_pm_formal_candidate_decision_v1

Date: 2026-07-16

PM decision:

```text
utilities_demand_state_v51f = formal_strategy_candidate
```

Not status:

```text
platform_replication
accepted_strategy
```

## Why PM Approves Formal Candidacy

V5.1f passed Quant Agent review on the main electricity-demand state:

- beats raw low PB and raw cash-flow yield baselines;
- passes selection_count robustness at 8 / 10 / 12;
- has positive state-conditioned RankIC for the selected factor in each state;
- has a clear utilities-specific economic explanation.

Approved candidate rule:

```text
weak demand -> high dividend
mid demand -> operating cash-flow yield
strong demand -> low PB
warmup -> operating cash-flow yield
```

## Why PM Does Not Approve Strategy Acceptance

The candidate still has known failure evidence:

```text
2017 = warmup failure
2020 = weak-demand high-dividend failure
```

The secondary state metric supports demand-state conditioning, but does not yet promote this exact rule to full quant-ready status.

Therefore the strategy is not accepted. It only moves to Engineering Agent contract audit.

## Engineering Gate

Engineering Agent may audit:

- spec schema;
- PIT visibility contract;
- external state availability;
- execution assumptions;
- reproducibility requirements.

Engineering Agent may not yet generate JoinQuant code or platform replication unless this audit passes and PM explicitly opens the next gate.

## Engineering Contract Audit Update

Engineering Agent completed the contract audit and passed:

```text
engineering_contract_audit_passed
```

The audit found no blocking issues in:

- strategy schema;
- PIT universe declaration;
- external state visibility rule;
- rolling validation requirement;
- execution-cost assumptions;
- suspension / limit handling.

PM opens only the next narrow gate:

```text
engineering_smoke_test
```

Engineering smoke test has passed:

```text
engineering_smoke_test_passed
```

PM still blocks:

```text
platform_replication
JoinQuant strategy code
accepted_strategy
```
