from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_internal_subsleeve_deep_engineering_runner import run_v5f_internal_subsleeve_deep_engineering


class V5fInternalSubSleeveDeepEngineeringRunnerTest(unittest.TestCase):
    def test_runner_promotes_70_30_without_acceptance(self) -> None:
        summary = run_v5f_internal_subsleeve_deep_engineering(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_internal_subsleeve_deep_engineering")
        self.assertEqual(
            summary["pm_gate_decision"],
            "promote_internal_subsleeve_70_30_to_v5f_candidate_not_accepted",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertGreater(summary["primary_delta_return_pct_points_vs_repaired_baseline"], 5.0)
        self.assertLessEqual(summary["primary_delta_max_drawdown_pct_points_vs_repaired_baseline"], 0.0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_internal_subsleeve_deep_engineering") / "current"
        expected = [
            "v5f_internal_subsleeve_deep_summary.json",
            "v5f_internal_subsleeve_deep_metrics.csv",
            "v5f_internal_subsleeve_yearly_stability.csv",
            "v5f_internal_subsleeve_rebalance_period_stability.csv",
            "v5f_internal_subsleeve_sleeve_attribution.csv",
            "v5f_internal_subsleeve_stock_concentration.csv",
            "v5f_internal_subsleeve_top_contribution_events.csv",
            "v5f_internal_subsleeve_turnover_cost_review.csv",
            "v5f_internal_subsleeve_governance_audit.csv",
            "v5f_internal_subsleeve_vs_current_overlay.csv",
            "v5f_internal_subsleeve_pm_gate_decision.csv",
            "v5f_internal_subsleeve_next_queue.csv",
            "v5f_internal_subsleeve_deep_blockers.csv",
            "v5f_internal_subsleeve_next_prompt.md",
            "v5f_internal_subsleeve_deep_report.md",
            "v5f_internal_subsleeve_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_internal_subsleeve_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_internal_subsleeve_vs_current_overlay.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(rows["internal_subsleeve_mom12_70_30"]["beats_current_on_return"], "True")


if __name__ == "__main__":
    unittest.main()
