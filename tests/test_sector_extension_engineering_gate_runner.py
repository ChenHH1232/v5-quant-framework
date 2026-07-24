from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.sector_extension_engineering_gate_runner import run_sector_extension_engineering_gate


def test_sector_extension_engineering_gate_passes_rank1_gas_water(tmp_path: Path) -> None:
    promotion_queue = tmp_path / "sleeve_promotion_queue.csv"
    _write_csv(
        promotion_queue,
        ["rank", "sector_id", "promotion_score", "recommended_next_owner", "pm_gate"],
        [
            ["1", "gas_water_operators", "89.0", "Engineering Agent", "paper_tracking_only_no_core_inclusion"],
            ["2", "home_appliances", "60.0", "Engineering Agent", "paper_tracking_only_no_core_inclusion"],
        ],
    )
    selected_queue = tmp_path / "selected_candidate_agent_queue.csv"
    _write_csv(
        selected_queue,
        ["queue_rank", "sector_id", "owner", "task"],
        [["1", "gas_water_operators", "Engineering Agent", "Run local daily only"]],
    )
    local_daily = tmp_path / "local_daily" / "gas_water"
    local_daily.mkdir(parents=True)
    (local_daily / "summary.json").write_text(
        json.dumps(
            {
                "strategy_id": "gas_water_v57b_text_debt_state_guard_v59b",
                "status": "engineering_local_daily_simulation_passed_ready_for_platform_preparation",
                "window": {"start_date": "2021-05-01", "end_date": "2026-05-31"},
                "signal_count": 20,
                "daily_count": 1228,
                "trade_count": 40,
                "dividend_count": 12,
                "rebalance_order_health": {
                    "needs_review": False,
                    "unexpected_rebalance_issue_count": 0,
                    "leading_no_order_no_position_count": 0,
                    "missing_daily_rebalance_count": 0,
                },
                "metrics": {"strategy_return": 0.76, "max_drawdown": 0.24, "information_ratio": 0.36},
            }
        ),
        encoding="utf-8",
    )
    for filename in ["trades.csv", "holdings.csv", "dividends.csv", "rebalance_order_health.csv"]:
        _write_csv(local_daily / filename, ["date"], [["2026-05-31"]])

    result = run_sector_extension_engineering_gate(
        promotion_queue=promotion_queue,
        selected_queue=selected_queue,
        gas_water_local_daily=local_daily,
        out_dir=tmp_path / "out",
    )

    assert result.status == "engineering_test_passed"
    assert result.selected_sector_id == "gas_water_operators"
    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["pm_rules"][0].startswith("Do not modify frozen V57f")
    checks = list(csv.DictReader(result.engineering_checks_csv.open("r", encoding="utf-8-sig")))
    assert {row["status"] for row in checks} == {"passed"}
    queue = list(csv.DictReader(result.next_agent_queue_csv.open("r", encoding="utf-8-sig")))
    assert queue[0]["gate"] == "observation_wait_no_core_inclusion"
    report = result.report_md.read_text(encoding="utf-8")
    assert "Detailed Flow Table" in report
    assert "This gate does not promote the sleeve into V57f" in report


def _write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)
