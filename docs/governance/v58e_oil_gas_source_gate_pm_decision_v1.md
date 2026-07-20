# V5.8e Oil / Gas Official Source Gate PM Decision

Date: 2026-07-20

## Stage

Experiment layer: `data_availability_gate`

Decision: `source_repair_blocked_until_reviewed_official_rows_are_imported`

V5.8e does not change the V5.8d model. It adds the data-source gate required before any further oil / gas promotion.

## What Was Added

Engineering / PM added a reusable source-gate runner for oil / gas:

- official source register
- official state import template
- source merge runner
- source gate audit
- unit tests

The source gate separates two thresholds:

| Gate | Required Metrics | Meaning |
| --- | --- | --- |
| Core state gate | `crude_oil_price_state`, `bitumen_price_state`, `gas_liquid_price_state`, `refining_spread_proxy_state` | enough to rerun state-conditioned OCF research validation |
| Promotion gate | core metrics plus `inventory_or_demand_state`, `pipeline_tariff_policy_state` | required before Engineering handoff or formal promotion |

## Current Result

The official import template was generated with 336 rows for 2021-2026.

Current audit status:

```text
source_repair_blocked
```

Coverage:

| Metric | Covered Rebalance Dates |
| --- | ---: |
| `crude_oil_price_state` | 0 / 18 |
| `bitumen_price_state` | 0 / 18 |
| `gas_liquid_price_state` | 0 / 18 |
| `refining_spread_proxy_state` | 0 / 18 |
| `inventory_or_demand_state` | 0 / 18 |
| `pipeline_tariff_policy_state` | 0 / 18 |

This is expected because the template is empty and marked `pit_usable=false`.

## Source Register

Registered source paths:

- INE crude oil futures official market data
- SHFE bitumen futures official market data
- NBS production-material price releases for LNG / LPG / gasoline / diesel
- NBS energy production / crude-processing / demand releases
- NDRC / company announcements / annual reports for pipeline tariff or policy state

Research Agent must use official export, manually reviewed public HTML/PDF, licensed vendor export, or manually entered source rows. Hidden or protected scraping is not allowed.

## PM Interpretation

V5.8d found a stronger research signal, but V5.8e confirms that the source gate is still not repaired.

This means:

- Do not tune oil / gas factors further on proxy data.
- Do not hand off to Engineering Agent.
- Do not write JoinQuant code.
- Do not add oil / gas to the V5.7f basket.
- Continue only by importing reviewed official / licensed source rows.

## Next Owner

Research Agent.

## Next Allowed Actions

1. Fill `数据库/processed/oil_gas_source_gate_v58e/oil_gas_official_state_import_template.csv` with reviewed official or licensed source rows.
2. Set `pit_usable=true` only when `visible_date`, `source_publication_date`, `source_name`, `source_url`, `value` and `review_status` are valid.
3. Rerun `audit-oil-gas-source-gate`.
4. If core coverage is at least 80%, rebuild the V5.8d/V5.8e state-conditioned panel using the repaired state source and rerun formal validation.

## Restart Condition

Oil / gas validation may continue only after core official state coverage passes the source gate.
