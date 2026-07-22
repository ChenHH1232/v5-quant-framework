from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.enhanced_etf_production_line_runner import build_enhanced_etf_production_line


def test_build_enhanced_etf_production_line_routes_sleeves(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    price = tmp_path / "price.csv"
    dividend = tmp_path / "dividend.csv"
    for path in [panel, price, dividend]:
        path.write_text("code,trade_date\n", encoding="utf-8")

    master = tmp_path / "master.csv"
    with master.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sector_id",
                "display_name",
                "pm_bucket",
                "basket_eligibility",
                "prevalidation_decision",
                "next_agent",
                "allowed_next_action",
                "blocked_action",
                "primary_theory",
                "primary_factor_priority",
                "data_gate",
                "external_state_burden",
                "sample_size_risk",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "sector_id": "bank",
                "display_name": "Bank",
                "pm_bucket": "core_or_observation_refresh_no_tuning",
                "basket_eligibility": "eligible_or_existing_sleeve_refresh_only",
                "next_agent": "Engineering Agent",
                "allowed_next_action": "refresh",
                "blocked_action": "do not tune",
                "data_gate": "passed",
                "external_state_burden": "medium",
                "sample_size_risk": "medium",
            }
        )
        writer.writerow(
            {
                "sector_id": "gas_water_operators",
                "display_name": "Gas / Water",
                "pm_bucket": "core_or_observation_refresh_no_tuning",
                "basket_eligibility": "eligible_or_existing_sleeve_refresh_only",
                "next_agent": "Engineering Agent",
                "allowed_next_action": "refresh",
                "blocked_action": "do not tune",
                "data_gate": "needs_manual_research",
                "external_state_burden": "medium",
                "sample_size_risk": "medium",
            }
        )
        writer.writerow(
            {
                "sector_id": "coal",
                "display_name": "Coal",
                "pm_bucket": "archived_or_rejected",
                "basket_eligibility": "not_eligible",
                "next_agent": "Project Manager Agent",
                "allowed_next_action": "archive",
                "blocked_action": "do not model",
                "data_gate": "blocked",
                "external_state_burden": "high",
                "sample_size_risk": "medium",
            }
        )

    config = tmp_path / "basket.json"
    project = "basket_test"
    config.write_text(
        json.dumps(
            {
                "project": project,
                "sectors": [
                    {
                        "sector_id": "bank",
                        "role": "core",
                        "panel_csv": str(panel),
                        "price_csv": str(price),
                        "dividend_csv": str(dividend),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({"strategies": [{"strategy_id": project, "current_status": ["formal_etf_candidate"]}]}),
        encoding="utf-8",
    )

    result = build_enhanced_etf_production_line(
        master_table=master,
        basket_config=config,
        status_registry=registry,
        out_dir=tmp_path / "out",
        next_clean_rebalance_date="2026-10-08",
    )

    assert result.active_sleeve_count == 1
    assert result.sleeve_registry_csv.exists()
    assert result.summary_json.exists()
    rows = list(csv.DictReader(result.sleeve_registry_csv.open("r", encoding="utf-8")))
    lanes = {row["sector_id"]: row["production_lane"] for row in rows}
    assert lanes["bank"] == "core_frozen_refresh"
    assert lanes["gas_water_operators"] == "observation_refresh_only"
    assert lanes["coal"] == "archived_or_rejected"
    report = result.report_path.read_text(encoding="utf-8")
    assert "V5 Enhanced ETF Production Line" in report
    assert "Historical performance alone" in report

