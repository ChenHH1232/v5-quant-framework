# Bank Value Quality V2 Second Round Process Review

Date: 2026-07-15

## Summary

The second-round test showed that V5 can already reproduce a JoinQuant engineering test closely:

- Local strategy return: 35.17%
- JoinQuant strategy return: 35.43%
- Local benchmark return: 26.59%
- JoinQuant benchmark return: 26.51%
- Local beta: 0.836
- JoinQuant beta: 0.837

This is a meaningful engineering milestone. But the process also exposed several workflow problems that must be fixed before V5 can be treated as a robust AI-driven quant research framework.

## Main Process Problems

### 1. Platform replication and research validation were mixed too easily

The same V2 idea produced two materially different local results:

- `notice_date` point-in-time mode: 28.06%
- `joinquant_source_year` platform-replication mode: 35.17%

This is not a small implementation detail. It changes what information was visible at each rebalance date.

Required fix:

- Every run must be labeled as one of:
  - `research_pit_validation`
  - `platform_replication`
  - `engineering_smoke_test`
  - `paper_trading`
- The Project Manager Agent should reject unlabeled results.

Owner:

- Project Manager Agent
- Quant Validation Agent

### 2. Data visibility rules were not explicit enough at the start

Eastmoney bank quality data was originally treated as a quality enhancement, but the test revealed two different visibility policies:

- strict notice-date visibility, suitable for formal validation.
- source-year visibility, useful only to replicate the current JoinQuant script.

Required fix:

- Every data source needs a visibility contract:
  - source date
  - notice date
  - effective date
  - earliest usable trade date
  - confidence/review status
- Formal factor validation must default to notice-date visibility.

Owner:

- Research Agent defines the intended information timing.
- Quant Validation Agent audits leakage.
- Engineering Agent implements the actual merge rule.

### 3. JoinQuant compatibility depends on hidden platform details

The remaining local-vs-JoinQuant gap is small, but it still depends on platform behavior:

- local uses daily open.
- JoinQuant runs at 09:40 using `current_data.last_price`.
- benchmark return appears to use a previous-trading-day anchor.
- dividend, order fill, and limit handling must be checked at daily level.

Required fix:

- Keep a dedicated `platform_replication` mode separate from research mode.
- Require JoinQuant daily return CSV for final reconciliation.
- Store daily comparison output as part of the experiment record.

Owner:

- Engineering Agent

### 4. Strategy code and local runner drift can happen silently

The local runner initially used dividend yield and panel aliases differently from the JoinQuant V2 script. That produced a much higher local result before correction.

Required fix:

- Strategy spec should generate both:
  - local runner configuration
  - JoinQuant script
- A compatibility test should compare rebalance-date selected stocks between local and JoinQuant logs.
- Any manual deviation in JoinQuant code must be recorded in the experiment manifest.

Owner:

- Engineering Agent
- Project Manager Agent

### 5. The quality proxy is still not formal research evidence

The Eastmoney quality data is currently marked `needs_check`. It is useful for engineering tests, but not enough for accepting V2 as a validated strategy.

Required fix:

- Quant Validation Agent must run:
  - baseline comparison
  - leave-one-factor-out ablation
  - rolling validation
  - robustness by rebalance day
  - data availability and coverage report
- Research Agent must document why each quality factor is economically meaningful before it enters formal validation.

Owner:

- Research Agent
- Quant Validation Agent

### 6. Experiment snapshots were not automatic enough

The second-round result had to be manually frozen after the fact.

Required fix:

- Every important run should automatically create a snapshot folder with:
  - command profile
  - summary
  - daily returns
  - holdings
  - trades
  - dividends
  - rebalance signals
  - source code git revision or dirty-worktree marker
  - platform comparison target

Owner:

- Engineering Agent

## Agent-Level Lessons

### Project Manager Agent

Needs to enforce experiment labels and decision gates. It should not allow a platform-replication result to be described as research validation.

### Research Agent

Needs to define factor visibility and economic logic before the Engineering Agent writes platform code.

### Quant Validation Agent

Needs to audit leakage before performance is interpreted. It should treat the 2021-2026 window as platform confirmation only, not as model-selection evidence.

### Engineering Agent

Needs to make local and JoinQuant behavior traceable at the daily and rebalance-date level, including holdings, cash, orders, dividends, benchmark anchor, and data availability.

## Recommended Next Steps

1. Export the JoinQuant daily return CSV from the 35.43% run.
2. Run local-vs-JoinQuant daily attribution.
3. Add a rebalance-stock comparison report using JoinQuant logs.
4. Make snapshot generation automatic for every local daily runner execution.
5. Move V2 formal testing back to `notice_date` mode and rolling validation.

