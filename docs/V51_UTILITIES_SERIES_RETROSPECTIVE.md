# V5.1 Utilities Series Retrospective

Date: 2026-07-16

Owner:

Project Manager Agent

Scope:

```text
V5.1 / V5.1b / V5.1c / V5.1d research_pit_validation
```

## Executive Conclusion

The V5 process is not the main problem.

The utilities models were repeatedly rejected because the research hypothesis was still too generic for utilities:

```text
generic value + generic cashflow + generic dividend + generic controls
```

did not beat the simpler raw baselines:

```text
raw_low_pb_utilities_top10
raw_cashflow_yield_utilities_top10
```

This is a useful process result. V5 correctly prevented weak or overbuilt models from moving to Engineering Agent.

## What V5.1 Proved

V5.1 proved that the framework can run outside bank-specific indicators:

- PIT utilities universe construction;
- local PIT panel collection from JoinQuant;
- IC / RankIC;
- baseline comparison;
- ablation;
- rolling validation;
- conditional validation;
- PM gatekeeping.

The process portability test passed:

```text
process_portability = passed_initial
```

The strategy candidate gate did not pass:

```text
formal_candidate_gate = rejected_for_now
```

## Result Summary

| Test | Main idea | Best model / case | Result |
| --- | --- | --- | --- |
| V5.1 | generic value-quality-dividend composite | composite_current = 1.1816 | rejected; lost to low PB and high dividend |
| V5.1b | sub-industry cash-flow value composite | cashflow_value_composite_v51b = 1.1414 | rejected; lost to raw low PB and raw cashflow yield |
| V5.1c | low PB + cashflow two-factor model | low_pb_cashflow_composite_v51c = 0.7539 | rejected; each single factor beat the composite |
| V5.1d | conditional low PB / cashflow | best conditional = 1.7446 | rejected; still lost to raw low PB and raw cashflow yield |

Baseline results:

| Baseline | Cumulative Return | Mean Period Return | Positive Ratio |
| --- | ---: | ---: | ---: |
| equal_weight_utilities | 0.4099 | 0.0137 | 0.5526 |
| raw_low_pb_utilities_top10 | 1.9448 | 0.0354 | 0.5526 |
| raw_cashflow_yield_utilities_top10 | 1.9223 | 0.0330 | 0.6316 |
| raw_high_dividend_utilities_top10 | 1.3529 | 0.0267 | 0.5789 |

## Why Models Were Repeatedly Rejected

### 1. Simple Baselines Were Stronger Than Composites

Low PB and operating cash-flow yield each had useful evidence. But combining them through static weights reduced performance.

This means the problem is not that there is no signal. The problem is that V5.1 has not yet found a financially justified interaction rule.

### 2. Generic Controls Added Noise

Capex and leverage controls sounded economically reasonable, but they weakened the current models.

For utilities, high capex and leverage can be normal. Without knowing whether capex is maintenance, expansion, policy-driven investment, or capacity-cycle timing, penalizing it mechanically can remove useful companies.

### 3. Sector State Is Missing

Utilities returns depend on external state variables:

- coal / fuel cost;
- electricity tariff mechanism;
- utilization hours;
- hydropower water conditions;
- marketized electricity-price exposure;
- gas tariff / margin pressure;
- regulatory and policy regime.

Financial-statement factors alone cannot distinguish these regimes.

### 4. Sub-Industry Ranking Improved Clarity But Not Outcome

Sub-industry scoring made factors cleaner:

- cashflow_yield_subindustry_score mean IC = 0.0598;
- low_pb_subindustry_score mean IC = 0.0494;
- both had positive IC ratio = 0.7105.

But sub-industry versions still underperformed raw low PB and raw cashflow-yield baselines.

### 5. Static Composite Testing Has Reached Diminishing Returns

Four tests are enough to conclude:

```text
do_not_continue_static_financial_composite_testing
```

The next useful research step requires new information, not another rearrangement of the same factors.

## What Should Be Kept

Keep as official V5.1 utilities research baselines:

```text
raw_low_pb_utilities_top10
raw_cashflow_yield_utilities_top10
raw_high_dividend_utilities_top10
equal_weight_utilities
```

Keep as useful research signals:

- raw PB;
- operating cash-flow yield;
- high dividend as a benchmark;
- cash-flow-supported dividend as a hypothesis;
- sub-industry scoring as a diagnostic tool.

## What Should Be Paused

Pause:

- static composite tests using only PB, cashflow, dividend, capex, leverage and ROE;
- Engineering Agent strategy code generation;
- JoinQuant platform replication;
- formal candidate promotion.

Do not call any V5.1 utilities model:

```text
formal_strategy_candidate
accepted_strategy
```

## Required Improvements

### Data

Build a PIT external utilities state panel:

- coal price / fuel-cost proxy;
- thermal utilization hours;
- hydropower utilization or water-condition proxy;
- tariff / marketized electricity price proxy;
- gas tariff / margin proxy.

Every row must have:

- visible date;
- state date;
- source publication date;
- source URL or source name;
- PIT usability flag.

### Research

Research Agent should define state-dependent hypotheses:

- low PB may work differently in falling coal-price regimes;
- cash-flow yield may work differently when utilization hours rise;
- hydropower valuation may need water-condition context;
- high dividend may only work when cash flow and tariff regime support payout.

### Quant

Quant Validation Agent should next run:

```text
utilities_external_state_validation
```

before any new strategy candidate.

Required tests:

- state variable coverage;
- PIT leakage audit;
- state-conditioned IC / RankIC;
- sub-industry split;
- baseline comparison against raw low PB and raw cashflow yield;
- no composite promotion unless it beats both raw baselines.

### Engineering

Engineering Agent should continue only with:

- external state data template population;
- generic sector runner hardening;
- data-quality validation;
- PIT visibility checks.

Engineering Agent must not generate JoinQuant code for utilities yet.

## Stop Rule

Stop testing a utilities strategy variant if:

- it does not beat raw low PB;
- it does not beat raw operating cash-flow yield;
- it relies on fields without visible dates;
- it improves only by changing weights after seeing 2017-2026 results;
- it cannot explain why factor interaction should work in utilities.

## PM Decision

V5.1 utilities research should pause strategy-candidate attempts and move to data enrichment.

Current status:

```text
utilities_process_portability = passed_initial
utilities_strategy_candidate = rejected_for_now
next_gate = external_state_data_enrichment
```
