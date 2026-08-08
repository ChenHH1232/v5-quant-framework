from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5f_pre2021_factor_panel_repair_runner import run_v5f_pre2021_factor_panel_repair


class V5fPre2021FactorPanelRepairRunnerTest(unittest.TestCase):
    def test_runner_generates_only_strict_pit_visible_port_rail_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "database"
            price_root = db / "processed" / "startup_preload_repaired_prices_v5"
            port_evidence_root = (
                db
                / "processed"
                / "port_rail_operating_evidence_v55h"
                / "reviewed_evidence_v55j"
            )
            highway_evidence_root = (
                db
                / "processed"
                / "highway_operating_data"
                / "annual_reports_2020_2025"
            )

            _write_csv(
                price_root / "port_rail_v55j_startup_repaired_daily_prices.csv",
                [
                    {"trade_date": "2020-10-09", "code": "600017.XSHG", "open": "2.8", "close": "2.8"},
                ],
            )
            _write_csv(
                price_root / "highway_v54h_startup_repaired_daily_prices.csv",
                [
                    {"trade_date": "2020-10-09", "code": "600035.XSHG", "open": "4.1", "close": "4.1"},
                ],
            )
            _write_csv(
                port_evidence_root / "port_rail_segment_business_evidence_reviewed_v55j.csv",
                [
                    {
                        "visible_date": "2020-08-27",
                        "code": "600017.XSHG",
                        "pit_usable": "true",
                        "approved_port_rail_business_tag": "core_port_operator",
                    },
                    {
                        "visible_date": "2021-03-30",
                        "code": "600018.XSHG",
                        "pit_usable": "true",
                        "approved_port_rail_business_tag": "core_port_operator",
                    },
                ],
            )
            _write_csv(
                highway_evidence_root / "highway_reviewed_operating_disclosure_data.csv",
                [
                    {
                        "visible_date": "2021-04-29",
                        "code": "600035.XSHG",
                        "pit_usable": "true",
                    }
                ],
            )

            summary = run_v5f_pre2021_factor_panel_repair(root, fetch_baostock=False)

            self.assertEqual(summary["port_rail_strict_rows"], 1)
            self.assertEqual(summary["highway_strict_rows"], 0)
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])

            out = root / "v5f_pre2021_factor_panel_repair" / "current"
            strict_path = out / "v5f_pre2021_port_rail_v55j_strict_panel_with_low_vol.csv"
            self.assertTrue(strict_path.exists())
            with strict_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["trade_date"], "2020-10-09")
            self.assertEqual(rows[0]["code"], "600017.XSHG")
            self.assertEqual(rows[0]["pre2021_universe_pit_status"], "pass")

            with (out / "v5f_pre2021_factor_panel_repair_blockers.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                blockers = {row["blocker_id"]: row for row in csv.DictReader(handle)}
            self.assertIn("highway_pre2021_strict_pit_universe_missing", blockers)
            self.assertIn("port_rail_pre2021_strict_pit_universe_partial", blockers)

            payload = json.loads((out / "v5f_pre2021_factor_panel_repair_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["pm_gate_decision"], "pre2021_factor_panel_repair_partial_not_complete_multisleeve")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
