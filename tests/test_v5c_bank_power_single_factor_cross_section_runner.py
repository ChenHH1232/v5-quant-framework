from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_bank_power_single_factor_cross_section_runner import (
    _diagnostic_status,
    _period_stock_return,
    run,
)
from v5.v5f_structural_rough_screen_runner import PRICE_DIR, REPAIRED_RUN


class V5cBankPowerSingleFactorCrossSectionRunnerTest(unittest.TestCase):
    def test_period_stock_return_uses_rebalance_window_only(self) -> None:
        dates = ["2025-04-30", "2025-05-01", "2025-07-01"]
        ret_map = {
            ("2025-04-30", "600000.XSHG"): 0.10,
            ("2025-05-01", "600000.XSHG"): -0.05,
            ("2025-07-01", "600000.XSHG"): 0.50,
        }
        value = _period_stock_return("600000.XSHG", "2025-04-30", "2025-07-01", dates, ret_map)
        self.assertAlmostEqual(value or 0.0, 0.045)

    def test_diagnostic_status_identifies_positive_direction(self) -> None:
        import pandas as pd

        self.assertEqual(_diagnostic_status(pd.Series([0.01, 0.02, -0.01, 0.03, 0.01])), "positive_directional_diagnostic")

    def test_runner_outputs_single_factor_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fixture(root)
            summary_path = run(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_single_factor_cross_section_test")
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])

            out = root / "v5c_bank_power_single_factor_cross_section_test" / "current"
            schema = _read_csv(out / "v5c_bank_power_single_factor_schema.csv")
            self.assertIn("bank_nim", {row["factor_id"] for row in schema})

            governance = _read_csv(out / "v5c_bank_power_single_factor_governance_audit.csv")
            preserved = next(row for row in governance if row["audit_id"] == "sleeve_weight_preserved")
            self.assertEqual(preserved["status"], "pass")


def _write_fixture(root: Path) -> None:
    pit = root / "v5c_bank_power_financial_report_pit_panel" / "current"
    pit.mkdir(parents=True)
    _write_csv(
        pit / "v5c_bank_power_rebalance_pit_field_panel.csv",
        [
            _pit("2025-04-30", "600000.XSHG", "bank", 0.25, net_interest_margin_pct=2.1, deposit_cost_pct=1.8),
            _pit("2025-04-30", "600001.XSHG", "bank", 0.25, net_interest_margin_pct=1.4, deposit_cost_pct=2.4),
            _pit("2025-04-30", "600011.XSHG", "utilities_electricity", 0.25, tariff_yuan_per_kwh=0.42, utilization_hours=4200),
            _pit("2025-04-30", "600012.XSHG", "utilities_electricity", 0.25, tariff_yuan_per_kwh=0.32, utilization_hours=3000),
        ],
    )

    price_dir = root / PRICE_DIR
    price_dir.mkdir(parents=True)
    price_rows = []
    returns = {"600000.XSHG": 0.10, "600001.XSHG": 0.00, "600011.XSHG": 0.08, "600012.XSHG": 0.00}
    for code, ret in returns.items():
        price_rows.append({"date": "2025-04-30", "code": code, "close": 10.0})
        price_rows.append({"date": "2025-05-01", "code": code, "close": 10.0 * (1 + ret)})
    _write_csv(price_dir / "fixture_prices.csv", price_rows)

    run_dir = root / REPAIRED_RUN
    run_dir.mkdir(parents=True)
    signals = [
        _signal("2025-04-30", "600000.XSHG", "bank", 0.25),
        _signal("2025-04-30", "600001.XSHG", "bank", 0.25),
        _signal("2025-04-30", "600011.XSHG", "utilities_electricity", 0.25),
        _signal("2025-04-30", "600012.XSHG", "utilities_electricity", 0.25),
    ]
    _write_csv(run_dir / "rebalance_signals.csv", signals)
    _write_csv(
        run_dir / "daily_returns.csv",
        [
            {"trade_date": "2025-04-30", "strategy_return": 0.0, "strategy_nav": 1.0},
            {"trade_date": "2025-05-01", "strategy_return": 0.0, "strategy_nav": 1.0},
        ],
    )

    rough = root / "v5f_structural_rough_screen" / "current"
    rough.mkdir(parents=True)
    primary = [
        {
            "version_id": "internal_subsleeve_mom12_70_30",
            "family": "fixture",
            "rebalance_date": row["trade_date"],
            "code": row["code"],
            "sleeve": row["sector_id"],
            "base_target_weight": row["target_weight"],
            "target_weight": row["target_weight"],
            "weight_delta": 0.0,
            "bucket": "fixture",
            "sleeve_weight_preserved": True,
            "new_stock_selected": False,
            "accepted": False,
        }
        for row in signals
    ]
    _write_csv(rough / "v5f_structural_rough_screen_weights.csv", primary)


def _pit(date: str, code: str, sleeve: str, weight: float, **values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "trade_date": date,
        "code": code,
        "sleeve": sleeve,
        "target_weight": weight,
        "matched_report_period": "2024-12-31",
        "matched_visible_date": "2025-03-30",
        "pit_status": "pass",
        "review_status": "automated_original_page_review_pass",
        "reviewed_metric_count": len(values),
    }
    for key in [
        "net_interest_margin_pct",
        "deposit_cost_pct",
        "special_mention_loan_ratio_pct",
        "net_interest_spread_pct",
        "interest_earning_assets_amount",
        "non_performing_loan_ratio_pct",
        "provision_coverage_ratio_pct",
        "core_tier1_capital_ratio_pct",
        "tariff_yuan_per_kwh",
        "utilization_hours",
        "generation_volume_yoy",
        "utilization_hours_yoy",
        "tariff_yuan_per_kwh_yoy",
        "fuel_cost_amount_yoy",
        "capacity_payment_flag",
        "hydro_water_flag",
    ]:
        row[key] = values.get(key, "")
    return row


def _signal(date: str, code: str, sleeve: str, weight: float) -> dict[str, object]:
    return {
        "trade_date": date,
        "code": code,
        "sector_id": sleeve,
        "strategy_id": "fixture",
        "selected_rank": 1,
        "selected_count": 4,
        "target_weight": weight,
        "score": 1,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
