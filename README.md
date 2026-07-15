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

For a research-data and validation pass:

```powershell
$env:PYTHONPATH="src"
python -m v5.cli collect-data examples/bank_value_15y_strategy.json --mode plan --out data/processed
python -m v5.cli collect-dividends data/processed/bank_value_15y/panel.csv --database-dir 数据库
python -m v5.cli collect-benchmarks --database-dir 数据库 --start-date 2011-01-01 --end-date 2026-07-14
python -m v5.cli collect-data examples/bank_value_15y_strategy.json --mode v4-raw --out data/processed --price-adjustment pre_adjusted
python -m v5.cli validate-research examples/bank_value_15y_strategy.json data/processed/bank_value_15y/panel.csv --out validation
python -m v5.cli local-backtest examples/bank_value_15y_strategy.json data/processed/bank_value_15y/panel.csv --out local_backtests
```

The local database lives in `数据库/`. `collect-dividends` writes real cash dividend data to `数据库/processed/bank_cash_dividends.csv`. `collect-data` automatically uses that file when it exists unless `--dividend-csv` is provided explicitly.

`collect-benchmarks` writes real bank benchmark data to `数据库/processed/bank_benchmarks.csv`. `collect-data` automatically uses `bank_etf_512800_qfq` as the default tradable benchmark when that file exists; use `--benchmark-id csi_bank_399986` to compare against the bank index instead.

The data panel records `price_adjustment`, `price_return`, `dividend_return`, `total_return`, `return_source`, `benchmark_return`, and `benchmark_source`. Validation and local backtests prefer `total_return` and fall back to legacy `future_return` only for old panels.

`collect-data` defaults to `--total-return-mode adjusted_total_return`. This is the correct comparison mode when migrated prices are already adjusted, because adding cash dividends again can double-count distributions. When a raw unadjusted price source is confirmed, use `--total-return-mode price_plus_net_cash_dividend`; V5 applies the JoinQuant-style default dividend tax assumption with `--dividend-tax-rate 0.2`.

For JoinQuant execution-matching local backtests, collect real unadjusted daily prices and cash-dividend events first:

```powershell
$env:JQDATA_USERNAME="..."
$env:JQDATA_PASSWORD="..."
$env:PYTHONPATH="src"
python -m v5.cli collect-joinquant-real-data data/processed_adjusted/bank_value_15y/panel.csv --database-dir 数据库 --start-date 2021-05-01 --end-date 2026-05-31
python -m v5.cli daily-backtest examples/bank_value_15y_strategy.json data/processed_adjusted/bank_value_15y/panel.csv --execution-price-csv 数据库/processed/joinquant_real_daily_prices.csv --benchmark-csv 数据库/processed/joinquant_real_benchmark_prices.csv --benchmark-id 512800.XSHG --dividend-cash-csv 数据库/processed/joinquant_cash_dividends.csv --out local_daily_backtests
```

The JoinQuant real-data collector writes `fq=None` daily stock open/close, `512800.XSHG` open/close, ex-dividend/payment cash events, and net cash dividends after the configured dividend tax rate. Credentials are read only from environment variables or an existing authenticated `jqdatasdk` session and are never persisted.

`local-backtest` defaults to the V4 comparison window: `2021-05-01` to `2026-05-31`. Use `--start-date` and `--end-date` only when a different research window is required.

`local-backtest` also defaults to `--min-coverage-ratio 0.8`. A rebalance period is skipped when its security count is below 80% of the maximum date coverage in the selected window.

Use `--save-periods` and `--save-holdings` on `local-backtest` only when detailed period returns or holding files are needed.

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
