from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.food_beverage_research_repair_runner import run_food_beverage_research_repair


def test_food_beverage_research_repair_can_open_engineering_gate_when_evidence_is_wide_and_stable(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    _write_panel(panel, codes_per_subindustry=12, weak_year=False)

    result = run_food_beverage_research_repair(panel, tmp_path / "out", tmp_path / "packets")

    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "food_beverage_engineering_handoff_ready"
    rows = list(csv.DictReader(result.result_csv.open("r", encoding="utf-8")))
    assert any(row["pm_gate"] == "engineering_handoff_candidate" for row in rows)


def test_food_beverage_research_repair_blocks_small_specialist_sample(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    _write_panel(panel, codes_per_subindustry=4, weak_year=False)

    result = run_food_beverage_research_repair(panel, tmp_path / "out", tmp_path / "packets")

    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "food_beverage_research_repair_completed_not_engineering_handoff"
    rows = list(csv.DictReader(result.result_csv.open("r", encoding="utf-8")))
    assert all(row["pm_gate"] == "research_repair_blocked" for row in rows)
    assert any("Sample width" in row["blocker"] or "Selection count" in row["blocker"] for row in rows)


def _write_panel(path: Path, *, codes_per_subindustry: int, weak_year: bool) -> None:
    headers = [
        "trade_date",
        "code",
        "sub_industry",
        "future_return",
        "operating_cash_flow_yield",
        "operating_cash_flow_to_net_profit",
        "factor_visible_date",
        "low_price_to_book",
        "high_inventory_pressure_flag",
        "high_receivables_pressure_flag",
        "high_working_capital_pressure_flag",
    ]
    dates = [f"{year}-{quarter}" for year in range(2021, 2027) for quarter in ("01-04", "04-01", "07-01", "10-08")]
    dates = dates[:20]
    rows = []
    for date_index, trade_date in enumerate(dates):
        year = trade_date[:4]
        for sub in ("sw_condiments", "sw_snack_food"):
            for code_index in range(codes_per_subindustry):
                code_num = (1 if sub == "sw_condiments" else 100) + code_index
                strength = code_index + 1
                if weak_year and year == "2025":
                    future_return = -0.02 * strength
                else:
                    future_return = 0.005 * strength
                rows.append(
                    {
                        "trade_date": trade_date,
                        "code": f"{code_num:06d}.XSHE",
                        "sub_industry": sub,
                        "future_return": str(future_return),
                        "operating_cash_flow_yield": str(0.01 * strength),
                        "operating_cash_flow_to_net_profit": str(1.0 + strength),
                        "factor_visible_date": trade_date,
                        "low_price_to_book": str(2.0 - 0.01 * strength),
                        "high_inventory_pressure_flag": "false",
                        "high_receivables_pressure_flag": "false",
                        "high_working_capital_pressure_flag": "false",
                    }
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
