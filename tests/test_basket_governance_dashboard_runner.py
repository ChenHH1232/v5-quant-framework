from __future__ import annotations

import json
from pathlib import Path

from v5.basket_governance_dashboard_runner import build_basket_governance_dashboard


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_governance_dashboard_waits_when_platform_deferred_and_paper_future(tmp_path: Path) -> None:
    pm = _write_json(tmp_path / "pm.json", {"status": "formal_candidate_pending_platform_exports", "blocker_count": 0})
    platform = _write_json(tmp_path / "platform.json", {"status": "platform_test_deferred_by_user_waiting_for_exports"})
    forward = _write_json(tmp_path / "forward.json", {"status": "pending_clean_future_rebalance", "next_rebalance_date": "2026-10-08"})
    preflight = _write_json(tmp_path / "preflight.json", {"status": "pending_future_data_window", "target_rebalance_date": "2026-10-08"})
    queue = _write_json(tmp_path / "queue.json", {"status": "queued_for_future_refresh_window", "task_count": 15})
    refresh = _write_json(tmp_path / "refresh.json", {"status": "waiting_for_future_refresh_window", "as_of_date": "2026-07-20"})

    result = build_basket_governance_dashboard(
        strategy_id="test",
        out_dir=tmp_path / "out",
        pm_gate_summary=pm,
        platform_export_intake_summary=platform,
        forward_paper_gate_summary=forward,
        paper_input_preflight_summary=preflight,
        paper_refresh_queue_summary=queue,
        paper_refresh_status_summary=refresh,
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "frozen_candidate_waiting_for_future_paper_window_platform_deferred"
    assert summary["blocker_count"] == 0
    assert summary["next_gate"] == "wait_until_refresh_window_or_user_supplies_platform_exports"


def test_governance_dashboard_blocks_on_pm_gate_blocker(tmp_path: Path) -> None:
    pm = _write_json(tmp_path / "pm.json", {"status": "blocked", "blocker_count": 1})

    result = build_basket_governance_dashboard(
        strategy_id="test",
        out_dir=tmp_path / "out",
        pm_gate_summary=pm,
    )

    assert result.status == "blocked"
    assert result.blocker_count == 1
