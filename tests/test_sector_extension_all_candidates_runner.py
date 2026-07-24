from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.sector_extension_all_candidates_runner import summarize_sector_extension_all_candidates


def test_summarize_sector_extension_all_candidates_classifies_every_candidate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    promotion_queue = tmp_path / "queue.csv"
    _write_csv(
        promotion_queue,
        ["rank", "sector_id", "display_name"],
        [
            ["1", "gas_water_operators", "Gas / Water"],
            ["2", "home_appliances", "Home"],
            ["3", "oil_gas_pipeline_integrated", "Oil"],
            ["4", "food_beverage", "Food"],
            ["5", "telecom_operators", "Telecom"],
            ["6", "insurance", "Insurance"],
            ["7", "consumer_staples_cashflow", "Consumer"],
        ],
    )
    _json("paper_trading_signals/gas_water_v59b_promotion_queue/gas_water_v57b_text_debt_state_guard_v59b/gas_water_paper_tracking_summary.json", {"status": "paper_tracking_ready_waiting_for_future_window"})
    _json("local_daily_backtests_v59b_gas_water_state_guard_repaired_2021_07/gas_water_v57b_text_debt_state_guard_v59b/summary.json", {"status": "engineering_local_daily_simulation_passed"})
    _json("paper_trading_signals/home_appliances_v5a5e_promotion_queue/home_appliances_ocf_quality_v5a5c/home_appliances_paper_tracking_summary.json", {"status": "paper_tracking_ready_waiting_for_future_window"})
    _json("local_daily_backtests_home_appliances_v5a5e/home_appliances_ocf_quality_v5a5c/summary.json", {"status": "engineering_local_daily_simulation_passed"})
    _json("telecom_engineering_execution_v5/current/telecom_engineering_execution_summary.json", {"status": "paper_tracking_ready_waiting_for_future_window"})
    _json("telecom_engineering_readiness_v5/current/telecom_engineering_readiness_summary.json", {"status": "engineering_observation_sleeve_ready"})
    _json("food_beverage_engineering_reviews_v5/current/food_beverage_engineering_review_summary.json", {"next_gate": "pm_review_tradability"})
    _json("local_daily_backtests_food_beverage_v5a9/food_beverage_packaged_food_ocf_quality_v5a9a/summary.json", {"status": "engineering_local_daily_simulation_needs_review"})
    _json("数据库/processed/oil_gas_source_gate_v58e/oil_gas_source_gate_summary.json", {"promotion_ready": False})
    _json("local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/summary.json", {"status": "engineering_smoke_test_completed_not_platform_replication"})
    _json("insurance_ev_nbv_panel_v53g_2020_2025/insurance_pev_value_v53g/ev_nbv_panel_summary.json", {"status": "ready"})
    _json("validation_formal_v5a6_consumer_subsector/consumer_staples_cashflow/consumer_subsector_validation_summary.json", {"status": "subsector_research_signal_found_not_engineering_handoff"})
    _json("数据库/processed/consumer_working_capital_state_v5a6/consumer_staples_cashflow/working_capital_state_summary.json", {"status": "working_capital_state_enriched_needs_validation"})

    result = summarize_sector_extension_all_candidates(promotion_queue=promotion_queue, out_dir=tmp_path / "out")

    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["candidate_count"] == 7
    assert summary["core_promotion_allowed_count"] == 0
    rows = list(csv.DictReader(result.status_matrix_csv.open("r", encoding="utf-8-sig")))
    assert {row["sector_id"] for row in rows} == {
        "gas_water_operators",
        "home_appliances",
        "oil_gas_pipeline_integrated",
        "food_beverage",
        "telecom_operators",
        "insurance",
        "consumer_staples_cashflow",
    }
    by_sector = {row["sector_id"]: row for row in rows}
    assert by_sector["gas_water_operators"]["paper_tracking_status"] == "ready_waiting_future_window"
    assert by_sector["food_beverage"]["engineering_test_status"] == "needs_review"
    assert by_sector["consumer_staples_cashflow"]["furthest_stage_reached"] == "working_capital_state_plus_subsector_validation"
    queue = list(csv.DictReader(result.next_agent_queue_csv.open("r", encoding="utf-8-sig")))
    assert queue[0]["sector_id"] == "oil_gas_pipeline_integrated"
    report = result.report_md.read_text(encoding="utf-8")
    assert "Candidate Status Matrix" in report


def _write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)


def _json(path: str, payload: dict[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")
