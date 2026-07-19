# V5.3g Insurance Stage Closeout V1

Date: 2026-07-17

Status:

```text
insurance_workflow_fixed_as_domain_specific_template
```

Strategy:

```text
insurance_pev_value_v53g
```

Current strategy status:

```text
frozen_formal_strategy_candidate
platform_replication_summary_matched_pending_daily_attribution
paper_trading_started
```

Not status:

```text
accepted_strategy
live_trading_approved
return_tuning_allowed
```

## Executive Summary

The insurance line has reached a useful stage result.

V5.3g is not an accepted strategy, but it is now a valid frozen candidate with:

- reviewed multi-year PIT EV/NBV data;
- a clean insurance-specific value hypothesis;
- formal PIT validation;
- local JoinQuant-like daily simulation;
- overfit audit with no blockers;
- JoinQuant summary-level replication that closely matches local results.

The main accepted research conclusion is:

```text
For core listed A-share insurers, low P/EV is a better insurance-specific value anchor than generic low PB.
```

NBV growth, solvency, ROE, dividend, PB, PE and investment yield are not approved score factors in V5.3g.

## Key Results

Formal validation:

| Metric | Value |
| --- | ---: |
| PIT leakage audit | pass |
| Mean IC | 0.0513 |
| Mean RankIC | 0.1095 |
| Positive IC ratio | 71.43% |
| Low P/EV top3 cumulative return | 32.14% |
| Equal-weight covered insurance cumulative return | 23.40% |

Local daily simulation:

| Metric | Value |
| --- | ---: |
| Strategy return | 29.89% |
| Annualized return | 5.51% |
| Benchmark | 399809.XSHE |
| Benchmark return | -3.02% |
| Excess return | 32.91% |
| Max drawdown | 34.20% |

JoinQuant summary result:

| Metric | Value |
| --- | ---: |
| Strategy return | 28.86% |
| Annualized return | 5.30% |
| Benchmark return | -3.51% |
| Excess return | 33.55% |
| Max drawdown | 34.25% |
| Max drawdown interval | 2023-05-08 to 2024-01-23 |

PM read:

```text
JoinQuant summary-level replication is close enough to confirm that the local simulation and platform execution are following the same frozen strategy contract.
```

## Why Insurance Workflow Should Be Fixed

Insurance should have a fixed V5 workflow, but it should not simply copy the bank or utilities template.

Insurance requires a domain-specific process because:

- generic low PB is only a proxy;
- the real value anchor is EV / P/EV;
- EV and NBV are not ordinary standardized factors in the local panel;
- source date and visible date matter heavily;
- company scope differs across group, life business, health business and P&C business;
- the universe is tiny, so every model is concentration-sensitive;
- 2026 shows that relative value can still suffer large absolute drawdowns.

Therefore, the fixed insurance workflow should be:

```text
Research knowledge -> EV/NBV source repair -> PIT visibility audit -> P/EV panel -> formal validation -> local daily simulation -> platform replication attribution -> paper trading
```

## Fixed Insurance Workflow

### 1. Research Agent

Responsibilities:

- maintain insurance valuation knowledge;
- distinguish group EV, life-only EV, life-plus-health EV and P&C non-EV business;
- decide whether a field is a score factor, diagnostic variable or risk-control candidate;
- reject return tuning after results are known.

Required outputs:

- insurance valuation hypothesis;
- EV / NBV scope notes;
- source reliability notes;
- next-hypothesis decision if validation fails.

### 2. Data / Research Repair

Required fields:

- code;
- report_period;
- field;
- value;
- unit;
- source_title;
- source_url;
- publish_date;
- visible_date;
- original_announcement_checked;
- review_status;
- notes.

Hard rule:

```text
No EV/NBV row may enter formal validation unless original_announcement_checked=true and review_status=reviewed.
```

### 3. Quant Validation Agent

Required tests:

- PIT coverage gate;
- visible-date leakage audit;
- IC / RankIC;
- baseline;
- rolling validation;
- ablation;
- robustness;
- failure-year analysis.

For insurance, the default accepted baseline comparisons should include:

- equal-weight core insurance;
- low PB;
- low P/EV;
- any proposed quality or guard factor.

### 4. Engineering Agent

Allowed after PM handoff:

- local JoinQuant-like daily simulation;
- real daily open / close execution;
- true cash dividend after tax;
- benchmark comparison using `399809.XSHE` unless PM changes it;
- platform attribution.

Not allowed:

- changing factor logic;
- adding guards;
- changing selection count;
- tuning around 2026;
- writing a new JoinQuant strategy before PM freezes the candidate.

### 5. Project Manager

PM must decide:

- whether the candidate can be frozen;
- whether platform replication is summary-matched or fully passed;
- whether paper trading can start;
- whether any failure requires Research Agent restart with a new strategy ID.

## Current Open Items

V5.3g still needs:

1. JoinQuant daily returns export;
2. JoinQuant transaction export;
3. JoinQuant position export;
4. full JoinQuant log;
5. local-vs-platform daily attribution;
6. future paper-trading signal records.

V5.3g does not need:

- more factor tuning;
- 2021-2026 return optimization;
- adding NBV growth into score;
- adding solvency or ROE guards under the same ID.

## Final PM Decision

Fix the insurance workflow as a domain-specific V5 template.

Do not treat it as the global golden template yet. The global golden template remains V5.1f utilities because it has a broader workflow structure. Insurance becomes the first fixed template for a data-repair-heavy financial subsector.

Next gate:

```text
export_joinquant_daily_transaction_position_log_for_attribution
```

Parallel ongoing gate:

```text
continue_forward_paper_trading_log_without_tuning
```
