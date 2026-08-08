from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_profit_lock_main_forward_paper_tracking_runner import (
    PRIMARY,
    run_v5e_profit_lock_main_forward_paper_tracking,
)


class V5eProfitLockMainForwardPaperTrackingRunnerTest(unittest.TestCase):
    def test_runner_prepares_tracking_packet_without_acceptance(self) -> None:
        root = Path(".")
        summary = run_v5e_profit_lock_main_forward_paper_tracking(root)

        self.assertEqual(summary["status"], "completed_forward_paper_tracking_packet")
        self.assertEqual(summary["pm_decision"], "paper_tracking_ready_waiting_forward_records")
        self.assertEqual(summary["candidate_id"], PRIMARY)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["minute_data_used_for_trigger"])
        self.assertEqual(summary["profit_lock_threshold"], 0.20)
        self.assertEqual(summary["sell_fraction"], 0.50)
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_profit_lock_main_forward_paper_execution_tracking" / "current"
        self.assertTrue((out / "v5e_profit_lock_forward_signal_template.csv").exists())
        self.assertTrue((out / "v5e_profit_lock_forward_execution_tracking_template.csv").exists())
        with (out / "v5e_profit_lock_forward_paper_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["accepted"], "False")
        self.assertEqual(rows[0]["next_gate"], "collect_forward_paper_records_then_pm_review")


if __name__ == "__main__":
    unittest.main()
