# V5.1f Utilities Quant Agent PM Escalation

Date: 2026-07-16

Escalation reason:

```text
Quant loop found a stronger demand-state rule before Engineering Agent review.
```

Current status:

```text
formal_candidate_quant_ready
```

Not status:

```text
formal_strategy_candidate
platform_replication
accepted_strategy
```

## Candidate Rule

```text
weak electricity demand -> high dividend top 10
mid electricity demand -> operating cash-flow yield top 10
strong electricity demand -> low PB top 10
warmup -> operating cash-flow yield top 10
```

Rule id:

```text
demand_state_dividend_cashflow_low_pb
```

## Quant Evidence

Rolling PIT evidence:

| Case | Cumulative Return | Positive Ratio |
| --- | ---: | ---: |
| demand_state_dividend_cashflow_low_pb | 2.6761 | 0.6053 |
| raw_low_pb_utilities_top10 | 1.9444 | 0.5526 |
| raw_cashflow_yield_utilities_top10 | 1.9209 | 0.6316 |

Selection-count robustness:

| Selection Count | Candidate | Low PB | Cash-flow | Result |
| ---: | ---: | ---: | ---: | --- |
| 8 | 3.1463 | 2.0196 | 1.9549 | pass |
| 10 | 2.6761 | 1.9444 | 1.9209 | pass |
| 12 | 2.7365 | 1.8761 | 2.2157 | pass |

State-conditioned RankIC support:

| State | Factor | RankIC |
| --- | --- | ---: |
| weak | high dividend | 0.0718 |
| mid | cash-flow yield | 0.0757 |
| strong | low PB | 0.0988 |

Failure-year count:

```text
2 fail years
4 mixed years
4 pass years
```

Fail years:

```text
2017, 2020
```

## PM Interpretation

The model is financially explainable:

- weak demand: high dividend acts as a defensive shareholder-return anchor;
- mid demand: cash-flow yield captures operating resilience;
- strong demand: low PB captures asset re-rating / valuation recovery.

Quant Agent may submit this to PM for formal-candidate review.

Engineering Agent remains blocked until PM explicitly upgrades the status to:

```text
formal_strategy_candidate
```

No JoinQuant code, local platform replication, or engineering implementation should be generated before that decision.
