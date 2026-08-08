from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_market_cap_pit_source_repair_runner import run_v5h_market_cap_pit_source_repair


class V5hMarketCapPitSourceRepairRunnerTest(unittest.TestCase):
    def test_runner_repairs_total_market_cap_with_attempt_1_and_skips_later_attempts(self) -> None:
        summary = run_v5h_market_cap_pit_source_repair(Path("."))

        self.assertEqual(summary["status"], "completed_attempt_1_daily_total_market_cap_repair")
        self.assertEqual(summary["repair_decision"], "attempt_1_success_later_steps_skipped")
        self.assertEqual(summary["succeeded_attempt"], "1")
        self.assertTrue(summary["later_steps_skipped"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertGreater(summary["repaired_rows"], 0)
        self.assertEqual(summary["missing_rows_before"], summary["repaired_rows"])

        out = Path("v5h_market_cap_pit_source_repair") / "current"
        for name in [
            "v5h_market_cap_pit_source_repair_summary.json",
            "v5h_market_cap_pit_source_repair_report.md",
            "v5h_market_cap_missing_rows_before.csv",
            "v5h_market_cap_source_attempt_order.csv",
            "v5h_market_cap_source_probe_result.csv",
            "v5h_market_cap_repaired_rows.csv",
            "v5h_market_cap_repair_decision.csv",
            "v5h_market_cap_repair_blockers.csv",
            "v5h_market_cap_repair_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_market_cap_source_attempt_order.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            attempts = list(csv.DictReader(handle))
        self.assertEqual(attempts[0]["status"], "success")
        self.assertEqual(attempts[1]["status"], "skipped_after_attempt_1_success")
        self.assertEqual(attempts[2]["status"], "skipped_after_attempt_1_success")


if __name__ == "__main__":
    unittest.main()
