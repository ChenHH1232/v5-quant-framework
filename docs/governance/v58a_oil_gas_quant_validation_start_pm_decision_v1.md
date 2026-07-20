# V5.8a Oil / Gas Quant Validation Start PM Decision V1

Date: 2026-07-20

Owner:

```text
Project Manager Agent
```

Layer:

```text
research_pit_validation
```

## PM Decision

V5.8a oil / gas has passed the minimum data gate to start preliminary Quant validation.

It has not passed the gate for Engineering handoff, platform replication, paper trading or accepted-strategy status.

Current status:

```text
research_pit_validation_started
test1_formal_validation_completed
research_signal_exists_needs_redesign
not_engineering_handoff
not_platform_replication
not_accepted_strategy
```

## What Changed

The prior blocker was:

```text
no PIT universe, no cycle-state data, no business-exposure tags
```

The repaired Test-1 input now has:

| Input | Status |
| --- | --- |
| PIT oil/gas candidate universe | collected |
| cycle-state proxy panel | preliminary ready |
| business-exposure PIT proxy | preliminary ready |
| low-volatility factors | collected |
| formal validation spec | config validation passed |
| formal validation packet | completed |

## Evidence

Input files:

```text
数据库/processed/oil_gas_external_state_v58a/oil_gas_external_state.csv
数据库/processed/oil_gas_external_state_v58a/collection_manifest.json
数据库/processed/oil_gas_formal_panel_v58a/panel.csv
数据库/processed/oil_gas_formal_panel_v58a/collection_manifest.json
数据库/processed/oil_gas_low_vol_panel_v58a/oil_gas_ocf_dividend_cycle_probe_v58a/panel_with_low_vol.csv
数据库/processed/oil_gas_low_vol_panel_v58a/oil_gas_ocf_dividend_cycle_probe_v58a/low_volatility_factor_manifest.json
examples/oil_gas_ocf_dividend_cycle_probe_v58a_strategy.json
```

Validation packet:

```text
validation_formal_v58a_oil_gas/oil_gas_ocf_dividend_cycle_probe_v58a/formal_validation_summary.json
validation_formal_v58a_oil_gas/oil_gas_ocf_dividend_cycle_probe_v58a/formal_validation_report.md
```

## Test-1 Result

Baseline results:

| Case | Cumulative Return | Positive Ratio |
| --- | ---: | ---: |
| equal-weight oil/gas pool | 39.26% | 61.11% |
| high OCF yield top8 | 80.38% | 72.22% |
| low-vol top8 | 47.41% | 72.22% |
| high-dividend top8 | 16.51% | 61.11% |
| OCF + dividend + low-vol composite top8 | 46.06% | 61.11% |

Factor IC / RankIC:

| Factor | Mean IC | Mean RankIC | PM Read |
| --- | ---: | ---: | --- |
| operating_cash_flow_yield | 0.0919 | 0.1111 | strongest preliminary evidence |
| low_vol_score | 0.0552 | 0.1191 | useful risk signal, but return spread is weak |
| dividend_yield | 0.0569 | 0.0314 | support variable only |
| low_price_to_book | 0.0711 | 0.0994 | mild valuation evidence |
| pe_ratio | 0.0912 | 0.0931 | useful but cyclical earnings risk remains |
| capex_burden | -0.0124 | 0.0311 | not promotable as positive guard |
| free_cash_flow_yield | 0.0424 | 0.0712 | diagnostic only |

Rolling validation:

| Year | Cumulative Return | PM Read |
| --- | ---: | --- |
| 2024 | 2.86% | weak but positive |
| 2025 | 28.55% | strong |
| 2026 | -8.44% | unresolved failure |

## PM Interpretation

The most important result is not the composite return. The important result is:

```text
OCF has the clearest evidence. Low-vol is supportive. Dividend is not enough by itself. FCF should remain diagnostic.
```

The current composite underperforms the OCF-only baseline, so it must not be promoted. This is similar to earlier V5 lessons: a richer story is not automatically a better model.

## Remaining Blockers

Before Engineering Agent can receive the strategy:

1. Replace or confirm futures proxies with official / reviewed oil, gas, product and spread data.
2. Review annual-report segment evidence for upstream, refining, pipeline / LNG / storage, retail and non-core exposure.
3. Explain 2026 failure mode.
4. Decide whether the next hypothesis should be OCF-led rather than dividend-led.
5. Keep FCF diagnostic until capex-cycle meaning is reviewed.
6. Add cash dividend events before local daily simulation.

## Next Owner

```text
Research Agent -> Quant Validation Agent loop
```

Allowed next action:

```text
redesign V5.8b around OCF-led oil/gas value with low-vol support and state-bucket diagnostics
```

Forbidden action:

```text
do not write JoinQuant code
do not run platform replication
do not add oil/gas to frozen V5.7f
do not tune from 2021-2026 return
```

Historical performance alone is never sufficient evidence for accepting a strategy.
