# V5.6 Basket Daily Backtest And Benchmark V1

Date: 2026-07-18

Owner:

```text
Engineering Agent, supervised by Project Manager Agent
```

Experiment layer:

```text
engineering_smoke_test
```

Status:

```text
basket_daily_backtest_completed
same_pool_total_return_benchmark_completed
bank_v3_real_daily_price_repaired
utilities_cash_dividend_events_repaired
not_platform_replication
not_accepted_strategy
```

## Purpose

This step upgrades V5.6 from shadow rebalance signals to a local basket-level daily simulation.

It includes:

- daily open-price execution;
- daily close-price valuation;
- 100-share lot handling;
- commission and minimum commission;
- cash, holdings, trades, dividends and daily returns logs;
- tax-adjusted cash dividends on pay date;
- same-pool equal-weight benchmark.

## Runner

Runner:

```text
src/v5/basket_daily_backtest_runner.py
```

CLI:

```text
python -m v5.cli daily-backtest-dividend-low-vol-fcf-basket \
  --config config/dividend_low_vol_fcf_basket_v56.json \
  --signals validation_formal_v56_basket_constructor/basket_rebalance_signals.csv \
  --out local_daily_backtests_v56_basket
```

## Output

Output directory:

```text
local_daily_backtests_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

Files:

| File | Purpose |
| --- | --- |
| `summary.json` | Metrics and execution contract |
| `daily_returns.csv` | Daily strategy, benchmark and excess returns |
| `holdings.csv` | Rebalance-date holdings and actual weights |
| `trades.csv` | Open-price orders, lot handling and commissions |
| `dividends.csv` | Net cash dividends credited to cash |
| `same_pool_equal_weight_benchmark.csv` | Same-pool equal-weight benchmark |
| `basket_daily_backtest_report.md` | PM-readable report |

## Current Basket Scope

Included:

| Sector | Status |
| --- | --- |
| Bank V3 | real daily price and low-vol panel completed |
| Utilities / electricity | low-vol panel completed; cash dividend events repaired |
| Highway infrastructure | low-vol panel completed |
| Port / rail infrastructure | low-vol panel completed |

Observation / blocked:

| Sector | Reason |
| --- | --- |
| Telecom operators | observation only, small A-share sample |
| Insurance | specialist observation sleeve |
| Gas / water | operating-purity and tariff evidence needed |
| Coal | cycle data gate blocked |

## Metrics

Current local daily smoke-test metrics:

| Metric | Value |
| --- | ---: |
| Strategy return | 73.39% |
| Annualized return | 13.12% |
| Same-pool benchmark return | 46.02% |
| Excess return | 27.37% |
| Max drawdown | 13.46% |
| Sharpe | 0.871 |
| Information ratio | 0.364 |
| Strategy volatility | 15.56% |
| Benchmark volatility | 17.65% |
| Max drawdown interval | 2022-03-03 to 2022-03-15 |
| Dividend cash events credited | 144 |

## Benchmark Policy

The benchmark is currently:

```text
same-pool equal-weight total-return benchmark where dividend data exists;
price return fallback where dividend data is missing.
```

All configured dividend files now contain at least one event:

| Dividend file | Events |
| --- | ---: |
| Bank V3 | 263 |
| Utilities / electricity | 549 |
| Highway infrastructure | 68 |
| Port / rail infrastructure | 130 |

## PM Decision

Approved:

```text
v56_basket_daily_backtest_completed
same_pool_total_return_benchmark_completed_initial_layer
bank_v3_real_daily_price_repair_completed
utilities_cash_dividend_repair_completed
```

Not approved:

```text
accepted_strategy
platform_replication_passed
paper_trading_ready
live_trading_approved
```

## Next Gate

```text
v56_basket_formal_validation_and_overfit_audit
```
