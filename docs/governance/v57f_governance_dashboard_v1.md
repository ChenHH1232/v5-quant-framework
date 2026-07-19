# V5.7f Governance Dashboard V1

## Purpose

This dashboard is the Project Manager Agent's consolidated readout for `dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f`.

It prevents three kinds of workflow drift:

- Treating a frozen candidate as an accepted strategy.
- Mistaking a deferred JoinQuant platform test for a failed platform replication.
- Generating a late "clean paper" signal from data that was not refreshed before the target rebalance gate.

## Current PM Status

- Strategy status: `formal_etf_candidate`
- Dashboard status: `frozen_candidate_waiting_for_future_paper_window_platform_deferred`
- Experiment layer: `pm_decision_gate`
- Blockers: `0`
- Needs review: `0`
- Last recorded signal date: `2026-07-01`
- Next clean rebalance gate: `2026-10-08`

## Inputs Included

- PM gate summary: `pm_gate_packets_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/basket_pm_gate_summary.json`
- Platform export intake: `platform_export_intake_checks_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/platform_export_intake_summary.json`
- Forward paper gate: `paper_trading_gates_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/forward_paper_gate_summary.json`
- Paper input preflight: `paper_input_preflight_checks_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/paper_input_preflight_summary.json`
- Paper refresh queue: `paper_refresh_queues_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/paper_refresh_task_queue_summary.json`
- Paper refresh status: `paper_refresh_status_checks_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/paper_refresh_task_status_summary.json`

## Generated Evidence

- Dashboard summary: `basket_governance_dashboards_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/basket_governance_dashboard_summary.json`
- Dashboard report: `basket_governance_dashboards_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/basket_governance_dashboard_report.md`
- Dashboard runner: `src/v5/basket_governance_dashboard_runner.py`
- Dashboard tests: `tests/test_basket_governance_dashboard_runner.py`

## PM Decision

V5.7f stays frozen. No return tuning, no factor-weight change, no sleeve change, no new JoinQuant run, and no clean paper signal generation are allowed in the current window.

The only allowed next actions are:

- Wait until the `2026-10-08` refresh window and execute the queued data-refresh tasks before generating a clean paper signal.
- If the user later supplies JoinQuant daily returns, transactions, positions and logs, run platform attribution without changing the model.

## Blocked Actions

- `accepted_strategy`
- `live_trading_approved`
- `return_tuning`
- `platform_replication_passed_without_exports`
- `late_recorded_clean_paper_signal`

## Next Gate

`wait_until_refresh_window_or_user_supplies_platform_exports`

Historical performance alone is never sufficient evidence for accepting a strategy.
