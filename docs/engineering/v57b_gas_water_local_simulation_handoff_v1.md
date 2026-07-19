# V5.7b Gas / Water Local Simulation Engineering Handoff V1

Date: 2026-07-19

Strategy:

```text
gas_water_value_serviceability_v57b
```

Engineering status:

```text
local_joinquant_style_simulation_ready
platform_replication_pending
```

## Engineering Scope

Engineering Agent may work on:

```text
local JoinQuant-style simulation
signal / trade / holding / dividend log inspection
platform replication preparation packet
```

Engineering Agent must not work on:

```text
factor tuning
coverage threshold tuning
receivables guard insertion
formal JoinQuant script generation
paper trading signal
accepted strategy promotion
```

## Frozen Inputs

| Item | Path |
| --- | --- |
| Strategy spec | `examples/gas_water_value_serviceability_v57b_strategy.json` |
| PIT panel | `数据库/processed/gas_water_financial_evidence_v57/panel_with_direct_financial_evidence.csv` |
| Business purity panel | `数据库/processed/gas_water_operating_evidence_v57/business_purity_panel/panel_business_purity_passed.csv` |
| Real JQ daily prices | `数据库/processed/gas_water_v57b_joinquant_real_daily_prices.csv` |
| Real JQ cash dividends | `数据库/processed/gas_water_v57b_joinquant_cash_dividends.csv` |
| Same-pool benchmark | `数据库/processed/gas_water_v57b_same_pool_equal_weight_benchmark.csv` |
| Overfit audit | `validation_overfit_v57_gas_water/gas_water_value_serviceability_v57b/overfit_audit_summary.json` |
| Platform packet | `platform_replication_packets_v57_gas_water/gas_water_value_serviceability_v57b/platform_replication_packet.json` |

## Frozen Command Profile

```text
python -m v5.cli daily-backtest
examples/gas_water_value_serviceability_v57b_strategy.json
数据库/processed/gas_water_financial_evidence_v57/panel_with_direct_financial_evidence.csv
--benchmark-csv 数据库/processed/gas_water_v57b_same_pool_equal_weight_benchmark.csv
--benchmark-id gas_water_same_pool_equal_weight
--execution-price-csv 数据库/processed/gas_water_v57b_joinquant_real_daily_prices.csv
--dividend-cash-csv 数据库/processed/gas_water_v57b_joinquant_cash_dividends.csv
--out local_daily_backtests_v57_gas_water
--start-date 2021-05-01
--end-date 2026-05-31
--min-coverage-ratio 0.8
--initial-cash 2000000
--target-exposure 0.995
--experiment-layer engineering_smoke_test
--value-trap-guard-mode disabled
```

## Local Simulation Result

Output directory:

```text
local_daily_backtests_v57_gas_water/gas_water_value_serviceability_v57b/
```

| Metric | Value |
| --- | ---: |
| Strategy return | 27.85% |
| Annualized return | 5.17% |
| Same-pool benchmark return | 32.69% |
| Excess return | -4.85% |
| Max drawdown | 26.55% |
| Signal count | 19 |
| Trade records | 223 |
| Portfolio dividend events | 50 |

## Known Engineering Notes

1. The first signal is 2021-10-08 because the frozen 80% coverage gate skips 2021-07-01.
2. The 70% coverage diagnostic is not allowed in formal engineering unless PM reopens the coverage policy.
3. The benchmark is an internal same-pool equal-weight benchmark; no formal JoinQuant gas/water sector benchmark has been confirmed.
4. The current simulation uses daily open execution as a JoinQuant approximation; a platform script at 09:40 may have small execution differences.
5. Dividends are added as tax-adjusted cash events using JQ `STK_XR_XD`, with 20% tax.

## Current Platform Packet Status

```text
pending_attribution
```

Reason:

```text
No JoinQuant daily result, transaction CSV or position CSV has been exported yet.
```

Coverage check:

```text
passed
```

Meaning:

```text
Local PIT panel and local rebalance signals cover the frozen expected rebalance dates.
```

## Next Engineering Gate

Engineering Agent may improve:

1. Local report readability.
2. Same-pool benchmark total-return treatment.
3. Platform export checklist.
4. Daily attribution tooling once platform exports exist.

Engineering Agent must wait for PM approval before:

```text
writing a formal JoinQuant platform script
```
