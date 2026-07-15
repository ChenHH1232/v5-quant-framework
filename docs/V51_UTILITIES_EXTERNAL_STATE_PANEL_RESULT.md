# V5.1 Utilities External State Panel Result

Date: 2026-07-16

Owner:

Engineering Agent

Scope:

```text
external_state_data_enrichment
```

Output:

```text
database_root/processed/utilities_external_state/utilities_external_state.csv
```

Windows note:

```text
Prefer the CLI default output path for this runner. Passing Chinese paths through PowerShell can display incorrectly on some terminals.
```

## Result

The first utilities external state panel has been populated and validated.

Validation:

```text
row_count = 731
pit_usable_count = 731
status = pass
```

## Current Coverage

| Metric | Rows | Use |
| --- | ---: | --- |
| electricity_consumption_cumulative | 239 | all-power demand state |
| electricity_consumption_yoy | 239 | all-power demand growth |
| secondary_industry_electricity_yoy | 239 | industrial power demand proxy |
| generation_utilization_hours_total | 4 | sparse power utilization anchor |
| thermal_capacity | 2 | sparse thermal capacity anchor |
| hydro_capacity | 2 | sparse hydropower capacity anchor |
| nuclear_capacity | 2 | sparse nuclear capacity anchor |
| thermal_utilization_hours | 1 | sparse thermal utilization anchor |
| hydro_utilization_hours | 1 | sparse hydropower utilization anchor |
| power_supply_coal_consumption_rate | 1 | sparse fuel-efficiency anchor |
| heating_coal_consumption | 1 | sparse thermal coal-use anchor |

## Source Policy

Monthly electricity demand rows:

```text
AkShare macro_china_society_electricity
```

PIT policy:

```text
visible_date = 25th day of the next month
```

This is conservative, but it is still marked:

```text
review_status = conservative_proxy
```

because AkShare does not expose a row-level official publication URL.

NEA rows:

```text
National Energy Administration public releases
```

PIT policy:

```text
visible_date = official publication date
```

These are marked:

```text
review_status = source_anchored
```

## What This Enables

Quant Validation Agent may now test demand-state questions, for example:

- Does low PB work better when electricity demand growth is weak?
- Does operating cash-flow yield work better when electricity demand growth is strong?
- Does industrial electricity demand change the relative value of thermal power operators?

## What This Does Not Yet Enable

Do not yet score strategies using:

- coal-price regime;
- tariff regime;
- hydropower water condition;
- gas tariff / margin state.

Those variables still need broader PIT source collection.

## PM Gate

The current external state panel is enough for:

```text
demand_state_research_validation
```

It is not enough for:

```text
formal_strategy_candidate
platform_replication
accepted_strategy
```
