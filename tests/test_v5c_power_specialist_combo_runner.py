from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_power_specialist_combo_runner import OUT_DIR, OVERLAY_VERSION, UTILITIES_PANEL, run
from v5.v5f_structural_rough_screen_runner import PRICE_DIR, REPAIRED_RUN


class V5cPowerSpecialistComboRunnerTest(unittest.TestCase):
    def test_runner_outputs_power_combo_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fixture(root)
            summary_path = run(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_power_specialist_combo_deep_dive")
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])
            self.assertFalse(summary["v5f_primary_modified"])
            self.assertFalse(summary["formal_backtest_used_as_validation"])

            out = root / OUT_DIR
            comparison = _read_csv(out / "v5c_power_combo_formal_comparison.csv")
            self.assertIn(OVERLAY_VERSION, {row["version_id"] for row in comparison})
            governance = _read_csv(out / "v5c_power_combo_governance_audit.csv")
            changed = next(row for row in governance if row["audit_id"] == "only_power_sleeve_changed_vs_v5f_primary")
            self.assertEqual(changed["status"], "pass")


def _write_fixture(root: Path) -> None:
    split = root / "v5_sample_split_governance_correction" / "current"
    split.mkdir(parents=True)
    (split / "v5_sample_split_rules.md").write_text("fixture", encoding="utf-8")

    screen = root / "v5c_cross_sector_pre2021_factor_screen" / "current"
    screen.mkdir(parents=True)
    _write_csv(
        screen / "v5c_cross_sector_pre2021_factor_comparison.csv",
        [
            {
                "factor_id": factor,
                "train_delta_pct_points": 1.0,
                "strict_delta_pct_points": 0.5,
            }
            for factor in [
                "utilities_low_pb",
                "utilities_ocf_yield",
                "utilities_cashflow_subindustry_score",
                "utilities_roe",
            ]
        ],
    )

    preview = root / "v5f_pre2021_repaired_multisleeve_data_gate" / "current"
    preview.mkdir(parents=True)
    _write_csv(
        preview / "v5f_pre2021_candidate_signal_preview.csv",
        [
            {"preview_date": "2020-04-01", "code": "600001.XSHG", "sector_id": "utilities_electricity"},
            {"preview_date": "2020-04-01", "code": "600002.XSHG", "sector_id": "utilities_electricity"},
            {"preview_date": "2020-04-01", "code": "600003.XSHG", "sector_id": "utilities_electricity"},
        ],
    )

    panel_path = root / UTILITIES_PANEL
    panel_path.parent.mkdir(parents=True)
    panel_rows = []
    for date in ["2020-04-01", "2021-05-06"]:
        panel_rows.extend(
            [
                _panel_row(date, "600001.XSHG", 1.0, 0.10),
                _panel_row(date, "600002.XSHG", 2.0, 0.02),
                _panel_row(date, "600003.XSHG", 3.0, -0.04),
            ]
        )
    _write_csv(panel_path, panel_rows)

    price_dir = root / PRICE_DIR
    price_dir.mkdir(parents=True)
    _write_csv(
        price_dir / "fixture_prices.csv",
        [
            {"date": "2021-05-06", "code": "600001.XSHG", "close": 10.0},
            {"date": "2021-05-07", "code": "600001.XSHG", "close": 11.0},
            {"date": "2021-05-06", "code": "600002.XSHG", "close": 10.0},
            {"date": "2021-05-07", "code": "600002.XSHG", "close": 10.2},
            {"date": "2021-05-06", "code": "600003.XSHG", "close": 10.0},
            {"date": "2021-05-07", "code": "600003.XSHG", "close": 9.6},
        ],
    )

    run_dir = root / REPAIRED_RUN
    run_dir.mkdir(parents=True)
    signals = [
        {"trade_date": "2021-05-06", "code": "600001.XSHG", "sector_id": "utilities_electricity", "target_weight": 1 / 3},
        {"trade_date": "2021-05-06", "code": "600002.XSHG", "sector_id": "utilities_electricity", "target_weight": 1 / 3},
        {"trade_date": "2021-05-06", "code": "600003.XSHG", "sector_id": "utilities_electricity", "target_weight": 1 / 3},
    ]
    _write_csv(run_dir / "rebalance_signals.csv", signals)
    _write_csv(
        run_dir / "daily_returns.csv",
        [
            {"trade_date": "2021-05-06", "strategy_return": 0.0, "strategy_nav": 1.0},
            {"trade_date": "2021-05-07", "strategy_return": 0.0, "strategy_nav": 1.0},
        ],
    )

    rough = root / "v5f_structural_rough_screen" / "current"
    rough.mkdir(parents=True)
    _write_csv(
        rough / "v5f_structural_rough_screen_weights.csv",
        [
            {
                "version_id": "internal_subsleeve_mom12_70_30",
                "family": "fixture",
                "rebalance_date": row["trade_date"],
                "code": row["code"],
                "sleeve": row["sector_id"],
                "base_target_weight": row["target_weight"],
                "target_weight": row["target_weight"],
                "weight_delta": 0.0,
                "accepted": False,
            }
            for row in signals
        ],
    )


def _panel_row(date: str, code: str, pb: float, future_return: float) -> dict[str, object]:
    good = 4.0 - pb
    return {
        "trade_date": date,
        "code": code,
        "sector_id": "utilities_electricity",
        "low_price_to_book": pb,
        "operating_cash_flow_yield": good,
        "cashflow_yield_subindustry_score": good,
        "return_on_equity_ttm": good,
        "future_return": future_return,
        "factor_visible_date": "2020-03-31" if date < "2021-01-01" else "2021-04-30",
        "universe_visible_date": "2020-03-31" if date < "2021-01-01" else "2021-04-30",
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
