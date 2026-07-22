# Basket PM Action Route: dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f

- Dashboard status: `needs_pm_review`
- Route status: `no_action_until_external_event`
- PM decision: `hold_frozen_candidate`
- Continue agent loop: `False`
- User decision required: `False`
- Next owner: `Project Manager Agent`
- Allowed next action: `wait_for_future_refresh_window_or_user_supplied_platform_exports`
- Next trigger: `2026-10-08 refresh window or JoinQuant exports supplied by user`

## Key Dates

- next_rebalance_date: `2026-10-08`
- last_recorded_signal_date: `2026-04-01`
- dashboard_as_of_date: `2026-07-20`

## Source Statuses

- pm_gate: `formal_candidate_paper_tracking_started_needs_review`
- platform_export_intake: `missing`
- forward_paper_gate: `pending_clean_future_rebalance`
- paper_input_preflight: `pending_future_data_window`
- paper_refresh_queue: `queued_for_future_refresh_window`
- paper_refresh_status: `waiting_for_future_refresh_window`

## Blocked Actions

- `accepted_strategy`
- `live_trading_approved`
- `return_tuning`
- `platform_replication_passed_without_exports`
- `late_recorded_clean_paper_signal`

## PM Rule

The PM router may only route existing evidence; it must not refresh data, run JoinQuant, tune parameters, or generate a signal.