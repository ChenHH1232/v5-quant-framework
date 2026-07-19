# Insurance V5.3e Research Hypothesis Redesign

Date: 2026-07-17

Project:

```text
V5.3e Insurance Research Reset
```

Status:

```text
research_hypothesis_design_only
```

## Research Premise

V5.3d showed that adding total investment return and solvency as simple positive score factors did not improve the low-PB insurance baseline.

Therefore V5.3e must change the structure of the hypothesis, not the parameter weights.

The new insurance research question is:

```text
When is low PB a real insurance value opportunity, and when is it a value trap caused by weak franchise value, weak solvency or adverse market state?
```

## Role Redesign

| Variable family | V5.3d role | V5.3e proposed role | Reason |
| --- | --- | --- | --- |
| PB | alpha score | core value score | still has the strongest PIT evidence |
| solvency | positive score | guard / risk-control candidate | weak alpha evidence, but economically useful for avoiding capital stress |
| total investment return | positive score | state / diagnostic variable | negative IC suggests it may capture regime exposure rather than alpha |
| EV / NBV | enhancement only | future core valuation / franchise layer after PIT repair | better insurance-specific economics, but coverage is not ready |
| real 10Y yield | review state | state bucket variable | insurance valuation and reinvestment economics are rate sensitive |
| equity market state | review state | state bucket variable | investment income and solvency are equity-market sensitive |

## Candidate Hypothesis A: Low PB With Solvency Guard

Hypothesis:

```text
Low PB works better when solvency is not weak. Solvency should filter value traps rather than create alpha.
```

Candidate rule:

- rank by low PB;
- require solvency not below a conservative PIT threshold or not in the weakest cross-sectional bucket;
- do not reward extremely high solvency as alpha;
- compare against raw low PB on the same common sample.

Reject if:

- filtered low PB does not improve drawdown, weak-year behavior or rolling stability;
- the filter only improves one hand-picked period;
- sample coverage becomes too small.

## Candidate Hypothesis B: Low PB With Investment-State Diagnostic

Hypothesis:

```text
Investment return is not a stable stock selector, but it may explain when low PB is dangerous.
```

Candidate use:

- do not add total investment return to the score;
- bucket periods by real 10Y yield state and equity-market drawdown state;
- test whether low PB works differently under rising-rate, falling-rate, equity-stress and equity-rebound states;
- use investment return only to explain failures unless state evidence is stable.

Reject if:

- state buckets are too sparse;
- state-conditioned performance is unstable under rolling validation;
- the state rule is only visible after knowing failure years.

## Candidate Hypothesis C: P/EV Value After PIT Repair

Hypothesis:

```text
Insurance value should be measured by price relative to embedded value, not only book value, when reliable PIT EV data exists.
```

Candidate rule after data repair:

- calculate market_cap / embedded_value;
- optionally calculate market_cap / new_business_value for life-insurance franchise sensitivity;
- compare P/EV against PB and low-PB-only baseline;
- run life-insurance-only and all-insurance panels separately.

Reject if:

- EV / NBV source dates cannot be verified;
- EV coverage is too short for rolling validation;
- P/EV does not beat low PB on common-sample PIT validation.

## Candidate Hypothesis D: Subgroup Split

Hypothesis:

```text
Life insurers and P&C insurers have different economics, so one composite may dilute signal.
```

Candidate tests:

- life insurance / insurance group subgroup;
- P&C subgroup;
- combined universe as reference only.

Life candidates:

- low PB;
- P/EV after repair;
- NBV growth after repair;
- solvency guard;
- real-rate state.

P&C candidates:

- low PB;
- combined ratio / claim ratio after repair;
- solvency guard;
- underwriting profitability stability.

Reject if:

- subgroup sample size is too small for stable rolling validation;
- results rely on one stock dominating the sample.

## Quant Validation Requirements

Quant Agent must test the redesigned hypotheses with:

- PIT leakage audit;
- common-sample low-PB baseline;
- single-factor IC / RankIC;
- rolling validation;
- failure-year analysis for 2021, 2022 and 2026;
- state-bucket validation for rate and equity-market states;
- guard-effect analysis for solvency filter;
- concentration sensitivity because the insurance universe is small.

## Engineering Block

Engineering Agent remains blocked until one redesigned hypothesis passes formal research PIT validation.

Do not generate:

- JoinQuant code;
- local daily simulation;
- platform replication;
- paper-trading records.

