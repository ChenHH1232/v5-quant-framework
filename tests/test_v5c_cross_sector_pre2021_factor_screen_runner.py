from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_cross_sector_pre2021_factor_screen_runner import (
    OUT_DIR,
    SECTOR_SPECS,
    _assign_buckets,
    run,
)


class V5cCrossSectorPre2021FactorScreenRunnerTest(unittest.TestCase):
    def test_assign_buckets_marks_top_and_bottom(self) -> None:
        import pandas as pd

        df = pd.DataFrame({"score": [1.0, 2.0, 3.0], "future_return_num": [0.0, 0.0, 0.0]})
        result = _assign_buckets(df)
        self.assertEqual(result["bucket"].tolist(), ["bottom", "middle", "top"])

    def test_runner_outputs_cross_sector_screen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fixture(root)
            summary_path = run(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_cross_sector_pre2021_factor_screen")
            self.assertFalse(summary["formal_backtest_used_as_validation"])
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])

            out = root / OUT_DIR
            comparison = _read_csv(out / "v5c_cross_sector_pre2021_factor_comparison.csv")
            self.assertTrue(comparison)
            decision = _read_csv(out / "v5c_cross_sector_pre2021_pm_gate_decision.csv")
            self.assertEqual(decision[0]["accepted"], "False")


def _write_fixture(root: Path) -> None:
    split = root / "v5_sample_split_governance_correction" / "current"
    split.mkdir(parents=True)
    (split / "v5_sample_split_rules.md").write_text("fixture", encoding="utf-8")

    preview = root / "v5f_pre2021_repaired_multisleeve_data_gate" / "current"
    preview.mkdir(parents=True)
    _write_csv(
        preview / "v5f_pre2021_candidate_signal_preview.csv",
        [
            {"preview_date": "2020-04-01", "code": "600001.XSHG", "sector_id": "utilities_electricity"},
            {"preview_date": "2020-04-01", "code": "600002.XSHG", "sector_id": "utilities_electricity"},
            {"preview_date": "2020-04-01", "code": "600003.XSHG", "sector_id": "utilities_electricity"},
            {"preview_date": "2020-04-01", "code": "600101.XSHG", "sector_id": "highway_infrastructure"},
            {"preview_date": "2020-04-01", "code": "600102.XSHG", "sector_id": "highway_infrastructure"},
            {"preview_date": "2020-04-01", "code": "600103.XSHG", "sector_id": "highway_infrastructure"},
            {"preview_date": "2020-04-01", "code": "600201.XSHG", "sector_id": "port_rail_infrastructure"},
            {"preview_date": "2020-04-01", "code": "600202.XSHG", "sector_id": "port_rail_infrastructure"},
            {"preview_date": "2020-04-01", "code": "600203.XSHG", "sector_id": "port_rail_infrastructure"},
        ],
    )

    for spec in SECTOR_SPECS:
        path = root / spec.panel_path
        path.parent.mkdir(parents=True)
        if spec.sector_id == "utilities_electricity":
            codes = ["600001.XSHG", "600002.XSHG", "600003.XSHG"]
            rows = [_row("2020-04-01", code, index, "utilities_electricity") for index, code in enumerate(codes)]
        elif spec.sector_id == "highway_infrastructure":
            codes = ["600101.XSHG", "600102.XSHG", "600103.XSHG"]
            rows = [_row("2020-04-01", code, index, "highway_infrastructure") for index, code in enumerate(codes)]
        else:
            codes = ["600201.XSHG", "600202.XSHG", "600203.XSHG"]
            rows = [_row("2020-04-01", code, index, "port_rail_infrastructure") for index, code in enumerate(codes)]
        _write_csv(path, rows)


def _row(date: str, code: str, index: int, sector: str) -> dict[str, object]:
    good = 3 - index
    ret = [0.10, 0.02, -0.05][index]
    return {
        "trade_date": date,
        "code": code,
        "future_return": ret,
        "low_price_to_book": index + 1,
        "dividend_yield": good,
        "operating_cash_flow_yield": good,
        "return_on_equity_ttm": good,
        "gross_profit_margin": good,
        "net_profit_margin": good,
        "operating_cash_flow_to_net_profit": good,
        "interest_coverage": good,
        "capex_burden": index + 1,
        "asset_liability_ratio": index + 1,
        "cashflow_yield_subindustry_score": good,
        "low_pb_subindustry_score": good,
        "dividend_cashflow_support_score": good,
        "capex_control_score": good,
        "leverage_control_score": good,
        "volatility_120d": index + 1,
        "max_drawdown_120d": index + 1,
        "low_vol_score": good,
        "pcf_ncf_ttm_inverse_proxy": good,
        "dividend_cash_per_share_used": good,
        "factor_visible_date": "2020-03-31",
        "universe_visible_date": "2020-03-31",
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
