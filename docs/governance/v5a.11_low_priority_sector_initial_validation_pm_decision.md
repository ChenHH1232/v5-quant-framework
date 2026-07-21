# V5a.11 Low-Priority Sector Initial Validation PM Decision

Date: 2026-07-21

## Decision

V5a.11 completed a low-cost batch screen for seven low-priority observation sectors:

- securities brokerage;
- basic chemicals;
- textile / apparel;
- logistics / express;
- retail / commerce;
- auto and parts;
- machinery / equipment.

This is research PIT validation only. No sector is approved for Engineering handoff, platform replication or paper trading.

## What Was Added

The common similar-sector PIT collector now supports the seven observation sectors and exports daily close prices for low-volatility factor construction.

Evidence:

```text
数据库/processed/similar_sector_pit_panel_v5a11/
数据库/processed/low_volatility_factors_v5a11/
validation_formal_v5a11_low_priority_initial/
validation_formal_v5a11_low_priority_lowvol/
```

## Initial Screen Result

First pass without low-volatility found three possible research signals:

| Sector | PM read |
| --- | --- |
| Securities brokerage | Research signal candidate, but financial-market beta specialist |
| Auto and parts | Research signal candidate before low-volatility repair |
| Machinery / equipment | Research signal candidate before low-volatility repair |

Rejected or unstable:

| Sector | PM read |
| --- | --- |
| Basic chemicals | Composite not superior to same-pool benchmark |
| Textile / apparel | Unstable rolling result |
| Logistics / express | Unstable rolling result |
| Retail / commerce | Composite not superior to same-pool benchmark |

## Low-Volatility Repair Result

After adding PIT-safe 60/120/252 day low-volatility factors, only securities brokerage remained a research signal:

| Sector | Equal weight | Composite | Low-vol | PM decision |
| --- | ---: | ---: | ---: | --- |
| Securities brokerage | `6.18%` | `46.87%` | `26.47%` | Research signal only; specialist state gate required |
| Auto and parts | `84.46%` | `67.37%` | `45.16%` | Rejected; composite not superior |
| Machinery / equipment | `127.31%` | `118.31%` | `100.71%` | Rejected; composite not superior |

## PM Interpretation

Securities brokerage is not a clean dividend low-volatility and OCF/FCF sleeve. Its evidence is more consistent with a financial-market-cycle value / dividend signal.

Therefore:

```text
Do not add securities brokerage to V5.7f / enhanced ETF mainline.
```

It can remain a specialist observation candidate only if Research Agent builds:

- equity-market turnover / trading-volume state;
- risk appetite / index drawdown state;
- brokerage balance-sheet and proprietary-investment exposure fields;
- dividend sustainability under market-cycle stress.

Auto and machinery should not continue through the current enhanced-ETF queue. They may be revisited only under a separate manufacturing-cycle framework with order backlog, inventory and downstream capex states.

## Queue Result

The broad observation queue is now cleaner:

- `securities_brokerage`: research signal only, specialist state gate required.
- `auto_and_parts`: initial composite rejected after low-volatility repair.
- `machinery_equipment`: initial composite rejected after low-volatility repair.
- `chemical_materials`: rejected / cycle data gate required.
- `textile_apparel`: unstable, watchlist only.
- `logistics_express`: unstable, watchlist only.
- `retail_commerce`: rejected.

No V5a.11 strategy is accepted, platform-ready, paper-trading-ready or Engineering-ready.
