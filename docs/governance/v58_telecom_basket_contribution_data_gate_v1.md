# V5.8 Telecom Basket Contribution Data Gate V1

Date: 2026-07-19

Owner:

```text
Project Manager Agent
```

Scope:

```text
telecom_operators
```

## Gate Result

Current gate status:

```text
blocked_by_missing_local_basket_inputs
```

Telecom is allowed only as an observation sleeve, but it cannot yet enter basket-level contribution testing because required local engineering inputs are incomplete.

## Available Input

Available:

```text
数据库/processed/similar_sector_pit_panel_v55/telecom_operators/panel.csv
```

Panel facts:

| Check | Result |
| --- | ---: |
| Core operators | 3 |
| PIT rows | 52 |
| Rebalance dates | 20 |
| Formal validation exists | yes |

## Missing Inputs

Missing:

```text
数据库/processed/telecom_joinquant_real_daily_prices.csv
数据库/processed/telecom_joinquant_cash_dividends.csv
数据库/processed/low_volatility_factors_v57/telecom_operators/panel_with_low_vol.csv
```

Because these are missing, PM blocks:

```text
basket_daily_backtest
platform_replication
paper_trading_ready
joinquant_code
```

## Required Engineering Data Tasks

Before any basket contribution test:

1. Collect JoinQuant / DataJQ real daily open and close prices for the three core telecom operators.
2. Collect cash dividend events with visible dates and apply the same 20% tax treatment used by the V5 basket backtester.
3. Build PIT-safe low-volatility factors from daily closes strictly before each rebalance date.
4. Rebuild a telecom observation panel with low-vol factors joined to the existing PIT fundamentals.
5. Run leave-one-name-out and single-stock concentration diagnostics before interpreting any return.

## PM Decision

Do not move telecom into the V5.7f main basket yet.

Allowed next owner:

```text
Engineering Agent for data input repair only
```

Not allowed:

```text
strategy implementation
return tuning
standalone model promotion
```

## 2026-07-19 Engineering Data Repair Update

Engineering Agent repaired the missing local basket inputs.

New artifacts:

```text
数据库/processed/telecom_joinquant_joinquant_real_daily_prices.csv
数据库/processed/telecom_joinquant_joinquant_real_benchmark_prices.csv
数据库/processed/telecom_joinquant_joinquant_cash_dividends.csv
数据库/processed/low_volatility_factors_v58/telecom_operators/telecom_operators_cashflow_dividend_v55a/panel_with_low_vol.csv
数据库/processed/low_volatility_factors_v58/telecom_operators/telecom_operators_cashflow_dividend_v55a/low_volatility_factors.csv
数据库/processed/low_volatility_factors_v58/telecom_operators/telecom_operators_cashflow_dividend_v55a/low_volatility_factor_manifest.json
```

Coverage:

| Input | Result |
| --- | ---: |
| Real daily price rows | 3,684 |
| Price rows per telecom operator | 1,228 |
| Cash dividend rows | 26 |
| Low-vol PIT panel rows | 52 |
| Low-vol enriched rows | 51 |

Known limitation:

```text
The only missing low-vol row is 600050.XSHG on 2021-07-01, caused by insufficient pre-rebalance daily history for the configured minimum observation window.
```

Updated gate status:

```text
data_inputs_repaired_basket_contribution_diagnostic_ready
```

Allowed next action:

```text
Run telecom as a capped observation sleeve contribution diagnostic outside the V5.7f frozen main basket.
```

Still not allowed:

```text
Standalone promotion, accepted strategy status, JoinQuant strategy code, or return tuning.
```
