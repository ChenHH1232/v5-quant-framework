# V5.8a Oil / Gas PIT Universe And Cycle-State Data Gate V1

Date: 2026-07-20

Owner:

```text
Project Manager Agent
```

Layer:

```text
data_availability_gate
```

## PM Decision

The oil / gas line can continue at the data-gate and Research Agent preparation layer, but it cannot enter formal Quant validation yet.

Current status:

```text
pit_universe_probe_completed
initial_pit_panel_collected
cycle_state_data_missing
business_exposure_pit_missing
blocked_before_quant
```

## PIT Universe Probe

The first-layer PIT universe was collected from JoinQuant industry membership for:

| JQData industry code | Label | Initial policy |
| --- | --- | --- |
| `HY01103` | integrated_oil_gas | include |
| `HY01104` | fuel_refining | include, but needs refining-spread state |
| `HY01105` | natural_gas_processing | include, but needs gas / utility overlap review |
| `HY01106` | oil_gas_distribution_other | include, but needs business-exposure review |
| `HY01102` | oilfield_services | exclude from first pass |

Oilfield services are excluded because their economics are mainly oil-company capex beta, not dividend low-volatility cash-flow evidence.

## Probe Output

Output directory:

```text
数据库/processed/similar_sector_pit_panel_v58/oil_gas_pipeline_integrated
```

Files:

```text
panel.csv
collection_manifest.json
```

Observed coverage:

| Item | Value |
| --- | ---: |
| rows | 351 |
| effective rebalance dates | 18 |
| candidate codes | 26 |
| warnings | 0 |

Subindustry row counts:

| Subindustry | Rows |
| --- | ---: |
| oil_gas_distribution_other | 157 |
| fuel_refining | 114 |
| natural_gas_processing | 44 |
| integrated_oil_gas | 36 |

Startup coverage issue:

```text
2021-07-01 and 2021-10-08 have no effective rows after price / fundamental coverage filters.
```

This must be treated as a data coverage issue, not as a strategy signal.

## Data Meaning

The current panel is only a first-layer research probe.

It uses:

```text
jqdatasdk.get_industry_stocks(date=trade_date)
jqdatasdk.get_fundamentals(date=trade_date)
pre-adjusted close-to-close returns
same-pool equal-weight return as provisional benchmark
```

Limitations:

```text
field-level original announcement dates are not exported
cash dividends are not separately attributed
real unadjusted open / close execution prices are not joined
business-exposure PIT tags are missing
cycle-state panel is missing
```

## Required Before Quant

Research Agent must provide:

1. PIT business-exposure tags.
2. Oil price state.
3. Natural-gas price state.
4. Refining-spread state.
5. Pipeline tariff / policy state.
6. Inventory / demand state.
7. Capex-cycle classification.
8. Cash dividend visibility and tax treatment plan.

Quant Validation Agent cannot run baseline, IC / RankIC, rolling, ablation or robustness until these are joined or explicitly waived by PM.

## Forbidden Actions

Do not:

```text
run formal validation
write JoinQuant code
add oil/gas into frozen V5.7f
promote FCF as a primary oil/gas factor
accept historical return evidence
```

## Next Owner

```text
Research Agent
```

Allowed next action:

```text
collect oil/gas external-state evidence and PIT business-exposure tags
```

Historical performance alone is never sufficient evidence for accepting a strategy.
