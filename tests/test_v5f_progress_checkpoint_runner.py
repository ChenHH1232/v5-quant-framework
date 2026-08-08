from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_progress_checkpoint_runner import run_v5f_progress_checkpoint


class V5fProgressCheckpointRunnerTest(unittest.TestCase):
    def test_runner_reports_next_forward_only_step(self) -> None:
        summary = run_v5f_progress_checkpoint(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_progress_checkpoint")
        self.assertEqual(summary["pm_gate_decision"], "v5f_wait_for_next_repaired_v57f_rebalance_paper_tracking")
        self.assertEqual(summary["candidate_id"], "momentum_plus_mean_reversion_equal_blend")
        self.assertTrue(summary["requires_future_rebalance_signal"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_progress_checkpoint") / "current"
        expected = [
            "v5f_progress_summary.json",
            "v5f_progress_status_matrix.csv",
            "v5f_progress_candidate_matrix.csv",
            "v5f_progress_next_action_matrix.csv",
            "v5f_progress_pm_decision.csv",
            "v5f_progress_blockers.csv",
            "v5f_progress_next_prompt.md",
            "v5f_progress_report.md",
            "v5f_progress_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_progress_pm_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")
        self.assertEqual(decision["deployment_approved"], "False")

        prompt = (out / "v5f_progress_next_prompt.md").read_text(encoding="utf-8")
        self.assertIn("momentum_plus_mean_reversion_equal_blend", prompt)
        self.assertIn("official startup-preload repaired V57f", prompt)


if __name__ == "__main__":
    unittest.main()
