# Insurance V5.3d Composite Rejection And Research Reset

Date: 2026-07-17

Project:

```text
V5.3d Insurance Value + Investment Quality + Solvency
```

Status:

```text
research_pit_validation_completed_composite_rejected
```

## What Was Tested

Research Agent tested whether low PB could be improved by adding insurance-specific investment quality and solvency evidence.

Core score:

| Factor | Role | Direction | Weight |
| --- | --- | --- | ---: |
| low_price_to_book | valuation | lower is better | 0.50 |
| total_investment_rate_of_return | investment quality | higher is better | 0.25 |
| solvency_adequacy_ratio | balance-sheet safety | higher is better | 0.25 |

The hypothesis was financially plausible:

```text
Low PB should be more trustworthy when investment quality and solvency are also strong.
```

## Quant Result

PIT audit passed, but the composite hypothesis failed.

Baseline comparison:

| Case | Cumulative return |
| --- | ---: |
| equal_weight_core_insurance | 91.42% |
| low_pb_core_insurance_top3 | 114.52% |
| high_total_investment_return_top3 | 52.16% |
| high_solvency_top3 | 111.92% |
| v53d_composite | 67.24% |

Single-factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC ratio |
| --- | ---: | ---: | ---: |
| low_price_to_book | 0.1203 | 0.1378 | 64.86% |
| total_investment_rate_of_return | -0.1062 | -0.1254 | 43.24% |
| solvency_adequacy_ratio | 0.0472 | 0.0216 | 54.05% |

## Research Interpretation

The failure is not a data-leakage failure. It is a hypothesis-design failure.

Research lessons:

- low PB remains the strongest insurance valuation signal in the available PIT sample;
- total investment return should not be treated as a universally positive ranking factor;
- solvency is better interpreted as a risk-control or value-trap guard than as a linear alpha score;
- insurance stocks may need state-conditioned logic because investment yield depends on interest-rate and equity-market regimes;
- life insurance and P&C insurance may not belong in one undifferentiated composite model.

## New Research Rules

Do not tune:

- factor weights;
- selection count;
- 2021-2026 failure-year behavior;
- platform-replication results.

Do redesign:

- role assignment for insurance-specific fields;
- PIT data coverage for EV / NBV / P/EV;
- state-variable interpretation for investment return;
- subgroup logic for life insurance vs P&C insurance.

## Handoff

Research Agent must return to hypothesis design.

Quant Validation Agent should only receive a new hypothesis after Research Agent explicitly states:

- what is the economic mechanism;
- which fields are alpha factors;
- which fields are guards;
- which fields are state variables;
- what data coverage is required before formal validation;
- what result would reject the hypothesis.

