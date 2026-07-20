# V5.7b Gas / Water Local Simulation PM Checkpoint V1

Date: 2026-07-20

Strategy:

```text
gas_water_value_serviceability_v57b
```

Layer:

```text
pm_decision_gate
```

## PM Decision

V5.7b gas / water remains a repaired research-signal candidate, but it should not be promoted to platform replication or paper trading.

Current status:

```text
local_daily_simulation_review_completed
platform_replication_deferred
research_signal_candidate_repaired
not_formal_strategy_candidate
not_paper_trading_ready
```

Reason:

```text
The strict 80% local JoinQuant-style simulation underperformed the same-pool benchmark.
The 70% startup coverage diagnostic materially improves results, but adopting it would be a coverage-policy change and cannot be used without a PM stage gate.
```

## Evidence Reviewed

Local daily simulation:

```text
local_daily_backtests_v57_gas_water/gas_water_value_serviceability_v57b/summary.json
```

Local attribution:

```text
local_daily_backtests_v57_gas_water/gas_water_value_serviceability_v57b/local_daily_pre_simulation_attribution_report.md
```

Overfit audit:

```text
validation_overfit_v57_gas_water/gas_water_value_serviceability_v57b/overfit_audit_summary.json
```

Platform packet:

```text
platform_replication_packets_v57_gas_water/gas_water_value_serviceability_v57b/platform_replication_packet.json
```

## Local Simulation Readout

Strict frozen coverage policy:

```text
minimum coverage ratio = 80%
```

| Metric | Value |
| --- | ---: |
| Strategy return | 27.85% |
| Annualized return | 5.17% |
| Same-pool benchmark return | 32.69% |
| Excess return | -4.85% |
| Max drawdown | 26.55% |
| Signal count | 19 |
| Trade records | 223 |
| Portfolio dividend events | 50 |

PM readout:

```text
This is enough to prove the local runner works, but not enough to justify platform replication as a strategy candidate.
```

## 2026 / Coverage Interpretation

The 2026 weakness is not a simple missing-data issue. Direct receivables and debt fields have full PIT coverage, but the 2026 selected basket still shows receivables-pressure risk.

The 2021 startup gap is a coverage-policy issue:

```text
2021-07-01 is skipped under the strict 80% business-purity coverage gate.
The 70% diagnostic is not accepted evidence because it changes the rule after seeing its performance impact.
```

## PM Rules

Engineering Agent may continue improving:

1. Local report readability.
2. Benchmark documentation.
3. Platform export checklist.
4. Daily attribution tooling if platform exports arrive later.

Engineering Agent must not:

1. Write a formal JoinQuant script for V5.7b now.
2. Lower the coverage gate to recover the 2021 trade.
3. Add a receivables guard just to repair 2026.
4. Promote V5.7b to formal_strategy_candidate.

## Next Gate

```text
archive_as_research_signal_candidate_or_wait_for_new_ex_ante_state_hypothesis
```

Restart conditions:

1. Research Agent produces a new ex-ante gas / water external-state hypothesis with PIT-visible fields.
2. PM explicitly approves a startup coverage policy before any performance comparison.
3. User supplies platform exports for attribution-only review.

Hard rule:

```text
Historical performance alone is never sufficient evidence for accepting a strategy.
```
