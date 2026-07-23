from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

from v5.enhanced_etf_comparison_runner import DEFAULT_ITEMS, build_v57f_comparison_packet


def test_v57f_comparison_packet_hardens_labels_and_gates(tmp_path: Path) -> None:
    summaries = {
        "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f": _summary(
            "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
            0.814,
            0.51,
            0.117,
            order_health={"needs_review": False, "first_executed_order_date": "2021-10-08"},
        ),
        "home_appliances_ocf_quality_v5a5c": _summary("home_appliances_ocf_quality_v5a5c", 1.06, -0.03, 0.30),
        "oil_gas_state_conditioned_ocf_v58g": _summary("oil_gas_state_conditioned_ocf_v58g", 0.99, 0.86, 0.22),
        "food_beverage_packaged_food_ocf_quality_v5a9a": _summary(
            "food_beverage_packaged_food_ocf_quality_v5a9a",
            0.046,
            -0.03,
            0.45,
            order_health={"needs_review": True},
        ),
        "coal_cashflow_cycle_value_v52b_capex_policy": _summary(
            "coal_cashflow_cycle_value_v52b_capex_policy",
            1.33,
            0.95,
            0.28,
        ),
    }
    temp_items = []
    for item in DEFAULT_ITEMS:
        if item.strategy_id in summaries:
            path = tmp_path / item.strategy_id / "summary.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(summaries[item.strategy_id], ensure_ascii=False), encoding="utf-8")
            temp_items.append(replace(item, summary_path=path))

    production_summary = tmp_path / "production_line_summary.json"
    production_summary.write_text(
        json.dumps(
            {
                "status": "engineering_local_refresh_ready_not_platform_replication",
                "next_clean_rebalance_date": "2026-10-08",
                "evidence": {
                    "pm_gate_summary": {"status": "formal_candidate_paper_tracking_started_needs_review"},
                    "dashboard_summary": {"status": "needs_pm_review"},
                    "action_route_summary": {"status": "no_action_until_external_event"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = build_v57f_comparison_packet(
        out_dir=tmp_path / "out",
        production_summary_path=production_summary,
        items=temp_items,
    )

    assert result.row_count == len(temp_items)
    rows = list(csv.DictReader(result.all_csv.open("r", encoding="utf-8")))
    assert rows
    assert all(row["label_en"] for row in rows)
    assert all(row["label_zh"] for row in rows)
    assert "??" not in result.all_csv.read_text(encoding="utf-8")
    assert "\ufffd" not in result.all_csv.read_text(encoding="utf-8")
    assert "??" not in result.report_path.read_text(encoding="utf-8")
    assert all(row["order_health_status"] in {"pass", "needs_review", "unknown", "not_applicable"} for row in rows)
    assert all(row["order_health_status"] for row in rows)

    by_sector = {row["sector_id"]: row for row in rows}
    assert by_sector["enhanced_etf_basket"]["is_directly_comparable_to_v57f"] == "yes"
    assert "2026-10-08" in by_sector["enhanced_etf_basket"]["allowed_next_action"]
    for sector in ["home_appliances", "oil_gas_pipeline_integrated", "food_beverage", "coal"]:
        assert by_sector[sector]["eligible_for_core"] == "no"
        assert by_sector[sector]["can_promote_to_v57f"] == "no"
        assert by_sector[sector]["is_directly_comparable_to_v57f"] == "no"
    assert by_sector["food_beverage"]["order_health_status"] == "needs_review"
    assert by_sector["coal"]["order_health_status"] == "unknown"

    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "comparison_packet_hardened_not_strategy_acceptance"
    assert "platform_replication_passed" in summary["not_status"]
    assert summary["next_gate"] == "wait_until_2026_10_08_or_joinquant_exports_for_daily_attribution"


def test_default_comparison_labels_are_stable() -> None:
    for item in DEFAULT_ITEMS:
        assert item.label_en
        assert item.label_zh
        assert "??" not in item.label_en
        assert "??" not in item.label_zh
        assert "\ufffd" not in item.label_en
        assert "\ufffd" not in item.label_zh
        if item.strategy_id != "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f":
            assert item.is_directly_comparable_to_v57f == "no"
    blocked = {item.sector_id: item for item in DEFAULT_ITEMS}
    for sector in ["coal", "home_appliances", "oil_gas_pipeline_integrated", "food_beverage"]:
        assert blocked[sector].eligible_for_core == "no"
        assert blocked[sector].can_promote_to_v57f == "no"


def _summary(
    strategy_id: str,
    strategy_return: float,
    benchmark_return: float,
    max_drawdown: float,
    *,
    order_health: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "strategy_id": strategy_id,
        "window": {"start_date": "2021-05-01", "end_date": "2026-05-31"},
        "daily_count": 1228,
        "metrics": {
            "strategy_return": strategy_return,
            "annualized_return": 0.1,
            "benchmark_return": benchmark_return,
            "excess_return": strategy_return - benchmark_return,
            "max_drawdown": max_drawdown,
            "sharpe": 0.5,
            "information_ratio": 0.2,
            "strategy_volatility": 0.16,
            "benchmark_volatility": 0.18,
        },
    }
    if order_health is not None:
        payload["rebalance_order_health"] = order_health
    return payload
