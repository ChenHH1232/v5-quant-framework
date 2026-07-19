from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.basket_paper_refresh_status_runner import check_basket_paper_refresh_status


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _queue_rows() -> list[dict[str, str]]:
    return [
        {
            "priority": "10",
            "owner_agent": "Engineering Agent",
            "sector_id": "bank",
            "task_type": "refresh_pit_panel",
            "reason": "",
            "required_before": "2026-10-08",
            "input_path": "panel.csv",
            "completion_check": "",
            "blocked_action_until_done": "clean_paper_signal_generation",
        },
        {
            "priority": "20",
            "owner_agent": "Project Manager Agent",
            "sector_id": "all",
            "task_type": "rerun_paper_input_preflight",
            "reason": "",
            "required_before": "2026-10-08",
            "input_path": "config.json",
            "completion_check": "",
            "blocked_action_until_done": "clean_paper_signal_generation",
        },
    ]


def test_refresh_status_marks_future_tasks_not_due(tmp_path: Path) -> None:
    queue = _write_csv(tmp_path / "queue.csv", _queue_rows())
    preflight = {
        "strategy_id": "test_basket",
        "status": "pending_future_data_window",
        "target_rebalance_date": "2026-10-08",
        "prior_trading_date": "2026-10-07",
        "sector_checks": [{"sector_id": "bank", "target_panel_rows": 0}],
    }
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")

    result = check_basket_paper_refresh_status(
        queue_csv=queue,
        preflight_summary=preflight_path,
        as_of_date="2026-07-20",
        out_dir=tmp_path / "out",
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "waiting_for_future_refresh_window"
    assert summary["task_counts_by_status"]["not_due_yet"] == 1
    assert summary["task_counts_by_status"]["pending_refresh"] == 1


def test_refresh_status_ready_after_preflight_passes(tmp_path: Path) -> None:
    queue = _write_csv(tmp_path / "queue.csv", _queue_rows())
    preflight = {
        "strategy_id": "test_basket",
        "status": "ready_to_construct_clean_paper_signal",
        "target_rebalance_date": "2026-10-08",
        "prior_trading_date": "2026-10-07",
        "sector_checks": [{"sector_id": "bank", "target_panel_rows": 4, "target_rows_missing_required_fields": 0}],
    }
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")

    result = check_basket_paper_refresh_status(
        queue_csv=queue,
        preflight_summary=preflight_path,
        as_of_date="2026-10-08",
        out_dir=tmp_path / "out",
    )

    assert result.status == "ready_for_clean_paper_signal_gate"
    assert result.completed_count == 2
