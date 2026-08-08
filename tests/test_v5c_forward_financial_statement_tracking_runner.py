from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_forward_financial_statement_tracking_runner import (
    OUT_DIR,
    run_v5c_forward_financial_statement_tracking,
)


class V5cForwardFinancialStatementTrackingRunnerTest(unittest.TestCase):
    def test_runner_opens_observation_only_forward_tracking(self) -> None:
        summary = run_v5c_forward_financial_statement_tracking(Path("."))

        self.assertEqual(summary["status"], "completed_forward_financial_statement_tracking_packet")
        self.assertEqual(summary["pm_gate_decision"], "forward_financial_statement_tracking_open_observation_only")
        self.assertGreater(summary["open_prediction_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_primary_modified"])
        self.assertFalse(summary["trade_rule_added"])
        self.assertFalse(summary["weight_change_added"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path(".") / OUT_DIR
        expected = [
            "v5c_forward_financial_statement_tracking_summary.json",
            "v5c_forward_financial_statement_tracking_report.md",
            "v5c_forward_financial_statement_prediction_ledger.csv",
            "v5c_forward_financial_statement_open_report_queue.csv",
            "v5c_forward_financial_statement_pm_gate_decision.csv",
            "v5c_v5f_weight_confidence_freeze_decision.csv",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_forward_financial_statement_prediction_ledger.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            ledger = list(csv.DictReader(handle))
        self.assertTrue(all(row["trade_impact"] == "none" for row in ledger))
        self.assertTrue(all(row["weight_impact"] == "none" for row in ledger))

        with (out / "v5c_v5f_weight_confidence_freeze_decision.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            freeze = list(csv.DictReader(handle))[0]
        self.assertEqual(freeze["v5f_weight_confidence_tag_spec_status"], "blocked_until_forward_or_pre2021_evidence")
        self.assertEqual(freeze["admit_engineering_backtest_now"], "False")


if __name__ == "__main__":
    unittest.main()
