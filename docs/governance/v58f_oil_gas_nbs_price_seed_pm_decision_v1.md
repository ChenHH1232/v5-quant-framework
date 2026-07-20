# V5.8f Oil / Gas NBS Price Seed PM Decision

Date: 2026-07-20

## Stage

Experiment layer: `data_availability_gate`

Decision: `source_repair_progress_but_still_blocked`

V5.8f does not modify the V5.8d oil / gas model. It only repairs one official data-ingestion path for the oil / gas source gate.

## What Was Added

Engineering / PM added a reusable importer for user-specified National Bureau of Statistics production-material price release pages:

- CLI command: `import-oil-gas-nbs-price-release`
- Runner function: `import_oil_gas_nbs_price_release`
- Parser-level duplicate guard for repeated HTML tables
- Unit test covering LNG, LPG, gasoline and diesel extraction

The importer reads a specific public NBS release URL. It does not crawl historical NBS pages.

## Imported Seed

Source URL:

```text
https://www.stats.gov.cn/sj/zxfb/202606/t20260623_1963989.html
```

Imported release:

| Field | Value |
| --- | --- |
| Publication date | `2026-06-24` |
| State date | `2026-06-20` |
| Rows imported | `4` |
| Duplicate rows skipped | `4` |
| Review status | `nbs_official_reviewed` |

Imported metrics:

| NBS product | V5 metric | Use |
| --- | --- | --- |
| LNG | `domestic_gas_price_state` | supplemental domestic gas state input |
| LPG | `gas_liquid_price_state` | core gas / liquid price input |
| Gasoline | `refined_product_price_state` | refining-spread component only |
| Diesel | `refined_product_price_state` | refining-spread component only |

## Source Gate Result

Audit status remains:

```text
source_repair_blocked
```

The seed was also merged into:

```text
数据库/processed/oil_gas_source_gate_v58e/oil_gas_official_state_formal_candidate.csv
```

Here `formal_candidate` means a candidate source table for future audit, not a formal strategy candidate.

Current core coverage:

| Metric | Usable rows | Covered V5.8d rebalance dates |
| --- | ---: | ---: |
| `crude_oil_price_state` | 0 | 0 / 18 |
| `bitumen_price_state` | 0 | 0 / 18 |
| `gas_liquid_price_state` | 1 | 0 / 18 |
| `refining_spread_proxy_state` | 0 | 0 / 18 |

The LPG seed is valid, but it is dated after the 2021-2026 validation rebalance window. It therefore does not repair historical coverage.

## PM Interpretation

V5.8f proves that one official NBS public source path can be imported in a PIT-safe way.

It does not prove that the V5.8d model is ready for Engineering handoff.

The oil / gas line remains blocked because:

- crude oil official / reviewed history is missing
- bitumen official / reviewed history is missing
- gasoline and diesel rows are only refined-product inputs, not a complete refining-spread proxy
- inventory / demand state is still missing
- pipeline tariff / policy state is still missing
- one 2026 release cannot cover the 2021-2026 validation window

## PM Decision

Do not:

- tune oil / gas factors further
- start local daily simulation
- write JoinQuant code
- add oil / gas to the frozen V5.7f basket
- mark V5.8d as Engineering-ready

## Next Owner

Research Agent.

## Allowed Next Actions

1. Import reviewed official or licensed historical crude rows.
2. Import reviewed official or licensed historical bitumen rows.
3. Import enough reviewed NBS LNG / LPG / gasoline / diesel release rows to cover the validation window.
4. Build a documented refining-spread proxy only after reviewed crude and product-price inputs exist.
5. Add inventory / demand and pipeline tariff / policy state before promotion.
6. Rerun `audit-oil-gas-source-gate`.

## Restart Condition

Oil / gas research validation may restart only after the core official / reviewed source gate reaches at least 80% coverage across V5.8d rebalance dates.
