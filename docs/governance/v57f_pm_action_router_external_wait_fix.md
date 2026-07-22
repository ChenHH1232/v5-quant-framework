# V57f PM Action Router External-Wait Fix

Date: 2026-07-22

Owner: Project Manager Agent

## Purpose

The V57f governance dashboard correctly reports `needs_pm_review` because JoinQuant platform exports are missing. However, this is not an ambiguous PM state when the user has deferred actual platform testing and the clean paper refresh is still waiting for the future 2026-10-08 window.

The action router now recognizes this pattern and routes V57f to:

```text
no_action_until_external_event
```

## Routing Rule

When all conditions are true:

- dashboard status is `needs_pm_review`;
- platform export intake is `missing` or explicitly deferred;
- forward paper gate is `pending_clean_future_rebalance`;
- paper input preflight is `pending_future_data_window`;
- paper refresh queue is `queued_for_future_refresh_window`;
- paper refresh status is `waiting_for_future_refresh_window`;

then the PM decision is:

```text
hold_frozen_candidate
```

## Current V57f Result

- Route status: `no_action_until_external_event`
- PM decision: `hold_frozen_candidate`
- Continue agent loop: `false`
- User decision required: `false`
- Next trigger: `2026-10-08 refresh window or JoinQuant exports supplied by user`

## Blocked Actions

- `accepted_strategy`
- `live_trading_approved`
- `return_tuning`
- `platform_replication_passed_without_exports`
- `late_recorded_clean_paper_signal`

This prevents PM from repeatedly asking for action while also preventing silent strategy promotion.

