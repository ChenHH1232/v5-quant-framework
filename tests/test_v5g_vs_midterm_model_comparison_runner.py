from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5g_vs_midterm_model_comparison_runner import run_v5g_vs_midterm_model_comparison


class V5gVsMidtermModelComparisonRunnerTest(unittest.TestCase):
    def test_runner_keeps_midterm_champion_primary_after_v5g_comparison(self) -> None:
        summary = run_v5g_vs_midterm_model_comparison(Path("."))

        self.assertEqual(summary["status"], "completed_v5g_vs_midterm_model_comparison")
        self.assertEqual(
            summary["pm_gate_decision"],
            "midterm_internal_subsleeve_champion_remains_primary_v5g_new_models_secondary",
        )
        self.assertEqual(summary["best_new_model_id"], "v5g_01_state_gated_internal_subsleeve_70_30")
        self.assertEqual(summary["best_midterm_model_id"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["comparable_new_model_count"], 1)
        self.assertEqual(summary["non_nav_new_gate_count"], 4)
        self.assertGreater(summary["best_new_delta_return_pct_points_vs_baseline"], 0.0)
        self.assertLess(summary["delta_return_pct_points_vs_midterm_champion"], 0.0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5g_vs_midterm_model_comparison") / "current"
        expected = [
            "v5g_vs_midterm_summary.json",
            "v5g_vs_midterm_report.md",
            "v5g_new_model_result_matrix.csv",
            "v5g_vs_midterm_top_model_comparison.csv",
            "v5g_delta_vs_midterm_champion.csv",
            "v5g_vs_midterm_governance_audit.csv",
            "v5g_vs_midterm_pm_gate_decision.csv",
            "v5g_vs_midterm_next_agent_queue.csv",
            "v5g_vs_midterm_blockers.csv",
            "v5g_vs_midterm_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5g_delta_vs_midterm_champion.csv").open("r", encoding="utf-8-sig", newline="") as f:
            delta = list(csv.DictReader(f))[0]
        self.assertEqual(delta["new_model_id"], "v5g_01_state_gated_internal_subsleeve_70_30")
        self.assertEqual(delta["midterm_champion_id"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(delta["beats_midterm_champion"], "False")
        self.assertLess(float(delta["delta_return_pct_points_vs_midterm_champion"]), 0.0)

        with (out / "v5g_new_model_result_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["model_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(rows["v5g_01_state_gated_internal_subsleeve_70_30"]["nav_comparable"], "True")
        self.assertEqual(rows["v5g_04_511360_exit_policy_spec"]["nav_comparable"], "False")
        self.assertEqual(rows["v5g_02_quality_guarded_momentum_factor_validation"]["status"], "diagnostic_only_negative_factor_validation")

        with (out / "v5g_vs_midterm_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in governance))


if __name__ == "__main__":
    unittest.main()
