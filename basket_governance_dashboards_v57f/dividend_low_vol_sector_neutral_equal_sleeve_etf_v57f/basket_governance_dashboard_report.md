# Basket Governance Dashboard: dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f

- Status: `frozen_candidate_waiting_for_future_paper_window_platform_deferred`
- Blockers: `0`
- Needs review: `0`
- Next gate: `wait_until_refresh_window_or_user_supplies_platform_exports`

## Key Dates

- next_rebalance_date: `2026-10-08`
- last_recorded_signal_date: `2026-07-01`
- dashboard_as_of_date: `2026-07-20`

## Source Statuses

- pm_gate: `formal_candidate_pending_platform_exports`
- platform_export_intake: `platform_test_deferred_by_user_waiting_for_exports`
- forward_paper_gate: `pending_clean_future_rebalance`
- paper_input_preflight: `pending_future_data_window`
- paper_refresh_queue: `queued_for_future_refresh_window`
- paper_refresh_status: `waiting_for_future_refresh_window`

## Checks

- `pass` pm_gate: PM gate status is formal_candidate_pending_platform_exports.
- `pass` platform_export_intake: Platform test is explicitly deferred by user.
- `pass` forward_paper_gate: Next clean rebalance is 2026-10-08.
- `pass` paper_input_preflight: Paper input preflight is waiting for the future data window.
- `pass` paper_refresh_queue: Refresh queue has 15 tasks queued.
- `pass` paper_refresh_status: Refresh status is waiting for future window with no blockers.

## PM Rule

Historical performance alone is never sufficient evidence for accepting a strategy.