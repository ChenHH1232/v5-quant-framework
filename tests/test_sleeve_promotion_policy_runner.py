from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.sleeve_promotion_policy_runner import run_sleeve_promotion_policy_audit


def test_sleeve_promotion_policy_blocks_return_only_promotion(tmp_path: Path) -> None:
    observation = tmp_path / "observation.csv"
    _write_csv(
        observation,
        [
            "sector_id",
            "strategy_id",
            "observation_class",
            "latest_stage",
            "strategy_return",
            "max_drawdown",
            "information_ratio",
            "order_health_status",
            "paper_tracking_status",
            "allowed_next_action",
            "blocked_action",
            "next_gate",
        ],
        [
            [
                "gas_water_operators",
                "gas",
                "observation_basket",
                "engineering_local_refresh_passed",
                "1.20",
                "0.10",
                "0.20",
                "passed",
                "paper_artifact_exists",
                "observe",
                "do_not_modify_V57f",
                "wait",
            ],
            [
                "food_beverage",
                "food",
                "engineering_review_or_research_repair",
                "engineering_local_refresh_passed",
                "0.50",
                "0.09",
                "0.50",
                "needs_review",
                "missing",
                "repair",
                "do_not_ignore_order_health",
                "repair",
            ],
        ],
    )
    core = tmp_path / "core.csv"
    _write_csv(
        core,
        ["row_type", "strategy_id", "strategy_return", "max_drawdown", "information_ratio"],
        [["mainline_basket", "v57f", "0.80", "0.12", "0.44"]],
    )

    result = run_sleeve_promotion_policy_audit(
        observation_registry=observation,
        core_dashboard=core,
        out_dir=tmp_path / "out",
    )

    summary = json.loads(result.audit_summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "promotion_policy_audit_completed_no_core_promotions"
    rows = list(csv.DictReader(result.audit_csv.open("r", encoding="utf-8-sig")))
    by_sector = {row["sector_id"]: row for row in rows}
    assert by_sector["gas_water_operators"]["promotion_decision"] == "remain_observation_needs_forward_or_sidecar_evidence"
    assert by_sector["gas_water_operators"]["can_promote_to_core_candidate"] == "no"
    assert "P6_information_ratio_below_threshold" in by_sector["gas_water_operators"]["failed_rules"]
    assert by_sector["food_beverage"]["promotion_decision"] == "engineering_repair_required"
    queue = list(csv.DictReader(result.next_agent_queue_csv.open("r", encoding="utf-8-sig")))
    assert queue[0]["blocked_actions"] == "do_not_modify_V57f;do_not_tune;do_not_promote_by_return"
    policy = result.policy_md.read_text(encoding="utf-8")
    assert "Historical return alone" in policy


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)
