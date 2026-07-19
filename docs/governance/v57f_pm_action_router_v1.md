# V5.7f PM Action Router V1

## Purpose

The PM action router converts the V5.7f governance dashboard into a single operational instruction for the next agent loop.

It answers:

- Should the agent continue working now?
- Which agent owns the next action?
- Is user input required?
- What event should restart the loop?

## Current Route

- Strategy: `dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f`
- Dashboard status: `frozen_candidate_waiting_for_future_paper_window_platform_deferred`
- Route status: `no_action_until_external_event`
- PM decision: `hold_frozen_candidate`
- Continue agent loop: `false`
- User decision required: `false`
- Next owner: `Project Manager Agent`
- Next trigger: `2026-10-08 refresh window or JoinQuant exports supplied by user`

## Why This Matters

V5.7f is already frozen as a formal ETF-style candidate. In the current window, further work cannot create clean new evidence unless one of two events happens:

- The future paper-trading data refresh window opens before the `2026-10-08` rebalance gate.
- The user supplies JoinQuant daily returns, trades, positions and logs for platform attribution.

Without either event, continuing the loop would only repeat the same conclusion and increase the risk of accidental tuning.

## Generated Evidence

- Runner: `src/v5/basket_pm_action_router_runner.py`
- Tests: `tests/test_basket_pm_action_router_runner.py`
- Route summary: `basket_pm_action_routes_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/basket_pm_action_route_summary.json`
- Route report: `basket_pm_action_routes_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/basket_pm_action_route_report.md`

## PM Rule

The route is a control-plane artifact only. It must not refresh data, run JoinQuant, tune parameters, change basket construction, or generate a new signal.

Allowed restart conditions:

- `2026-10-08` refresh window opens.
- User supplies JoinQuant exports for platform attribution.
- A separate PM decision starts a new candidate lane outside V5.7f.
