# Bank Quant V5

V5 is not just a new trading strategy.

It is a research and development framework for systematic quantitative investing. Its purpose is to turn investment hypotheses into reproducible, explainable, and deployable quantitative strategies.

> A strategy can generate returns.
>
> A research framework can generate strategies.
>
> Bank Quant V5 is designed to build the latter.

## Research Philosophy

Statistical methods identify relationships. Financial theory explains why those relationships exist. Artificial Intelligence accelerates the process of discovering, validating, and implementing them.

V5 is built on the integration of these three disciplines rather than relying on any single one.

The full research manifesto is stored in [docs/RESEARCH_MANIFESTO.md](docs/RESEARCH_MANIFESTO.md), the operating skill map is stored in [docs/V5_SKILL_MAP.md](docs/V5_SKILL_MAP.md), and the machine-readable project context is stored in [config/v5_context.json](config/v5_context.json).

## Framework Summary

V5 is a natural-language-driven quantitative strategy research framework. Its core operating idea is simple:

> AI translates research intent into a structured strategy specification; deterministic Python modules run validation, research, backtests, and experiment recording.

This repository starts with a minimal auditable skeleton:

- Structured strategy specification in JSON.
- Strict validation and research-risk audit.
- Deterministic engine entrypoint.
- Experiment artifact recording.
- Skill design documents for the V5 workflow.
- A V4 bank strategy reproduction example as the first standard case.

## Agent Architecture

V5 uses a compact four-agent architecture. The objective is not to create many agents, but to mirror the way a real quantitative research team separates responsibility and prevents unchecked decisions.

```text
User
  |
  v
Project Manager Agent
  |
  +--> Research Agent
  +--> Quant Validation Agent
  +--> Engineering Agent
  |
  v
Project Manager Agent
  |
  v
Final Result
```

### Project Manager Agent

The Project Manager Agent is the orchestrator of the V5 project. It reads the manifesto, maintains the roadmap, breaks work into stages, assigns tasks, collects agent reports, manages experiment flow, updates TODOs, and records final decisions.

Its core question is: what should happen next?

It does not directly design factors, write strategy code, or perform statistical validation.

### Research Agent

The Research Agent acts as the financial researcher. It converts investment ideas into testable hypotheses, proposes factor designs, explains financial logic, reviews literature, judges economic meaning, and creates experiment plans.

Its core question is: why is this worth researching?

It does not write code, tune parameters, or accept strategies based only on returns.

### Quant Validation Agent

The Quant Validation Agent acts as the statistical analyst. It validates research hypotheses through IC analysis, RankIC, Fama-MacBeth regression, correlation analysis, feature selection, rolling validation, walk-forward testing, robustness tests, and overfitting checks.

Its core question is: is there evidence to support this?

It does not create financial theory, modify strategy ideas, or write trading logic.

### Engineering Agent

The Engineering Agent acts as the quantitative engineer. It turns approved research into runnable systems, including Python modules, JoinQuant implementations, strategy engines, portfolio construction, risk control, tests, audit checks, and documentation.

Its core question is: how can this be implemented reliably?

It does not invent investment views, change research conclusions, or adjust theory to fit historical performance.

## Shared Agent Rule

Every V5 agent must follow the same rule:

> Every decision must be evidence-driven, financially explainable, statistically validated, reproducible and maintainable. Historical performance alone is never sufficient evidence for accepting a strategy.

## Dynamic Skill Lifecycle

V5 skills are living project infrastructure.

If a skill becomes unavailable, unsafe, or outdated because an API, data source, permission, or research process changes, it should be marked as limited, deprecated, or disabled for new work. The reason and replacement route must be recorded.

If a task succeeds without an existing skill and the workflow is repeatable, V5 should summarize the experience and convert it into a new candidate skill.

## Quick Start

```powershell
$env:PYTHONPATH="src"
python -m v5.cli validate examples/v4_bank_candidate1.json
python -m v5.cli run examples/v4_bank_candidate1.json --out experiments
```

For local development:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
```

## Design Principles

- Research is more valuable than a single strategy.
- Explainability comes before performance.
- Evidence comes before optimization.
- Reproducibility is mandatory.
- AI augments researchers rather than replacing them.
- No free-form AI strategy code generation for core research logic.
- Every strategy must be expressed as a structured, inspectable specification.
- Serious data leakage or execution issues block formal runs.
- Local research, platform backtests, and future execution should share the same strategy spec.
- Every experiment records the spec, audit result, code context, parameters, warnings, and outputs.

## Current Scope

This first scaffold does not yet implement real factor computation or backtesting. It establishes the contract that future modules must follow:

```text
natural language
    -> strategy spec
    -> validation and leakage audit
    -> deterministic research engine
    -> experiment record
    -> report and platform export
```

## Project Layout

```text
src/v5/
  spec.py          Strategy specification model and parser
  audit.py         Completeness, leakage, and execution-risk audit
  engine.py        Deterministic run orchestration and artifact writing
  cli.py           Command-line entrypoint
examples/
  v4_bank_candidate1.json
docs/
  RESEARCH_MANIFESTO.md
  V5_SKILL_MAP.md
skills/
  v5-controller/
  research-agent/
  quant-validation-agent/
  engineering-agent/
  data-source-router/
  joinquant-a-share-collector/
  tushare-data-collector/
  financial-statement-standardizer/
  bank-indicator-replacement-collector/
  annual-report-bank-indicator-collector/
  candidate-governance/
  allocation-selection-separator/
  momentum-research/
  mean-reversion-research/
  defensive-overlay-research/
  state-routing-research/
  strategy-attribution/
  execution-stress-test/
  research-archive-freeze/
  statistical-validation-protocol/
  joinquant-strategy-exporter/
  skill-lifecycle-manager/
  strategy-spec/
  data-leakage-audit/
  factor-research/
  rolling-validation/
  execution-consistency/
  research-report/
tests/
```
