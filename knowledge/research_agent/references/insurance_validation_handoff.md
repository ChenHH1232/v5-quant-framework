# Insurance Validation Handoff

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

Owner:

Research Agent -> Quant Validation Agent

Status:

```text
handoff_template_ready
```

## Required Quant Tests

Quant Validation Agent must run:

- PIT leakage audit;
- baseline comparison;
- IC / RankIC;
- rolling validation;
- ablation by factor module;
- robustness tests;
- weak-year analysis;
- rate-state validation;
- equity-market-state validation.

## Baselines

Required baselines:

- equal-weight insurance;
- low-PB insurance top N;
- low-PE insurance top N;
- high-dividend insurance top N;
- life-insurance-only baseline;
- P&C-only baseline if sample is sufficient.

Optional baselines if data coverage permits:

- low P/EV top N;
- high solvency top N;
- high embedded-value-growth top N;
- low combined-ratio P&C top N.

## Required Robustness

Run:

- selection count perturbation;
- factor weight perturbation;
- rebalance-date perturbation;
- report visible-date lag sensitivity;
- life vs P&C subgroup exclusion;
- rate-state bucket split;
- equity-market-state bucket split;
- random window stress.

## Acceptance Bar

The model may only be considered for `formal_strategy_candidate` if:

- PIT audit passes;
- factors have financial explanation;
- IC / RankIC is stable enough;
- rolling years are not dominated by one rate or equity-market regime;
- ablation does not show that one fragile factor explains everything;
- baselines are not clearly superior;
- weak-year behavior is explainable ex ante.

