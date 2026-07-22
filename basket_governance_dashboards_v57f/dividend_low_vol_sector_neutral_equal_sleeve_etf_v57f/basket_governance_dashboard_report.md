# Basket Governance Dashboard: dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f

- Status: `needs_pm_review`
- Blockers: `0`
- Needs review: `1`
- Next gate: `pm_review_missing_or_needs_review_items`

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

## Checks

- `pass` pm_gate: PM gate status is formal_candidate_paper_tracking_started_needs_review.
- `needs_review` platform_export_intake: Platform export intake summary is missing.
- `pass` forward_paper_gate: Next clean rebalance is 2026-10-08.
- `pass` paper_input_preflight: Paper input preflight is waiting for the future data window.
- `pass` paper_refresh_queue: Refresh queue has 15 tasks queued.
- `pass` paper_refresh_status: Refresh status is waiting for future window with no blockers.

## PM Rule

Historical performance alone is never sufficient evidence for accepting a strategy.