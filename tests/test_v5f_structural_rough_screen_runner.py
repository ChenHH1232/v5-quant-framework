from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_structural_rough_screen_runner import run_v5f_structural_rough_screen


class V5fStructuralRoughScreenRunnerTest(unittest.TestCase):
    def test_runner_screens_structural_directions_without_acceptance(self) -> None:
        summary = run_v5f_structural_rough_screen(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_structural_rough_screen")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "rough_screen_has_deep_research_candidates_not_accepted",
                "rough_screen_diagnostic_only_no_new_deep_candidate",
                "blocked_by_governance_issue",
            },
        )
        self.assertEqual(summary["backtest_scope_start"], "2021-05-01")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_structural_rough_screen") / "current"
        expected = [
            "v5f_structural_rough_screen_summary.json",
            "v5f_structural_rough_screen_spec.csv",
            "v5f_structural_rough_screen_weights.csv",
            "v5f_structural_rough_screen_daily_returns.csv",
            "v5f_structural_rough_screen_metrics.csv",
            "v5f_structural_rough_screen_yearly.csv",
            "v5f_structural_rough_screen_drawdown.csv",
            "v5f_structural_rough_screen_sleeve_contribution.csv",
            "v5f_structural_rough_screen_governance_audit.csv",
            "v5f_structural_rough_screen_comparison_matrix.csv",
            "v5f_structural_rough_screen_pm_decision.csv",
            "v5f_structural_rough_screen_next_queue.csv",
            "v5f_structural_rough_screen_blockers.csv",
            "v5f_structural_rough_screen_prompt.md",
            "v5f_structural_rough_screen_report.md",
            "v5f_structural_rough_screen_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_structural_rough_screen_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_structural_rough_screen_comparison_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["direction_id"] for row in csv.DictReader(f)}
        self.assertIn("internal_subsleeve_mom12_80_20", rows)
        self.assertIn("dual_sleeve_mom12_80_20", rows)
        self.assertIn("state_routed_mom12_70_30_or_100_0", rows)
        self.assertIn("admission_suppression_mom12_bottom_cap75", rows)


if __name__ == "__main__":
    unittest.main()
