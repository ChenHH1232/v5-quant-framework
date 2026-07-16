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

The repository now contains the working V5 research platform:

- Structured strategy specification in JSON.
- Strict validation and research-risk audit.
- Shared scoring logic with explicit `scoring.method` validation.
- Formal validation runners for PIT leakage, baseline comparison, ablation, IC / RankIC, rolling validation, robustness, and weak-year review.
- Local daily JoinQuant-like backtests with real open / close execution prices, benchmark series, cash, trades, holdings, dividends, and daily returns.
- Platform-replication attribution for local versus JoinQuant daily returns, holdings, transactions, and rebalance signals.
- Overfit and execution audits, including sample-window, parameter, timing, leakage, and reproducibility checks.
- Sector workflow branches for banks, utilities, coal, and insurance.
- Skill and governance documents for the V5 four-agent workflow.

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

- Project Manager Agent asks: what should happen next?
- Research Agent asks: why is this worth researching?
- Quant Validation Agent asks: is there evidence to support this?
- Engineering Agent asks: how can this be implemented reliably?

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

The local database lives in `数据库`. `collect-dividends` writes real cash dividend data to `数据库/processed/bank_cash_dividends.csv`. `collect-data` automatically uses that file when it exists unless `--dividend-csv` is provided explicitly.

`collect-benchmarks` writes real benchmark data to `数据库/processed/bank_benchmarks.csv`. `collect-data` automatically uses `bank_etf_512800_qfq` as the default tradable bank benchmark when that file exists; use `--benchmark-id csi_bank_399986` to compare against the bank index instead.

The data panel records `price_adjustment`, `price_return`, `dividend_return`, `total_return`, `return_source`, `benchmark_return`, and `benchmark_source`. Validation and local backtests prefer `total_return` and fall back to legacy `future_return` only for old panels.

For JoinQuant execution-matching local backtests, collect real unadjusted daily prices and cash-dividend events first:

```powershell
$env:JQDATA_USERNAME="..."
$env:JQDATA_PASSWORD="..."
$env:PYTHONPATH="src"
python -m v5.cli collect-joinquant-real-data data/processed_adjusted/bank_value_15y/panel.csv --database-dir 数据库 --start-date 2021-05-01 --end-date 2026-05-31
python -m v5.cli daily-backtest examples/bank_value_15y_strategy.json data/processed_adjusted/bank_value_15y/panel.csv --execution-price-csv 数据库/processed/joinquant_real_daily_prices.csv --benchmark-csv 数据库/processed/joinquant_real_benchmark_prices.csv --benchmark-id 512800.XSHG --dividend-cash-csv 数据库/processed/joinquant_cash_dividends.csv --out local_daily_backtests
```

The JoinQuant real-data collector writes `fq=None` daily stock open / close, benchmark open / close, ex-dividend cash events, and net cash dividends after the configured dividend tax rate. Credentials are read only from environment variables or an existing authenticated `jqdatasdk` session and are never persisted.

`local-backtest` defaults to the V4 comparison window: `2021-05-01` to `2026-05-31`. Use `--start-date` and `--end-date` only when a different research window is required.

`local-backtest` also defaults to `--min-coverage-ratio 0.8`. A rebalance period is skipped when its security count is below 80% of the maximum date coverage in the selected window.

Use `--save-periods` and `--save-holdings` on `local-backtest` only when detailed period returns or holding files are needed.

For local development:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
```

Optional dependencies are split by use case:

```powershell
pip install -e .[data]
pip install -e .[jq]
pip install -e .[tushare]
pip install -e .[dev]
```

## Current Scope

V5 is no longer only a scaffold. The current platform supports formal PIT research validation, local JoinQuant-like daily simulation, platform-replication attribution, overfit audits, and sector-specific workflow branches.

Strategy acceptance is governed separately. A profitable backtest is never enough.

```text
natural language
    -> strategy spec
    -> research hypothesis
    -> PIT data and visibility audit
    -> formal validation packet
    -> engineering smoke test
    -> local daily simulation
    -> platform replication, if approved
    -> paper trading, if approved
    -> PM decision record
```

## Project Layout

```text
src/v5/
  spec.py                         Strategy specification model and parser
  scoring.py                      Shared scoring logic and method registry
  formal_validation_runner.py     PIT validation, baselines, IC / RankIC, ablation, robustness
  daily_backtest.py               JoinQuant-like daily execution simulator
  platform_attribution_runner.py  Local versus JoinQuant attribution
  overfit_audit_runner.py         Leakage, robustness, and overfit checks
  io_utils.py                     Shared CSV / JSON helpers
  math_utils.py                   Shared numeric, rank, correlation, and compounding helpers
  date_utils.py                   Shared date parsing helpers
  paths.py                        Shared repository data paths
  cli.py                          Thin command-line entrypoint
  cli_bank.py                     Bank data and quality-date commands
  cli_utilities.py                Utilities / electricity commands
  cli_coal.py                     Coal commands
  cli_insurance.py                Insurance commands
  cli_platform.py                 Platform replication and audit commands
  coal_data_audit_runner.py       Compatibility facade for coal data audit APIs
  coal_state_data_runner.py       Coal external-state import and merge APIs
  coal_segment_evidence_runner.py Coal segment evidence APIs
  coal_business_audit_runner.py   Coal business-tag and capex audit APIs
examples/
  bank_value_15y_strategy.json
  bank_high_dividend_sustainability_v3_strategy.json
  utilities_demand_state_v51f_strategy.json
  coal_cashflow_cycle_value_v52b_capex_policy_strategy.json
  insurance_low_pb_only_v53c_strategy.json
docs/
  RESEARCH_MANIFESTO.md
  V5_SKILL_MAP.md
  governance/status_registry.json
数据库/
  processed/
tests/
```
