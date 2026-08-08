from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_profit_lock_execution_robust_formal_review_runner import (
    NEW_PRIMARY,
    run_v5e_profit_lock_execution_robust_formal_review,
)


class V5eProfitLockExecutionRobustFormalReviewRunnerTest(unittest.TestCase):
    def test_runner_promotes_profit_lock_review_candidate_without_acceptance(self) -> None:
        root = Path(".")
        summary = run_v5e_profit_lock_execution_robust_formal_review(root)

        self.assertEqual(summary["status"], "completed_profit_lock_execution_robust_formal_review")
        self.assertEqual(summary["pm_decision"], "promote_profit_lock_main_to_execution_robust_review_candidate_not_accepted")
        self.assertEqual(summary["primary_candidate"], NEW_PRIMARY)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_replacement"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["minute_data_used_for_trigger"])
        self.assertGreater(summary["new_primary_vwap_adjusted_delta_vs_baseline"], 0)
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_profit_lock_execution_robust_formal_review" / "current"
        with (out / "v5e_profit_lock_execution_robust_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["accepted"], "False")
        self.assertEqual(rows[0]["next_gate"], "v5e_profit_lock_main_forward_paper_execution_tracking")


if __name__ == "__main__":
    unittest.main()
