from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_bank_power_industry_factor_weight_runner import run
from v5.v5f_structural_rough_screen_runner import PRICE_DIR, REPAIRED_RUN


class V5cBankPowerIndustryFactorWeightRunnerTest(unittest.TestCase):
    def test_industry_factor_weight_test_stays_observation_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fixture(root)
            summary_path = run(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_bank_power_industry_factor_weight_test")
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])
            self.assertFalse(summary["new_stock_selected"])

            out = root / "v5c_bank_power_industry_factor_weight_test" / "current"
            comparison = _read_csv(out / "v5c_bank_power_industry_factor_comparison.csv")
            self.assertIn("bank_power_specialist_overlay_on_v5f_10pct", {row["version_id"] for row in comparison})
            self.assertGreater(float(comparison[0]["delta_return_pct_points_vs_v5f_primary"]), 0)

            governance = _read_csv(out / "v5c_bank_power_industry_factor_governance_audit.csv")
            self.assertTrue(all(row["status"] in {"pass", "review"} for row in governance))
            preserved = next(row for row in governance if row["audit_id"] == "sleeve_weight_preserved")
            self.assertEqual(preserved["status"], "pass")


def _write_fixture(root: Path) -> None:
    price_dir = root / PRICE_DIR
    price_dir.mkdir(parents=True)
    rows = []
    codes = ["600001.XSHG", "600002.XSHG", "600003.XSHG", "600901.XSHG", "600902.XSHG", "600903.XSHG"]
    returns = {
        "600001.XSHG": 0.12,
        "600002.XSHG": 0.02,
        "600003.XSHG": -0.04,
        "600901.XSHG": 0.10,
        "600902.XSHG": 0.01,
        "600903.XSHG": -0.03,
    }
    for code in codes:
        rows.append({"date": "2021-05-06", "code": code, "close": 10.0})
        rows.append({"date": "2021-05-07", "code": code, "close": 10.0 * (1.0 + returns[code])})
    _write_csv(price_dir / "fixture_prices.csv", rows)

    run_dir = root / REPAIRED_RUN
    run_dir.mkdir(parents=True)
    signal_rows = []
    for code in codes[:3]:
        signal_rows.append(_signal("2021-05-06", code, "bank"))
    for code in codes[3:]:
        signal_rows.append(_signal("2021-05-06", code, "utilities_electricity"))
    _write_csv(run_dir / "rebalance_signals.csv", signal_rows)
    _write_csv(
        run_dir / "daily_returns.csv",
        [
            {"trade_date": "2021-05-06", "strategy_return": 0.0, "strategy_nav": 1.0},
            {"trade_date": "2021-05-07", "strategy_return": 0.0, "strategy_nav": 1.0},
        ],
    )

    rough = root / "v5f_structural_rough_screen" / "current"
    rough.mkdir(parents=True)
    primary_rows = []
    for row in signal_rows:
        primary_rows.append(
            {
                "version_id": "internal_subsleeve_mom12_70_30",
                "family": "v5f_primary_reference",
                "rebalance_date": row["trade_date"],
                "code": row["code"],
                "sleeve": row["sector_id"],
                "base_target_weight": row["target_weight"],
                "target_weight": row["target_weight"],
                "weight_delta": 0.0,
                "new_stock_selected": False,
            }
        )
    _write_csv(rough / "v5f_structural_rough_screen_weights.csv", primary_rows)

    p1 = root / "v5c_p1_financial_quality_pit_panel" / "current"
    p1.mkdir(parents=True)
    p2 = root / "v5c_p2_valuation_and_crowding_state_panel" / "current"
    p2.mkdir(parents=True)
    p1_rows = []
    p2_rows = []
    for i, row in enumerate(signal_rows):
        quality = 3 - (i % 3)
        p1_rows.append(
            {
                "trade_date": row["trade_date"],
                "code": row["code"],
                "sleeve_id": row["sector_id"],
                "dividend_yield_decimal": 0.02 + quality * 0.01,
                "operating_cash_flow_yield": 0.05 + quality * 0.02,
                "return_on_equity_ttm": quality * 5,
                "gross_profit_margin": quality * 10,
                "net_profit_margin": quality * 5,
                "non_performing_loan_ratio": 5 - quality,
                "provision_coverage_ratio": quality * 100,
                "core_tier_1_capital_adequacy_ratio": quality * 4,
                "capex_burden": 5 - quality,
                "asset_liability_ratio": 80 - quality,
                "visible_date_status": "pass",
                "quality_status": "pass",
            }
        )
        p2_rows.append(
            {
                "trade_date": row["trade_date"],
                "code": row["code"],
                "low_price_to_book": 1.0 / quality,
                "pb_cheapness_percentile_sleeve_cross_section": quality / 3,
                "valuation_cheapness_score": quality / 3,
                "valuation_state": "fixture",
                "pit_status": "pass",
            }
        )
    _write_csv(p1 / "v5c_p1_financial_quality_pit_panel.csv", p1_rows)
    _write_csv(p2 / "v5c_p2_valuation_state_panel.csv", p2_rows)


def _signal(date: str, code: str, sleeve: str) -> dict[str, object]:
    return {
        "trade_date": date,
        "code": code,
        "sector_id": sleeve,
        "strategy_id": "fixture",
        "selected_rank": 1,
        "selected_count": 6,
        "target_weight": 1 / 6,
        "score": 1,
        "used_factors": "fixture",
        "basket_scoring_scope": "fixture",
        "basket_scoring_sector": sleeve,
        "rebalance_event_type": "fixture",
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
