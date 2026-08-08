from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_internal_subsleeve_formal_review_runner import run_v5f_internal_subsleeve_formal_review


class V5fInternalSubSleeveFormalReviewRunnerTest(unittest.TestCase):
    def test_runner_promotes_to_forward_candidate_without_acceptance(self) -> None:
        summary = run_v5f_internal_subsleeve_formal_review(Path("."))

        review = summary["review"]
        forward = summary["forward"]
        self.assertEqual(review["status"], "completed_v5f_internal_subsleeve_pm_quant_review")
        self.assertEqual(forward["status"], "completed_v5f_internal_subsleeve_forward_paper_tracking_packet")
        self.assertEqual(review["pm_gate_decision"], "promote_internal_subsleeve_70_30_to_forward_paper_candidate_not_accepted")
        self.assertEqual(forward["pm_gate_decision"], "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal")
        self.assertEqual(review["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertGreater(review["delta_return_pct_points_vs_repaired_baseline"], 5.0)
        self.assertFalse(review["accepted"])
        self.assertFalse(review["live_trading_approved"])
        self.assertFalse(review["deployment_approved"])
        self.assertFalse(forward["accepted"])
        self.assertFalse(forward["live_trading_approved"])
        self.assertFalse(forward["deployment_approved"])

        review_out = Path("v5f_internal_subsleeve_pm_quant_review") / "current"
        forward_out = Path("v5f_internal_subsleeve_forward_paper_tracking") / "current"
        for name in [
            "v5f_internal_subsleeve_review_summary.json",
            "v5f_internal_subsleeve_candidate_checks.csv",
            "v5f_internal_subsleeve_risk_benefit_matrix.csv",
            "v5f_internal_subsleeve_candidate_matrix.csv",
            "v5f_internal_subsleeve_pm_gate_decision.csv",
            "v5f_internal_subsleeve_review_next_queue.csv",
            "v5f_internal_subsleeve_review_report.md",
        ]:
            self.assertTrue((review_out / name).exists(), name)
        for name in [
            "v5f_internal_subsleeve_forward_summary.json",
            "v5f_internal_subsleeve_forward_candidate_status.csv",
            "v5f_internal_subsleeve_forward_schema.csv",
            "v5f_internal_subsleeve_rebalance_day_checklist.csv",
            "v5f_internal_subsleeve_forward_next_queue.csv",
        ]:
            self.assertTrue((forward_out / name).exists(), name)

        with (review_out / "v5f_internal_subsleeve_candidate_checks.csv").open("r", encoding="utf-8-sig", newline="") as f:
            checks = list(csv.DictReader(f))
        self.assertTrue(all(row["pass"] == "True" for row in checks))


if __name__ == "__main__":
    unittest.main()
