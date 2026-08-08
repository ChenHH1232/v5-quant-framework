from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.v5b_forward_paper_handoff_runner import build_v5b_forward_paper_handoff


def test_v5b_forward_paper_handoff_writes_scope_and_priority_files(tmp_path: Path) -> None:
    paths = _make_inputs(tmp_path)

    result = build_v5b_forward_paper_handoff(**paths, out_dir=tmp_path / "out")

    assert result.status == "v5_frozen_handoff_v5b_forward_paper_scope_ready"
    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["v5_final_state"]["scope_end_date"] == "2026-05-31"
    assert summary["v57f"]["not_status"] == ["accepted_strategy", "live_trading_approved", "platform_replication_passed"]
    assert summary["highest_value_next_action"].startswith("JoinQuant platform attribution")
    assert result.agent_execution_rules_md.exists()

    priority = list(csv.DictReader(result.candidate_priority_queue_csv.open("r", encoding="utf-8-sig")))
    assert priority[0]["sector_id"] == "gas_water_operators"
    assert priority[0]["can_join_v57f_core"] == "no"
    assert priority[-1]["sector_id"] == "coal"

    blocked = result.blocked_actions_csv.read_text(encoding="utf-8-sig")
    assert "Modify core sleeves" in blocked
    assert "Continue minute-level timing optimization" in blocked

    external = list(csv.DictReader(result.required_external_inputs_csv.open("r", encoding="utf-8-sig")))
    assert {row["input_name"] for row in external} >= {"Daily return export", "Transaction export", "Position export", "Log export"}

    report = result.report_md.read_text(encoding="utf-8")
    assert "V57f remains the frozen formal ETF candidate" in report
    assert "V5b Candidate Priority Queue" in report


def _make_inputs(tmp_path: Path) -> dict[str, Path]:
    status_registry = _json(tmp_path / "status.json", {"strategies": [{"strategy_id": "v57f"}]})
    v5_scope_summary = _json(
        tmp_path / "scope.json",
        {
            "status": "v5_scope_closed_local_engineering_to_2026_05_31",
            "scope_end_date": "2026-05-31",
            "scope_rule": "V5 local engineering and JoinQuant-aligned backtest evidence ends at 2026-05-31. Future/paper signals are outside V5 scope.",
            "outputs": {"final_status_csv": "final.csv"},
        },
    )
    v5_final_status = _csv(
        tmp_path / "final.csv",
        ["candidate_id", "v5_final_status", "evidence_primary"],
        [["gas_water_operators", "engineering_passed_observation_parked_v5_scope_closed", "gas.json"]],
    )
    v5_scope_queue = _csv(tmp_path / "scope_queue.csv", ["queue_rank"], [["1"]])
    governance_summary = _json(tmp_path / "gov.json", {"paper_runner_note": "Future paper belongs elsewhere."})
    governance_report = tmp_path / "gov.md"
    governance_report.write_text("# Governance\n", encoding="utf-8")
    production_summary = _json(
        tmp_path / "prod.json",
        {
            "strategy_id": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
            "active_sleeves": ["bank", "utilities_electricity", "highway_infrastructure", "port_rail_infrastructure"],
            "evidence": {
                "daily_summary": {
                    "metrics": {"strategy_return": 0.8, "max_drawdown": 0.12, "information_ratio": 0.44},
                    "rebalance_order_health": {"needs_review": False},
                }
            },
        },
    )
    promotion_summary = _json(tmp_path / "promo.json", {"candidate_count": 7})
    promotion_queue = _csv(
        tmp_path / "promo.csv",
        ["sector_id", "pm_note"],
        [["gas_water_operators", "rank 1"], ["coal", "archived"]],
    )
    all_candidates_summary = _json(tmp_path / "all.json", {"candidate_count": 7})
    all_candidates_status = _csv(
        tmp_path / "all.csv",
        ["sector_id", "primary_evidence"],
        [["gas_water_operators", "gas.json"], ["home_appliances", "home.json"]],
    )
    execution_robustness = _json(
        tmp_path / "robust.json",
        {
            "status": "execution_robustness_completed_not_tuning",
            "decision": "execution_timing_not_fragile_no_strategy_change",
            "variant_count": 8,
            "stable_positive_excess_variant_count": 8,
        },
    )
    return {
        "status_registry": status_registry,
        "v5_scope_summary": v5_scope_summary,
        "v5_final_status": v5_final_status,
        "v5_scope_queue": v5_scope_queue,
        "governance_summary": governance_summary,
        "governance_report": governance_report,
        "production_summary": production_summary,
        "promotion_summary": promotion_summary,
        "promotion_queue": promotion_queue,
        "all_candidates_summary": all_candidates_summary,
        "all_candidates_status": all_candidates_status,
        "execution_robustness": execution_robustness,
    }


def _json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _csv(path: Path, fields: list[str], rows: list[list[str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)
    return path
