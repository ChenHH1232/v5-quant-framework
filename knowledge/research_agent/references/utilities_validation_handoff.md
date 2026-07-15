# Utilities Validation Handoff

Date: 2026-07-16

Owner:

Research Agent

Receiver:

Quant Validation Agent

Project:

```text
V5.1 Utilities Sector Process-Portability Test
```

Status:

```text
ready_for_pm_gate_review
```

## Handoff Purpose

This file defines what Quant Validation Agent must test before V5.1 can become a formal strategy candidate.

No platform backtest should start before this validation packet is complete and reviewed by Project Manager Agent.

## Required Validation Layer

All validation results must be tagged:

```text
research_pit_validation
```

## PIT Leakage Audit

Quant Validation Agent must check:

- financial statement pubDate or conservative visible date;
- dividend announcement date, ex-dividend date, and payment date separation;
- universe membership visible date;
- listing date, ST status, suspension status;
- no use of future industry reclassification;
- no use of full-sample normalization.

## Single-Factor Tests

For each candidate factor:

- IC;
- RankIC;
- information decay by holding horizon;
- coverage by rebalance date;
- missing-data rate;
- correlation with other factors;
- subgroup comparison if thermal / hydro / nuclear / gas / water behave differently.

## Baselines

Minimum baselines:

- equal-weight utilities operating universe;
- low-PB utilities baseline;
- high-dividend utilities baseline.

Optional baselines:

- electric-power-only equal-weight baseline;
- market-cap-weighted utilities baseline if benchmark data is available.

## Ablation

Run module-level ablation:

- valuation only;
- dividend only;
- profitability quality only;
- cash flow only;
- debt-service capacity only;
- composite without valuation;
- composite without dividend;
- composite without cash-flow support;
- composite without debt-service penalty.

## Rolling Validation

Quant Validation Agent must use rolling windows rather than treating 2021-2026 as a tuning period.

Required checks:

- rolling IC / RankIC;
- rolling baseline excess;
- rolling drawdown and volatility;
- rolling factor coverage;
- stability of selected stocks.

## Robustness

Required robustness checks:

- selection count perturbation;
- factor weight perturbation;
- rebalance frequency perturbation;
- common-sample comparison;
- missing-data policy comparison;
- sub-industry split;
- exclusion of extreme valuation observations;
- dividend-yield trap filter sensitivity.

## Weak-Period Review

If V5.1 has weak years or weak windows, Quant Validation Agent must identify whether the cause is:

- tariff or policy shock;
- fuel-cost cycle;
- capex cycle;
- dividend cut;
- high leverage becoming unserviceable;
- sub-industry concentration;
- platform execution assumptions.

## PM Promotion Criteria

V5.1 can move toward `formal_strategy_candidate` only if:

- retained factors have clear utilities-specific economic logic;
- PIT leakage audit passes;
- at least one baseline comparison is meaningful;
- ablation shows contribution is not only from one accidental exposure;
- rolling validation is not dominated by one short period;
- robustness does not collapse under small parameter changes.
