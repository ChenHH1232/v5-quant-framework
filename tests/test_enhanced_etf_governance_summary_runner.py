from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.enhanced_etf_governance_summary_runner import (
    ObservationSpec,
    build_enhanced_etf_governance_summary,
)


def test_enhanced_etf_governance_summary_separates_core_and_observation(tmp_path: Path, monkeypatch) -> None:
    status_registry = tmp_path / "status.json"
    _write_json(
        status_registry,
        {
            "strategies": [
                {
                    "strategy_id": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
                    "current_status": ["formal_etf_candidate", "waiting_for_future_refresh_window"],
                    "not_status": ["accepted_strategy"],
                    "next_gate": "external_wait",
                },
                {
                    "strategy_id": "obs_strategy",
                    "current_status": ["engineering_local_refresh_passed", "paper_tracking_preparation_ready"],
                    "next_gate": "wait",
                },
            ]
        },
    )
    production = tmp_path / "production.json"
    _write_json(
        production,
        {
            "registry_next_gate": "external_wait",
            "evidence": {
                "daily_summary": {
                    "path": "daily.json",
                    "metrics": {"strategy_return": 0.8, "max_drawdown": 0.1, "information_ratio": 0.4},
                    "rebalance_order_health": {"needs_review": False},
                }
            },
        },
    )
    sleeve_registry = tmp_path / "sleeves.csv"
    _write_csv(
        sleeve_registry,
        ["sector_id", "is_active_v57f_sleeve", "basket_role"],
        [["bank", "yes", "financial_core"], ["gas_water_operators", "no", ""]],
    )
    obs_summary = tmp_path / "obs_summary.json"
    _write_json(
        obs_summary,
        {
            "metrics": {"strategy_return": 0.2, "max_drawdown": 0.05, "information_ratio": 0.3},
            "rebalance_order_health": {"needs_review": False},
        },
    )
    obs_paper = tmp_path / "obs_paper.json"
    _write_json(obs_paper, {"status": "paper_tracking_ready"})
    monkeypatch.setattr(
        "v5.enhanced_etf_governance_summary_runner.OBSERVATION_SPECS",
        [
            ObservationSpec(
                "gas_water_operators",
                "obs_strategy",
                "Observation",
                "observation_basket",
                obs_summary,
                obs_paper,
                "paper tracking only",
                "do_not_modify_V57f",
                "wait",
            )
        ],
    )

    result = build_enhanced_etf_governance_summary(
        status_registry=status_registry,
        production_summary=production,
        sleeve_registry=sleeve_registry,
        out_dir=tmp_path / "out",
    )

    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert payload["status"] == "v57f_core_and_observation_governance_completed"
    assert payload["paper_runner_scope"] == "excluded_from_this_run"
    core_rows = list(csv.DictReader(result.core_dashboard_csv.open("r", encoding="utf-8-sig")))
    assert {row["row_type"] for row in core_rows} == {"mainline_basket", "core_sleeve"}
    assert all(row["can_change_v57f"] == "no" for row in core_rows)
    observation_rows = list(csv.DictReader(result.observation_registry_csv.open("r", encoding="utf-8-sig")))
    assert observation_rows[0]["can_join_v57f_core"] == "no"
    assert observation_rows[0]["paper_tracking_status"] == "paper_artifact_exists"
    queue_rows = list(csv.DictReader(result.next_agent_queue_csv.open("r", encoding="utf-8-sig")))
    assert "do_not_start_paper_runner_here" in queue_rows[0]["blocked_actions"]
    report = result.report_md.read_text(encoding="utf-8")
    assert "V57f remains the frozen mainline" in report


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)
