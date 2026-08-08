# Dividend Low-Vol Cash-Flow Basket Construction Report

Created at UTC: `2026-07-28T06:24:36+00:00`

## PM Decision

The first basket constructor generated shadow rebalance signals. This is not a performance result and not a strategy acceptance.

## Summary

- Signal dates: `19`
- Holdings across all signal dates: `526`

## Sector Holding Counts

- `bank`: 133
- `highway_infrastructure`: 127
- `port_rail_infrastructure`: 133
- `utilities_electricity`: 133

## First Signal Dates

- `2021-10-08`
- `2022-01-04`
- `2022-04-01`

## Startup Preload

- `deployment_date`: `2021-05-01`
- `first_tradable_date`: `2021-05-06`
- `warmup_start_date`: `2021-05-06`
- `initial_rebalance_event`: `2021-05-06`
- `startup_ready`: `False`
- `startup_blocker`: `initial_rebalance_not_generated_required_fields_or_warmup_missing`

## Hard Rule

Basket construction must be followed by formal validation, daily simulation, overfit audit, platform attribution and paper trading before acceptance.
