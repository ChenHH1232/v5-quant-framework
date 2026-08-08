from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_internal_subsleeve_queue_123_runner import run_v5f_internal_subsleeve_queue_123


class V5fInternalSubSleeveQueue123RunnerTest(unittest.TestCase):
    def test_runner_executes_queue_without_using_late_signal_as_clean_forward(self) -> None:
        summary = run_v5f_internal_subsleeve_queue_123(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_internal_subsleeve_queue_123_execution")
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["pm_gate_decision"], "queue_123_completed_forward_targets_pending_combined_review_ready")
        self.assertEqual(
            summary["target_population_status"],
            "not_populated_waiting_next_clean_official_repaired_v57f_targets",
        )
        self.assertGreater(summary["delta_return_pct_points_vs_repaired_baseline"], 10.0)
        self.assertGreater(summary["incremental_delta_return_vs_prior_primary"], 10.0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_internal_subsleeve_queue_123_execution") / "current"
        for name in [
            "v5f_queue_123_summary.json",
            "v5f_queue_123_official_rebalance_signal_audit.csv",
            "v5f_queue_123_paper_target_population_status.csv",
            "v5f_queue_123_required_input_queue.csv",
            "v5f_queue_123_paper_target_template.csv",
            "v5f_queue_123_forward_evidence_closeout_framework.csv",
            "v5f_queue_123_forward_closeout_status.csv",
            "v5f_queue_123_v5c_v5e_conflict_matrix.csv",
            "v5f_queue_123_pm_decision.csv",
            "v5f_queue_123_next_queue.csv",
            "v5f_queue_123_report.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_queue_123_official_rebalance_signal_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = {row["source_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(audit["late_shadow_signal_20260701"]["audit_status"], "reference_only_not_clean_forward")
        self.assertEqual(audit["paper_input_preflight_20261008"]["audit_status"], "forward_only_pending")

        with (out / "v5f_queue_123_v5c_v5e_conflict_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            conflicts = {row["component"]: row for row in csv.DictReader(f)}
        self.assertEqual(conflicts["V5c_ERC"]["conflict_status"], "separate_review_required_before_combination")
        self.assertEqual(conflicts["V5e_511360_cash_proxy"]["conflict_status"], "separate_review_required_before_combination")


if __name__ == "__main__":
    unittest.main()
