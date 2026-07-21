from __future__ import annotations

import csv
import json
from pathlib import Path

import v5.low_priority_sector_initial_validation_runner as runner


def test_low_priority_sector_initial_validation_routes_research_signal(monkeypatch, tmp_path: Path) -> None:
    panel_dir = tmp_path / "panels" / "retail_commerce"
    panel_dir.mkdir(parents=True)
    panel = panel_dir / "panel.csv"
    fields = ["trade_date", "code", "future_return", "factor_visible_date", "operating_cash_flow_yield", "dividend_yield", "free_cash_flow_yield"]
    with panel.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for month in range(1, 13):
            for index in range(12):
                writer.writerow(
                    {
                        "trade_date": f"2025-{month:02d}-01",
                        "code": f"000{index:03d}.XSHG",
                        "future_return": "0.01",
                        "factor_visible_date": f"2025-{month:02d}-01",
                        "operating_cash_flow_yield": "0.1",
                        "dividend_yield": "0.02",
                        "free_cash_flow_yield": "0.03",
                    }
                )

    def fake_run_formal_validation(spec_path: Path, panel_csv: Path, out_dir: Path) -> Path:
        target = out_dir / "retail_commerce_ocf_dividend_fcf_initial_v5a11" / "formal_validation_report.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "baseline_tests": [
                {"case": "equal_weight_retail_commerce", "cum_return": 0.1},
                {"case": "high_ocf", "cum_return": 0.2},
                {"case": "high_dividend", "cum_return": 0.15},
                {"case": "high_fcf", "cum_return": 0.12},
                {"case": "ocf_dividend_fcf", "cum_return": 0.25},
            ],
            "rolling_validation": [{"cum_return": 0.01}, {"cum_return": 0.02}],
            "factor_ic_rankic": [],
        }
        target.with_name("formal_validation_summary.json").write_text(json.dumps(summary), encoding="utf-8")
        target.write_text("# report\n", encoding="utf-8")
        return target

    monkeypatch.setattr(runner, "run_formal_validation", fake_run_formal_validation)

    result = runner.run_low_priority_sector_initial_validation(tmp_path / "panels", tmp_path / "out", ["retail_commerce"])

    assert result.status == "initial_research_signal_found_not_engineering_handoff"
    assert "research_signal_candidate_needs_low_vol_state_gate" in result.result_csv.read_text(encoding="utf-8")
