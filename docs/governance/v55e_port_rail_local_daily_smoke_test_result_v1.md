# V5.5e Port / Rail Local Daily Smoke Test Result V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
Engineering Agent
```

Experiment layer:

```text
engineering_smoke_test
```

Strategy:

```text
port_rail_cashflow_value_operating_diagnostic_v55c
```

## PM Result

Status:

```text
engineering_smoke_test_completed
local_daily_backtest_ready
platform_replication_still_blocked
paper_trading_still_blocked
```

The local daily simulation can now be used for engineering review. It must not be treated as platform replication or accepted-strategy evidence.

## Inputs

| Input | Path |
| --- | --- |
| frozen strategy spec | `examples/port_rail_cashflow_value_operating_diagnostic_v55c_strategy.json` |
| PIT signal panel | `数据库/processed/port_rail_operating_state_v55b/panel_operating_state.csv` |
| real daily open / close | `数据库/processed/port_rail_v55c_joinquant_real_daily_prices.csv` |
| real cash dividends | `数据库/processed/port_rail_v55c_joinquant_cash_dividends.csv` |
| engineering benchmark proxy | `数据库/processed/port_rail_v55c_joinquant_real_benchmark_prices.csv` |

Output directory:

```text
local_daily_backtests_port_rail_v55c/port_rail_cashflow_value_operating_diagnostic_v55c
```

## Generated Artifacts

| Artifact | Status |
| --- | --- |
| `summary.json` | generated |
| `RUN_MANIFEST.json` | generated |
| `daily_returns.csv` | 1228 rows |
| `holdings.csv` | 144 rows |
| `trades.csv` | 193 rows |
| `dividends.csv` | 35 rows |
| `rebalance_signals.csv` | 18 rows |

## Local Daily Metrics

Window:

```text
2021-05-01 to 2026-05-31
```

Execution assumptions:

```text
daily open execution
daily close valuation
100-share lot rounding
0.03% open / close commission
20% tax-adjusted cash dividends
no defensive overlay
value trap guard disabled because V5.5c has no approved hard guard
```

| Metric | Value |
| --- | ---: |
| Strategy return | 63.86% |
| Annualized return | 10.67% |
| Benchmark return | 17.69% |
| Excess return | 46.16% |
| Alpha | 0.0904 |
| Beta | 0.4778 |
| Sharpe | 0.6248 |
| Sortino | 0.9143 |
| Max drawdown | 20.20% |
| Max drawdown interval | 2023-05-08 to 2024-01-22 |
| Strategy volatility | 19.16% |
| Benchmark volatility | 24.14% |
| Information ratio | 0.2884 |

## Smoke Test Findings

### Passed

The local execution chain works:

```text
frozen PIT signals -> daily open execution -> cash / holdings -> dividends -> close NAV -> benchmark NAV -> logs
```

The runner generated all required review files for local engineering inspection.

### Needs Review Before Platform Replication

First rebalance signal:

```text
2022-01-04
```

The backtest window begins in 2021-05, but the V5.5c PIT panel starts at 2022-01-04. The early 2021 cash period must be reviewed before JoinQuant replication. This is likely a PIT universe / industry-coverage issue, not an order-size issue, because the first generated trades on 2022-01-04 are normal and well above the 100-share constraint.

Benchmark:

```text
516970.XSHG
```

This remains an engineering proxy only. It must not be described as a pure port / rail benchmark.

Operating evidence:

```text
0 reviewed rows in the V5.5d operating evidence template
```

Cargo throughput, container throughput, rail freight volume, tariff / pricing policy and segment revenue-share evidence remain blocked until original-source review.

## PM Decision

V5.5c may proceed to local engineering review.

V5.5c may not proceed to:

```text
JoinQuant code generation
platform replication
paper trading
accepted strategy
```

until PM resolves:

```text
2021 signal gap
operating evidence review
benchmark policy
```

## Next Gate

```text
V5.5f local daily attribution review and 2021 signal-gap diagnosis
```
