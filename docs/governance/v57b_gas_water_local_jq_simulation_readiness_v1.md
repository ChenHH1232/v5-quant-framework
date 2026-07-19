# V5.7b Gas / Water Local JoinQuant-Style Simulation Readiness V1

Date: 2026-07-19

Strategy:

```text
gas_water_value_serviceability_v57b
```

Layer:

```text
engineering_smoke_test
```

## PM Decision

V5.7b is now worth doing local JoinQuant-style simulation and engineering debugging.

It is not yet worth writing a formal JoinQuant platform-replication script.

Status:

```text
local_joinquant_style_simulation_ready
engineering_pre_simulation_completed
not_platform_replication_ready
not_formal_strategy_candidate
not_accepted_strategy
```

Reason:

```text
Real JQ open/close prices, true JQ cash dividends, same-pool benchmark, daily returns, holdings, trades, dividends, rebalance signals and overfit audit now exist.
The remaining blocker is governance, not code: the startup coverage policy must be frozen before any platform script.
```

## Inputs Repaired

| Input | Path / Result |
| --- | --- |
| PIT panel | `数据库/processed/gas_water_financial_evidence_v57/panel_with_direct_financial_evidence.csv` |
| Real daily prices | `数据库/processed/gas_water_v57b_joinquant_real_daily_prices.csv` |
| True cash dividends | `数据库/processed/gas_water_v57b_joinquant_cash_dividends.csv` |
| Same-pool benchmark | `数据库/processed/gas_water_v57b_same_pool_equal_weight_benchmark.csv` |
| Direct financial evidence | 100% coverage for receivables, collection cash and interest-bearing debt |
| Business purity | 746 / 830 rows passed; 40 codes retained |

## Strict Engineering Smoke Test

Run:

```text
local_daily_backtests_v57_gas_water/gas_water_value_serviceability_v57b/
```

Strict coverage policy:

```text
minimum coverage ratio = 80%
```

Result:

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

Important note:

```text
2021-07-01 was skipped because the business-purity passed panel had 28 rows,
below the inherited 80% coverage threshold.
```

## Coverage Sensitivity Diagnostic

Run:

```text
local_daily_backtests_v57_gas_water_coverage_diagnostic/gas_water_value_serviceability_v57b/
```

Diagnostic coverage policy:

```text
minimum coverage ratio = 70%
```

Result:

| Metric | Value |
| --- | ---: |
| Strategy return | 79.79% |
| Annualized return | 12.79% |
| Same-pool benchmark return | 32.69% |
| Excess return | 47.10% |
| Max drawdown | 24.56% |
| Signal count | 20 |

PM interpretation:

```text
The model is highly sensitive to the 2021 startup coverage gate.
This is a data-governance issue, not a factor-weight issue.
Do not use the 70% diagnostic result as accepted evidence unless PM explicitly changes the coverage rule.
```

## Overfit Audit

Audit:

```text
validation_overfit_v57_gas_water/gas_water_value_serviceability_v57b/overfit_audit_summary.json
```

Result:

| Check | Count |
| --- | ---: |
| Blockers | 0 |
| Needs review | 2 |
| Pass | 12 |

Needs review:

1. 2021-2026 remains platform-confirmation context, not accepted-strategy evidence.
2. Parameter perturbation must be governed by formal validation / robustness tests.

## External State Evidence

Source register:

```text
knowledge/research_agent/references/gas_water_v57_external_state_source_register.csv
```

Research reports support four external-state themes:

```text
gas procurement cost / gas sales-price policy
gas pass-through and profitability stability
water tariff reform
water receivables, local fiscal pressure and financing risk
```

PIT warning:

```text
Most 2026 external-state reports were published after the 2026-01 rebalance.
They explain failure modes and generate future hypotheses, but cannot be used as ex-ante V5.7b scoring variables.
```

## PM Gate

V5.7b may proceed to:

```text
local_joinquant_style_engineering_debug
```

It may not proceed to:

```text
joinquant_platform_replication_script
formal_strategy_candidate
paper_trading
accepted_strategy
```

until PM freezes one of these coverage policies:

1. Conservative policy: keep 80% coverage and accept no 2021-07 trade.
2. Startup-repair policy: lower only the first business-purity startup gate to 70% because all rows are PIT-visible, then re-run validation and overfit audit under the same frozen rule.

## Next Action

```text
Freeze coverage policy, then generate the local simulation packet.
Only after that should Engineering Agent write a JoinQuant script.
```

Hard rule:

```text
Historical performance alone is never sufficient evidence for accepting a strategy.
```
