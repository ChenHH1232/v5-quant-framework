from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

from v5.new_sleeve_observation_execution_runner import (
    DEFAULT_CANDIDATES,
    run_new_sleeve_observation_execution,
)


def test_new_sleeve_observation_execution_routes_all_candidates(tmp_path: Path) -> None:
    config = tmp_path / "v57f.json"
    config.write_text(
        json.dumps(
            {
                "project": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
                "sectors": [
                    {"sector_id": "bank"},
                    {"sector_id": "utilities_electricity"},
                    {"sector_id": "highway_infrastructure"},
                    {"sector_id": "port_rail_infrastructure"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    v57f_summary = tmp_path / "v57f_summary.json"
    _write_summary(v57f_summary, 0.8, 0.5, 0.3, 0.12, order_health=True)
    sleeve_registry = tmp_path / "sleeves.csv"
    _write_csv(
        sleeve_registry,
        ["sector_id", "panel_exists", "price_exists", "dividend_exists"],
        [
            ["gas_water_operators", "yes", "yes", "yes"],
            ["home_appliances", "yes", "yes", "yes"],
            ["oil_gas_pipeline_integrated", "yes", "yes", "yes"],
            ["food_beverage", "yes", "yes", "yes"],
            ["insurance", "yes", "yes", "no"],
            ["telecom_operators", "yes", "yes", "yes"],
            ["consumer_staples_cashflow", "no", "yes", "no"],
            ["coal", "no", "yes", "no"],
        ],
    )
    status_registry = tmp_path / "status.json"
    status_registry.write_text(
        json.dumps(
            {
                "strategies": [
                    {
                        "strategy_id": "gas_water",
                        "sector": "gas_water_operators",
                        "current_status": ["engineering_local_daily_simulation_passed", "rebalance_order_health_passed"],
                        "evidence_paths": ["panel_with_low_vol.csv", "external_state.csv"],
                    },
                    {
                        "strategy_id": "food",
                        "sector": "food_beverage",
                        "current_status": ["engineering_local_daily_simulation_needs_review"],
                        "evidence_paths": ["panel_with_low_vol.csv", "state_guard.csv"],
                    },
                    {
                        "strategy_id": "consumer",
                        "sector": "consumer_staples_cashflow",
                        "current_status": ["research_signal_only_not_engineering_handoff"],
                        "evidence_paths": ["consumer_subsector_validation_summary.json"],
                    },
                    {
                        "strategy_id": "coal",
                        "sector": "coal",
                        "current_status": ["strategy_candidate_failed"],
                        "blockers": ["inventory data gate failed"],
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temp_candidates = []
    for candidate in DEFAULT_CANDIDATES:
        local = tmp_path / candidate.sector_id / "summary.json"
        paper = tmp_path / candidate.sector_id / "paper.json" if candidate.sector_id in {"gas_water_operators", "home_appliances"} else None
        sidecar = tmp_path / candidate.sector_id / "sidecar.json" if candidate.sector_id in {"gas_water_operators", "telecom_operators"} else None
        if candidate.sector_id != "coal":
            _write_summary(local, 0.2, 0.1, 0.1, 0.1, order_health=candidate.sector_id != "food_beverage")
        else:
            _write_summary(local, 1.0, 0.8, 0.2, 0.3, order_health=False)
        if paper:
            paper.parent.mkdir(parents=True, exist_ok=True)
            paper.write_text(json.dumps({"status": "paper_tracking_ready"}), encoding="utf-8")
        if sidecar:
            _write_summary(sidecar, 0.7, 0.5, 0.2, 0.11, order_health=True)
        temp_candidates.append(replace(candidate, local_summary=local, paper_summary=paper, sidecar_summary=sidecar))

    result = run_new_sleeve_observation_execution(
        out_dir=tmp_path / "out",
        v57f_config=config,
        v57f_summary=v57f_summary,
        sleeve_registry=sleeve_registry,
        status_registry=status_registry,
        candidates=temp_candidates,
    )

    summary = json.loads(result.master_summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "all_candidates_routed_no_v57f_change"
    assert summary["freeze"]["freeze_status"] == "pass"
    assert result.packet_count == 8
    routes = list(csv.DictReader(result.route_table_csv.open("r", encoding="utf-8-sig")))
    assert {row["sector_id"] for row in routes} == {candidate.sector_id for candidate in DEFAULT_CANDIDATES}
    by_sector = {row["sector_id"]: row for row in routes}
    assert by_sector["gas_water_operators"]["route_status"] == "observation_paper_tracking"
    assert by_sector["food_beverage"]["route_status"] == "archived_not_current_mandate"
    assert by_sector["consumer_staples_cashflow"]["route_status"] == "research_data_gate_repair"
    assert by_sector["coal"]["route_status"] == "archived_not_current_mandate"
    assert all(row["blocked_action"] for row in routes)

    sidecars = list(csv.DictReader(result.sidecar_comparison_csv.open("r", encoding="utf-8-sig")))
    assert any(row["sidecar_status"] == "completed_not_core_promotion" for row in sidecars)
    queue = list(csv.DictReader(result.next_agent_queue_csv.open("r", encoding="utf-8-sig")))
    assert len(queue) == 1
    assert "do_not_modify_V57f" in queue[0]["blocked_actions"]


def _write_summary(path: Path, strategy_return: float, benchmark_return: float, excess: float, drawdown: float, *, order_health: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metrics": {
            "strategy_return": strategy_return,
            "benchmark_return": benchmark_return,
            "excess_return": excess,
            "max_drawdown": drawdown,
            "sharpe": 0.5,
            "information_ratio": 0.2,
            "strategy_volatility": 0.15,
        },
        "trade_count": 10,
        "dividend_count": 3,
    }
    if order_health:
        payload["rebalance_order_health"] = {"needs_review": False}
    else:
        payload["rebalance_order_health"] = {"needs_review": True}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)
