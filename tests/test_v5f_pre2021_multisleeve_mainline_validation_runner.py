from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from v5.v5f_pre2021_multisleeve_mainline_validation_runner import (
    BASELINE,
    PRIMARY,
    _build_weights,
    _spike_reclassification,
    run_v5f_pre2021_multisleeve_mainline_validation,
)


class V5fPre2021MultisleeveMainlineValidationRunnerTest(unittest.TestCase):
    def test_runner_blocks_when_inputs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_v5f_pre2021_multisleeve_mainline_validation(Path(tmp))

        self.assertEqual(summary["status"], "blocked_missing_required_inputs")
        self.assertGreater(summary["fatal_blocker_count"], 0)
        self.assertFalse(summary["accepted"])

    def test_build_weights_uses_existing_pool_only_and_holds_when_momentum_missing(self) -> None:
        preview = pd.DataFrame(
            [
                _preview("2019-04-01", "000001.XSHE", "bank", 1),
                _preview("2019-04-01", "000002.XSHE", "bank", 2),
                _preview("2019-04-01", "600001.XSHG", "utilities_electricity", 3),
            ]
        )
        prices = pd.DataFrame(
            [
                {"date": "2019-04-01", "code": "000001.XSHE", "mom_12_1": None},
                {"date": "2019-04-01", "code": "000002.XSHE", "mom_12_1": None},
                {"date": "2019-04-01", "code": "600001.XSHG", "mom_12_1": None},
            ]
        )

        rows = _build_weights(preview, prices)
        primary = [row for row in rows if row["version_id"] == PRIMARY]
        baseline = [row for row in rows if row["version_id"] == BASELINE]

        self.assertEqual({row["code"] for row in primary}, set(preview["code"]))
        self.assertEqual(len(primary), len(baseline))
        for row in primary:
            self.assertEqual(row["bucket"], "momentum_unavailable_hold_baseline")
            self.assertAlmostEqual(float(row["target_weight"]), float(row["base_target_weight"]))
            self.assertFalse(row["new_stock_selected"])

    def test_build_weights_applies_internal_subsleeve_when_momentum_available(self) -> None:
        preview = pd.DataFrame(
            [
                _preview("2020-10-09", "000001.XSHE", "bank", 1),
                _preview("2020-10-09", "000002.XSHE", "bank", 2),
                _preview("2020-10-09", "000003.XSHE", "bank", 3),
            ]
        )
        prices = pd.DataFrame(
            [
                {"date": "2020-10-09", "code": "000001.XSHE", "mom_12_1": 0.3},
                {"date": "2020-10-09", "code": "000002.XSHE", "mom_12_1": 0.1},
                {"date": "2020-10-09", "code": "000003.XSHE", "mom_12_1": -0.1},
            ]
        )

        primary = [row for row in _build_weights(preview, prices) if row["version_id"] == PRIMARY]
        by_code = {row["code"]: row for row in primary}

        self.assertEqual(by_code["000001.XSHE"]["bucket"], "momentum_subsleeve_30pct")
        self.assertGreater(float(by_code["000001.XSHE"]["target_weight"]), float(by_code["000001.XSHE"]["base_target_weight"]))
        self.assertLess(float(by_code["000003.XSHE"]["target_weight"]), float(by_code["000003.XSHE"]["base_target_weight"]))

    def test_spike_reclassification_stays_observation_only(self) -> None:
        rows = _spike_reclassification(
            {
                "validation_window_start": "2020-10-09",
                "validation_window_end": "2020-12-31",
                "validation_window_classification": "micro_sample",
                "limited_2020q4_directional_pass": True,
                "independent_validation_pass": False,
                "formal_promotion_allowed": False,
                "best_variant": "x",
                "best_net_incremental_return_pct_points": 0.04,
                "best_win_rate": 0.83,
            },
            [{"version_id": "x", "net_incremental_return_pct_points": "0.04", "win_rate": "0.83"}],
            {"backtest_delta_vs_primary_pct_points": 0.7},
        )

        self.assertEqual(rows[0]["status"], "observation_only_not_candidate")
        self.assertFalse(rows[0]["formal_independent_pass"])
        self.assertFalse(rows[0]["accepted"])

    def test_runner_completes_with_seeded_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_inputs(root)

            summary = run_v5f_pre2021_multisleeve_mainline_validation(root)

            self.assertEqual(summary["status"], "completed_pre2021_p0_p1_p2_validation")
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["threshold_scan_used"])


def _preview(date: str, code: str, sector: str, rank: int) -> dict[str, object]:
    return {
        "preview_date": date,
        "code": code,
        "sector_id": sector,
        "selected_rank": rank,
        "score": 1.0,
        "used_factors": "low_price_to_book;volatility_120d;dividend_yield",
        "preview_status": "complete_multisleeve_preview",
    }


def _seed_inputs(root: Path) -> None:
    data_gate = root / "v5f_pre2021_repaired_multisleeve_data_gate" / "current"
    spike = root / "v5f_spike_funded_mr_borrowing_independent_validation_gate" / "current"
    jq = root / "v5f_spike_mr_prebacktest_to_backtest_jq_sim" / "current"
    prices = root / "数据库" / "processed" / "startup_preload_repaired_prices_v5"
    for path in [data_gate, spike, jq, prices]:
        path.mkdir(parents=True, exist_ok=True)

    (data_gate / "v5f_pre2021_data_gate_summary.json").write_text(
        json.dumps({"pre2021_multisleeve_pool_status": "pre2021_multisleeve_pool_ready"}),
        encoding="utf-8",
    )
    sectors = ["bank", "utilities_electricity", "highway_infrastructure", "port_rail_infrastructure"]
    _write_csv(
        data_gate / "v5f_pre2021_multisleeve_panel_coverage.csv",
        [
            {
                "sector_id": sector,
                "panel_source_scope": "unit",
                "exists": "True",
                "row_count": "2",
                "pre2021_row_count": "2",
                "pre2021_date_count": "1",
                "pre2021_code_count": "1",
                "coverage_status": "pass_pre2021_candidate_rows",
            }
            for sector in sectors
        ],
    )
    _write_csv(
        data_gate / "v5f_pre2021_required_field_coverage.csv",
        [
            {"sector_id": sector, "field": field, "field_exists": "True", "pre2021_nonempty_rows": "1", "pre2021_nonempty_dates": "1", "field_status": "pass_pre2021"}
            for sector in sectors
            for field in ["low_vol_score", "volatility_120d", "dividend_yield"]
        ],
    )
    _write_csv(
        data_gate / "v5f_pre2021_price_coverage.csv",
        [
            {"sector_id": sector, "pre2021_row_count": "2", "pre2021_date_count": "2", "pre2021_code_count": "1"}
            for sector in sectors
        ],
    )
    _write_csv(
        data_gate / "v5f_pre2021_candidate_signal_preview.csv",
        [_preview("2020-10-09", f"00000{i}.XSHE", sector, i) for i, sector in enumerate(sectors, start=1)],
    )
    file_map = {
        "bank": "bank_v3_startup_repaired_daily_prices.csv",
        "utilities_electricity": "utilities_v51f_startup_repaired_daily_prices.csv",
        "highway_infrastructure": "highway_v54h_startup_repaired_daily_prices.csv",
        "port_rail_infrastructure": "port_rail_v55j_startup_repaired_daily_prices.csv",
    }
    for i, sector in enumerate(sectors, start=1):
        _write_csv(
            prices / file_map[sector],
            [
                {"date": "2020-10-09", "code": f"00000{i}.XSHE", "close": "10"},
                {"date": "2020-10-12", "code": f"00000{i}.XSHE", "close": str(10 + i)},
            ],
        )
    (spike / "v5f_spike_mr_validation_summary.json").write_text(
        json.dumps(
            {
                "validation_window_start": "2020-10-09",
                "validation_window_end": "2020-12-31",
                "validation_window_classification": "micro",
                "limited_2020q4_directional_pass": True,
                "independent_validation_pass": False,
                "formal_promotion_allowed": False,
                "best_variant": "x",
                "best_net_incremental_return_pct_points": 0.04,
                "best_win_rate": 0.8,
            }
        ),
        encoding="utf-8",
    )
    _write_csv(spike / "v5f_spike_mr_validation_metrics.csv", [{"version_id": "x", "net_incremental_return_pct_points": "0.04", "win_rate": "0.8"}])
    (jq / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json").write_text(
        json.dumps({"backtest_delta_vs_primary_pct_points": 0.7}),
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
