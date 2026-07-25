from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.v5_scope_closeout_runner import build_v5_scope_closeout_packet


def test_v5_scope_closeout_removes_future_signal_from_v5_and_adjudicates_food(tmp_path: Path) -> None:
    candidates = tmp_path / "all_candidates.csv"
    _write_csv(
        candidates,
        [
            "sector_id",
            "engineering_test_status",
            "primary_evidence",
            "secondary_evidence",
        ],
        [
            ["gas_water_operators", "passed", "gas.json", "gas_local.json"],
            ["food_beverage", "needs_review", "food_review.json", "food_local.json"],
        ],
    )
    v57f_summary = tmp_path / "v57f.json"
    _json(
        v57f_summary,
        {
            "strategy_id": "v57f",
            "window": {"end_date": "2026-05-31"},
            "metrics": {"strategy_return": 0.8, "max_drawdown": 0.12},
        },
    )
    food_review = tmp_path / "food_review.json"
    _json(
        food_review,
        {
            "local_metrics": {"strategy_return": 0.115, "max_drawdown": 0.431},
            "order_health": {"partial_skipped_order_count": 3, "high_cash_rebalance_dates": ["2024-10-08"]},
            "startup_gap": {"status": "research_pit_window_gap", "first_signal_date": "2022-01-04", "has_startup_gap": "true"},
            "dividend_gap": {"status": "passed"},
        },
    )

    result = build_v5_scope_closeout_packet(
        all_candidates_csv=candidates,
        v57f_summary=v57f_summary,
        food_review_json=food_review,
        out_dir=tmp_path / "out",
    )

    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["scope_end_date"] == "2026-05-31"
    assert "outside V5 scope" in summary["scope_rule"]
    assert summary["core_promotion_allowed_count"] == 0

    rows = list(csv.DictReader(result.final_status_csv.open("r", encoding="utf-8-sig")))
    by_id = {row["candidate_id"]: row for row in rows}
    assert by_id["gas_water_operators"]["v5_scope_future_signal_policy"] == "outside_v5_scope"
    assert by_id["food_beverage"]["v5_final_status"] == "observation_candidate_closed_failed_pm_tradability_review"
    assert by_id["food_beverage"]["food_beverage_pm_decision"] == "archive_in_v5_do_not_promote_to_observation_or_engineering_next_layer"

    food = json.loads(result.food_decision_json.read_text(encoding="utf-8"))
    assert food["status"] == "closed_failed_v5_observation_candidate"
    report = result.report_md.read_text(encoding="utf-8")
    assert "V5 no longer waits for or generates a 2026-10 signal" in report


def _write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)


def _json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
