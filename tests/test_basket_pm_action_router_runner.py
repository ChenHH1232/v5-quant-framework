from __future__ import annotations

import json
from pathlib import Path

from v5.basket_pm_action_router_runner import route_basket_pm_action


def _write_dashboard(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_pm_action_router_stops_until_future_window_when_v57f_is_waiting(tmp_path: Path) -> None:
    dashboard = _write_dashboard(
        tmp_path / "dashboard.json",
        {
            "strategy_id": "v57f",
            "status": "frozen_candidate_waiting_for_future_paper_window_platform_deferred",
            "source_statuses": {
                "platform_export_intake": "platform_test_deferred_by_user_waiting_for_exports",
                "paper_refresh_status": "waiting_for_future_refresh_window",
                "paper_input_preflight": "pending_future_data_window",
            },
            "key_dates": {"next_rebalance_date": "2026-10-08"},
            "blocked_actions": ["return_tuning"],
        },
    )

    result = route_basket_pm_action(governance_dashboard_summary=dashboard, out_dir=tmp_path / "out")

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.route_status == "no_action_until_external_event"
    assert result.should_continue_agent_loop is False
    assert result.user_decision_required is False
    assert summary["allowed_next_action"] == "wait_for_future_refresh_window_or_user_supplied_platform_exports"


def test_pm_action_router_routes_ready_exports_to_engineering_attribution(tmp_path: Path) -> None:
    dashboard = _write_dashboard(
        tmp_path / "dashboard.json",
        {
            "strategy_id": "v57f",
            "status": "needs_pm_review",
            "source_statuses": {
                "platform_export_intake": "ready_for_platform_attribution",
                "paper_refresh_status": "waiting_for_future_refresh_window",
            },
            "key_dates": {"next_rebalance_date": "2026-10-08"},
        },
    )

    result = route_basket_pm_action(governance_dashboard_summary=dashboard, out_dir=tmp_path / "out")

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.route_status == "platform_exports_ready"
    assert result.should_continue_agent_loop is True
    assert summary["next_owner"] == "Engineering Agent"
    assert summary["pm_decision"] == "run_platform_attribution_without_tuning"
