# V5.1 Utilities External State Next Steps

Date: 2026-07-16

Owner:

Engineering Agent

Scope:

```text
external_state_data_enrichment
```

## Goal

Populate a PIT-usable utilities external state panel before any new utilities strategy candidate is tested.

Template:

```text
数据库/processed/utilities_external_state/utilities_external_state_template.csv
```

## Required Fields

Each row must include:

- `visible_date`;
- `state_date`;
- `state_scope`;
- `sub_industry`;
- `metric`;
- `value`;
- `unit`;
- `source_name`;
- `source_url`;
- `source_publication_date`;
- `pit_usable`;
- `review_status`;
- `notes`.

## Priority Metrics

### Thermal Power

- coal price / fuel-cost proxy;
- thermal utilization hours;
- marketized power price / tariff proxy.

### Hydropower

- hydro utilization hours;
- water-condition or inflow proxy if available.

### Gas

- gas tariff or margin proxy;
- gas purchase-cost proxy if available.

### All Power Operators

- national electricity demand growth;
- marketized electricity trading price or tariff policy proxy.

## Source Rules

Allowed:

- official regulator releases;
- official statistics;
- industry association reports;
- company disclosures;
- manually reviewed research report data if visible date is clear.

Not allowed:

- joining annual data to historical dates before publication;
- using future reports to fill earlier state;
- using unsourced web snippets;
- using market commentary as a numeric data source.

## Validation Command

After the panel is populated:

```powershell
python -m v5.cli utilities-external-state validate 数据库\processed\utilities_external_state\utilities_external_state.csv
```

## PM Gate

Quant Validation Agent may resume utilities modeling only after:

```text
utilities_external_state_panel.status = pass
```

and coverage is sufficient for at least thermal, hydro, gas and water subgroups.
