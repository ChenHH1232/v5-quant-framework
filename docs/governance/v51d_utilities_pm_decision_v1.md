# Governance Record: v51d_utilities_pm_decision_v1

Date: 2026-07-16

Layer:

```text
research_pit_validation
```

Current status:

```text
research_pit_validation_completed_rejected_for_now
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## PM Decision

Quant Validation Agent completed V5.1d conditional validation.

V5.1d is rejected for formal candidate promotion.

## Why

The best conditional cases do not beat the two strongest raw baselines:

- `raw_low_pb_utilities_top10`;
- `raw_cashflow_yield_utilities_top10`.

The V5.1 series now has enough evidence to stop static composite testing for utilities.

## Approved Next Step

Engineering Agent may continue data-pipeline work only:

```text
populate_utilities_external_state_panel
```

Quant Validation Agent may continue only after external variables have PIT-visible dates.

## Blocked

- no JoinQuant code;
- no platform replication;
- no accepted strategy label.
