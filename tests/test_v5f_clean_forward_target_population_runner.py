from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_clean_forward_target_population_runner import run_v5f_clean_forward_target_population


class V5fCleanForwardTargetPopulationRunnerTest(unittest.TestCase):
    def test_runner_freezes_forward_target_population_after_historical_boundary(self) -> None:
        summary = run_v5f_clean_forward_target_population(Path("."))

        self.assertEqual(summary["status"], "frozen_by_historical_operation_boundary")
        self.assertEqual(summary["pm_gate_decision"], "frozen_no_post_20260531_forward_target_operation")
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertEqual(summary["next_clean_rebalance_date"], "2026-10-08")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 1)
        self.assertFalse(summary["historical_boundary_audit"]["allowed"])

        out = Path("v5f_clean_forward_target_population") / "current"
        expected = [
            "v5f_clean_forward_target_population_summary.json",
            "v5f_clean_forward_target_population_report.md",
            "v5f_clean_forward_target_pm_gate_decision.csv",
            "v5f_clean_forward_target_blockers.csv",
            "v5f_clean_forward_target_historical_boundary_audit.csv",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_clean_forward_target_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["pm_gate_decision"], "frozen_no_post_20260531_forward_target_operation")
        self.assertEqual(decision["accepted"], "False")


if __name__ == "__main__":
    unittest.main()
