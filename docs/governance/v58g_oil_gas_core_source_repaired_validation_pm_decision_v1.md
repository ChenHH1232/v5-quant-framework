# V5.8g Oil / Gas Core-Source-Repaired Validation PM Decision

Date: 2026-07-20

## Stage

Experiment layer: `research_pit_validation`

Decision: `core_source_gate_repaired_formal_validation_completed_not_engineering_handoff`

V5.8g keeps the V5.8d hypothesis frozen and reruns it with PIT-safe licensed futures state inputs from the source gate.

## What Changed

No factor weights or selection rules were tuned.

The change is data-source repair:

- `crude_oil_price_state`: Tushare licensed INE crude active futures
- `bitumen_price_state`: Tushare licensed SHFE bitumen active futures
- `gas_liquid_price_state`: Tushare licensed DCE LPG active futures
- `refining_spread_proxy_state`: Tushare licensed low-sulfur fuel-oil active futures minus converted INE crude active futures
- NBS seed remains supplementary official evidence for LNG / LPG / gasoline / diesel

Daily futures closes are treated as visible on the next calendar day. Rebalance-day closes are not used.

## Source Gate Result

Core gate status:

```text
core_state_ready_needs_promotion_sources
```

Core source coverage:

| Metric | Coverage |
| --- | ---: |
| `crude_oil_price_state` | 18 / 18 |
| `bitumen_price_state` | 18 / 18 |
| `gas_liquid_price_state` | 18 / 18 |
| `refining_spread_proxy_state` | 18 / 18 |

Promotion source coverage is still incomplete because inventory / demand and pipeline tariff / policy state are missing.

## Formal Validation Result

Panel:

```text
数据库/processed/oil_gas_state_conditioned_panel_v58g/oil_gas_state_conditioned_ocf_v58g/panel.csv
```

Summary:

| Item | Result |
| --- | ---: |
| Rows | 351 |
| Rebalance dates | 18 |
| PIT leakage audit | pass |
| Composite cumulative return | 120.94% |
| Equal-weight oil/gas pool | 39.26% |
| Raw OCF top 8 | 80.38% |
| Raw low-vol top 8 | 47.41% |
| State-conditioned OCF top 8 | 127.01% |

Key factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio |
| --- | ---: | ---: | ---: |
| `state_conditioned_ocf_score` | 0.191 | 0.215 | 66.67% |
| `cycle_defensive_low_vol_score` | 0.078 | 0.171 | 66.67% |
| `operating_cash_flow_yield` | 0.092 | 0.111 | 50.00% |
| `low_vol_score` | 0.055 | 0.119 | 50.00% |

Rolling result:

| Year | Cumulative Return |
| --- | ---: |
| 2024 | 1.17% |
| 2025 | 45.32% |
| 2026 | 6.57% |

## PM Interpretation

The core source repair is successful enough to reopen and complete Quant Validation.

The evidence supports the research claim that oil/gas OCF should be interpreted conditionally on cycle state. The state-conditioned OCF signal is stronger than raw OCF and equal-weight baselines.

However, V5.8g still cannot move to Engineering handoff because:

- refining spread is still a futures proxy, not a reviewed operating margin
- inventory / demand state is missing
- pipeline tariff / policy state is missing
- business exposure remains a JoinQuant industry proxy, not reviewed annual-report segment evidence
- cash dividend event data is not repaired
- the 2021-2026 window remains research validation / platform-confirmation context, not acceptance evidence

## PM Decision

Current status:

```text
research_pit_validation_passed_core_source_gate_repaired
```

Not allowed yet:

- Engineering handoff
- local daily simulation
- JoinQuant code
- paper trading
- accepted strategy
- V5.7f basket inclusion

## Next Owner

Research Agent.

## Next Gate

Repair the promotion data gate:

1. Add inventory / demand state.
2. Add pipeline tariff / policy state.
3. Review annual-report business exposure tags.
4. Repair cash dividend events.
5. Rerun formal validation and PM gate.

Only after those repairs can PM decide whether V5.8g becomes an Engineering preparation candidate.
