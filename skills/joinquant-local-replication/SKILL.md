# JoinQuant Local Replication Skill

## Purpose

Replicate a JoinQuant backtest locally as closely as possible before spending user time and credits on the JoinQuant platform.

This skill belongs to the Engineering Agent.

## When To Use

Use this skill when:

- user asks for local simulation of JoinQuant results;
- a JoinQuant strategy export needs pre-checking;
- local results differ from JoinQuant;
- daily returns, holdings, cash, trades, dividends, or benchmark behavior must be compared;
- a strategy needs `platform_replication` rather than formal research validation.

Do not use this skill to accept a research hypothesis. Platform replication is engineering evidence, not factor validation.

## Required Inputs

- strategy spec JSON;
- local factor panel;
- JoinQuant real unadjusted stock open/close data;
- JoinQuant-compatible benchmark data;
- cash dividend data;
- experiment layer;
- data visibility mode.

For Bank Value Quality V2 platform replication:

- `experiment_layer`: `platform_replication`
- `eastmoney_visibility_mode`: `joinquant_source_year`

For formal research:

- use Quant Validation skills instead;
- use `research_pit_validation`;
- use `notice_date` visibility.

## Standard Local Replication Command

```powershell
$env:PYTHONPATH='src'
python -m v5.cli daily-backtest `
  examples\bank_value_quality_v2_strategy.json `
  data\processed\bank_value_15y\panel.csv `
  --execution-price-csv 数据库\processed\joinquant_real_daily_prices.csv `
  --benchmark-csv 数据库\processed\bank_benchmarks.csv `
  --benchmark-id bank_etf_512800_qfq `
  --dividend-cash-csv 数据库\processed\joinquant_cash_dividends.csv `
  --eastmoney-quality-csv 数据库\processed\eastmoney_bank_quality_manual_csv.csv `
  --eastmoney-visibility-mode joinquant_source_year `
  --experiment-layer platform_replication `
  --snapshot-out experiments\snapshots `
  --out local_daily_backtests_v2_governed `
  --start-date 2021-05-01 `
  --end-date 2026-05-31 `
  --target-exposure 1.0
```

## Expected Outputs

The runner must produce:

- `summary.json`
- `RUN_MANIFEST.json`
- `daily_returns.csv`
- `holdings.csv`
- `trades.csv`
- `dividends.csv`
- `rebalance_signals.csv`

The automatic snapshot should be stored under:

- `experiments/snapshots/`

## JoinQuant Daily Attribution Command

After the user exports the JoinQuant daily return CSV:

```powershell
$env:PYTHONPATH='src'
python -m v5.cli platform-attribution `
  local_daily_backtests_v2_governed\bank_value_quality_v2\daily_returns.csv `
  <joinquant_daily_returns.csv> `
  --out platform_attribution `
  --strategy-id bank_value_quality_v2 `
  --local-rebalance-signals-csv local_daily_backtests_v2_governed\bank_value_quality_v2\rebalance_signals.csv `
  --local-trades-csv local_daily_backtests_v2_governed\bank_value_quality_v2\trades.csv `
  --local-dividends-csv local_daily_backtests_v2_governed\bank_value_quality_v2\dividends.csv
```

Expected attribution outputs:

- `daily_attribution.csv`
- `platform_attribution_summary.json`
- `platform_attribution_report.md`
- `local_execution_diagnostics.json`

## Required Checks

Before reporting the result:

1. Confirm `RUN_MANIFEST.json` exists.
2. Confirm experiment layer is `platform_replication`.
3. Confirm benchmark return is close to the platform benchmark.
4. Confirm `daily_returns.csv`, `holdings.csv`, `trades.csv`, `dividends.csv`, and `rebalance_signals.csv` exist.
5. State remaining known gaps.

## Known Gaps To Report

- Local runner uses daily open as execution approximation.
- JoinQuant strategy may run at 09:40 and use `current_data.last_price`.
- Benchmark may need previous-trading-day close anchor.
- Daily attribution requires the user's exported JoinQuant daily returns CSV.
- Platform replication does not replace `research_pit_validation`.

## Failure Handling

If platform replication diverges materially:

1. Compare `rebalance_signals.csv` against JoinQuant logs.
2. Compare daily benchmark returns.
3. Compare dividend dates and cash amounts.
4. Compare trades, skipped trades, and cash weights.
5. Check data visibility mode.
6. Check whether the JoinQuant code uses old pandas limitations, such as no `DataFrame.attrs`.

## Governance

This skill always operates under Engineering Agent ownership.

Project Manager Agent must prevent this skill's result from being used as strategy acceptance evidence.

