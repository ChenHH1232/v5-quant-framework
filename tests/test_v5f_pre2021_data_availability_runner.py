from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5f_pre2021_data_availability_runner import run_v5f_pre2021_data_availability_gate


class V5fPre2021DataAvailabilityRunnerTest(unittest.TestCase):
    def test_runner_blocks_complete_pool_without_all_pre2021_sleeve_panels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir(parents=True)
            db = root / "db" / "processed"
            panel_root = db / "startup_preload_repaired_panels_v5"
            price_root = db / "startup_preload_repaired_prices_v5"

            sectors = [
                ("bank", "bank_v3_repaired"),
                ("utilities_electricity", "utilities_v51f"),
                ("highway_infrastructure", "highway_v54h"),
                ("port_rail_infrastructure", "port_rail_v55j"),
            ]
            for sector_id, folder in sectors:
                panel_dir = panel_root / folder
                panel_dir.mkdir(parents=True)
                if sector_id in {"bank", "utilities_electricity"}:
                    _write_csv(
                        panel_dir / "panel_with_low_vol.csv",
                        [
                            {
                                "trade_date": "2020-12-31",
                                "code": "600000.XSHG",
                                "low_vol_score": "0.8",
                                "volatility_120d": "0.1",
                                "dividend_yield": "0.04",
                            }
                        ],
                    )
                else:
                    _write_csv(
                        panel_dir / "panel_with_low_vol.csv",
                        [
                            {
                                "trade_date": "2021-05-06",
                                "code": "600000.XSHG",
                                "low_vol_score": "0.8",
                                "volatility_120d": "0.1",
                                "dividend_yield": "0.04",
                            }
                        ],
                    )
                price_root.mkdir(parents=True, exist_ok=True)
                _write_csv(
                    price_root / f"{folder}_prices.csv",
                    [
                        {"trade_date": "2020-12-31", "code": "600000.XSHG", "open": "10", "close": "10.1"},
                        {"trade_date": "2021-05-06", "code": "600000.XSHG", "open": "10", "close": "10.1"},
                    ],
                )

            config = {
                "project": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
                "sectors": [
                    {
                        "sector_id": sector_id,
                        "strategy_id": sector_id,
                        "panel_csv": f"db/processed/startup_preload_repaired_panels_v5/{folder}/panel_with_low_vol.csv",
                        "price_csv": f"db/processed/startup_preload_repaired_prices_v5/{folder}_prices.csv",
                    }
                    for sector_id, folder in sectors
                ],
                "signals": {
                    "factors": [{"name": "low_vol_score", "direction": "higher_is_better"}],
                    "scoring": {
                        "method": "weighted_composite",
                        "normalization_scope": "sector_adaptive",
                        "min_factor_count": 1,
                        "weights": {"low_vol_score": 1.0},
                    },
                },
                "portfolio": {
                    "start_date": "2021-05-01",
                    "end_date": "2026-05-31",
                    "required_fields": ["low_vol_score", "volatility_120d", "dividend_yield"],
                },
            }
            (config_dir / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json").write_text(
                json.dumps(config),
                encoding="utf-8",
            )

            summary = run_v5f_pre2021_data_availability_gate(root, probe_baostock=False)

            self.assertEqual(summary["pre2021_multisleeve_pool_status"], "pre2021_pool_blocked_by_required_fields")
            self.assertFalse(summary["complete_v57f_repaired_multisleeve_pool_available"])
            self.assertFalse(summary["v4_5min_required"])
            self.assertFalse(summary["post_20260531_required"])

            out = root / "v5f_pre2021_repaired_multisleeve_data_gate" / "current"
            self.assertTrue((out / "v5f_pre2021_data_gate_summary.json").exists())
            self.assertTrue((out / "v5f_pre2021_multisleeve_panel_coverage.csv").exists())
            self.assertTrue((out / "v5f_pre2021_missing_data_blockers.csv").exists())

            with (out / "v5f_pre2021_missing_data_blockers.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                blockers = {row["blocker_id"]: row for row in csv.DictReader(handle)}
            self.assertEqual(blockers["v4_5min_not_required"]["severity"], "not_a_blocker")
            self.assertEqual(blockers["post_20260531_not_required"]["severity"], "not_a_blocker")
            self.assertIn("missing_pre2021_required_panel_highway_infrastructure", blockers)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
