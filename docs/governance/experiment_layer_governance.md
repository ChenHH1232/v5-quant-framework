# V5 Experiment Layer Governance

Date: 2026-07-15

## Required Experiment Layers

Every result must be tagged with exactly one layer:

- `research_pit_validation`
- `platform_replication`
- `engineering_smoke_test`
- `paper_trading`

Project Manager Agent must block any report that does not carry one of these labels.

## Layer Definitions

### research_pit_validation

Purpose:

Validate whether a research hypothesis has statistical evidence.

Required rules:

- Use point-in-time data.
- Use `notice_date` visibility for disclosed financial data.
- Use rolling validation.
- Include baseline, ablation, robustness, and leakage audit.
- Do not tune on the 2021-2026 platform-confirmation window.

### platform_replication

Purpose:

Reproduce a JoinQuant or other platform result closely enough for debugging and deployment confidence.

Required rules:

- Use the same strategy logic as the platform script.
- Use platform-compatible visibility rules when replicating a known platform script.
- Produce daily returns, holdings, trades, dividends, cash, and rebalance signals.
- Run local-vs-platform daily attribution after platform daily CSV is exported.

### engineering_smoke_test

Purpose:

Check whether code, data pipes, and runners work.

Required rules:

- Performance cannot be used as investment evidence.
- Any positive result must be escalated to `research_pit_validation` before interpretation.

### paper_trading

Purpose:

Record forward behavior after a strategy candidate is frozen.

Required rules:

- No backfilled decisions.
- All decisions must be recorded before execution.
- Use `notice_date` visibility.

## Agent Gates

### Project Manager Agent

- Reject unlabeled results.
- Reject mixed interpretation across layers.
- Maintain decision log.
- Decide when a strategy can move from one layer to another.

### Quant Validation Agent

- Owns `research_pit_validation`.
- Must run:
  - notice-date leakage audit
  - rolling validation
  - baseline tests
  - ablation tests
  - robustness tests

### Engineering Agent

- Owns `platform_replication` and `engineering_smoke_test`.
- Must produce:
  - automatic snapshot
  - daily attribution
  - rebalance-stock comparison material
  - order, dividend, cash diagnostics

