# Utilities External State Panel V1

Date: 2026-07-16

Status:

```text
external_state_panel_populated_initial
```

## What Was Added

First PIT-structured utilities external state panel:

```text
database_root/processed/utilities_external_state/utilities_external_state.csv
```

Rows:

```text
731
```

All rows have visible dates and pass structural validation.

## Current Useful Layer

The panel is currently strongest for electricity-demand state:

- total social electricity consumption;
- total social electricity consumption YoY;
- secondary-industry electricity consumption YoY.

## Current Weak Layer

Fuel-cost, tariff, hydrology and gas-margin state are not yet broad enough for scoring.

## Research Implication

Next utilities validation should test demand-state conditioning before returning to strategy-candidate attempts.
