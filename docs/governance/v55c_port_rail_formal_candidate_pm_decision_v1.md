# V5.5c Port / Rail Formal Candidate PM Decision V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
research_pit_validation
```

Status:

```text
formal_strategy_candidate
engineering_blocked_until_operating_evidence_review
not_accepted_strategy
```

## Summary

V5.5 tested three nearby dividend / cash-flow sectors:

```text
telecom_operators
gas_water_operators
port_rail_infrastructure
```

Port / rail infrastructure had the strongest initial evidence, so PM opened a Research -> Quant repair loop.

Research Agent added an operating-state framework. Quant Agent tested two versions:

```text
V5.5b: operating_state_score as positive scoring factor
V5.5c: operating_state_score as diagnostic-only field
```

PM decision:

```text
Accept V5.5c as a formal_strategy_candidate.
Reject operating_state_score as a positive scoring factor.
Keep operating_state_score as diagnostic / review field only.
Block Engineering until real operating evidence is reviewed.
```

## Model

Strategy ID:

```text
port_rail_cashflow_value_operating_diagnostic_v55c
```

Core scoring factors:

| Factor | Role |
| --- | --- |
| dividend_yield | shareholder return |
| operating_cash_flow_yield | cash-flow value |
| free_cash_flow_yield | distributable cash proxy |
| low_price_to_book | valuation discipline |
| capex_burden | capital intensity risk |

Diagnostic-only field:

```text
operating_state_score
```

The diagnostic field has zero scoring weight.

## Evidence

Full sample:

| Test | Result |
| --- | ---: |
| Rows / dates / securities | 409 / 18 / 23 |
| Composite cumulative return | 54.95% |
| Equal-weight baseline | 13.19% |
| High-dividend baseline | 22.85% |
| Operating-state-only diagnostic | 30.42% |
| Rolling 2024 | 19.32% |
| Rolling 2025 | 14.90% |
| Rolling 2026 | -4.84% |
| Selection count 6 / 8 / 10 | 59.09% / 54.95% / 39.31% |

Factor IC / RankIC:

| Factor | Mean IC | Mean RankIC | Positive IC ratio |
| --- | ---: | ---: | ---: |
| dividend_yield | 0.1124 | 0.0995 | 0.5000 |
| operating_cash_flow_yield | 0.1122 | 0.1125 | 0.7778 |
| free_cash_flow_yield | 0.1263 | 0.1017 | 0.6111 |
| low_price_to_book | 0.1991 | 0.1806 | 0.7222 |
| capex_burden | -0.0356 | 0.0532 | 0.5556 |
| operating_state_score | 0.0455 | 0.0401 | 0.5556 |

Interpretation:

```text
The main evidence supports cash-flow value and low-PB valuation discipline.
Operating-state score is weakly positive in the full sample but not strong enough to score directly.
```

## V5.5b Rejection

V5.5b tested operating_state_score as a positive factor.

Result:

```text
Composite with operating_state_score: 49.86%
Drop operating_state_score: 55.21%
Rail-only operating_state_score RankIC: -0.0500
```

PM conclusion:

```text
Do not use operating_state_score as a positive ranking factor.
```

## Subgroup Review

| Subgroup | Evidence | PM interpretation |
| --- | --- | --- |
| Port only | Composite 50.15%; beats equal-weight 17.59% and high-dividend 25.74% | Supported. |
| Rail only | Composite approximately equal to universe; 2025 and 2026 negative | Not independently supported. |

PM interpretation:

```text
V5.5c is a port-dominant infrastructure cash-flow value candidate.
It may include railway names in the mixed universe only if they pass the same cash-flow value screen.
Railway cannot be marketed or treated as a standalone validated model.
```

## State Bucket Finding

The sector-level revenue-growth bucket did not behave as a simple cycle-following signal:

| State | Periods | Mean return | Cumulative return |
| --- | ---: | ---: | ---: |
| weak | 5 | 3.63% | 18.36% |
| strong | 3 | 0.55% | 1.60% |
| mid | 5 | -1.61% | -9.03% |
| warmup | 5 | 0.75% | 3.47% |

Interpretation:

```text
Port / rail cash-flow value may be defensive in weak demand states.
Do not add a strong-demand timing overlay without new evidence.
```

## Blockers Before Engineering

Engineering Agent must not run local daily simulation or write JoinQuant code yet.

Required repair items:

```text
manual / official operating evidence review;
cargo throughput and container throughput where available;
rail freight / passenger volume where available;
tariff or pricing-policy evidence;
port / rail revenue-share purity evidence;
real cash dividend event collection;
sector benchmark confirmation;
```

## PM Status

Approved status:

```text
formal_strategy_candidate
research_pit_validation_passed
engineering_blocked_until_operating_evidence_review
```

Not approved:

```text
accepted_strategy
platform_replication
paper_trading
live_trading
```

## Next Gate

Next step:

```text
V5.5d operating evidence review and engineering data gate.
```

Only after that can Engineering Agent do:

```text
local daily simulation
cash dividend handling
benchmark alignment
JoinQuant replication
```

