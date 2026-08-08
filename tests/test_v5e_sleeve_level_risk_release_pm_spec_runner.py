from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_sleeve_level_risk_release_pm_spec_runner import run_v5e_sleeve_level_risk_release_pm_spec


class V5eSleeveLevelRiskReleasePMSpecRunnerTest(unittest.TestCase):
    def test_runner_generates_pm_spec_without_engineering(self) -> None:
        root = Path(".")
        summary = run_v5e_sleeve_level_risk_release_pm_spec(root)

        self.assertEqual(summary["status"], "completed_sleeve_level_risk_release_pm_spec")
        self.assertEqual(
            summary["pm_admission_decision"],
            "admit_sleeve_level_risk_release_to_quant_spec_not_engineering",
        )
        self.assertEqual(summary["candidate_direction_count"], 4)
        self.assertEqual(summary["quant_spec_allowed_count"], 2)
        self.assertFalse(summary["engineering_backtest_run"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["new_threshold_added"])
        self.assertFalse(summary["reentry_allowed"])
        self.assertFalse(summary["cross_sleeve_transfer_allowed"])
        self.assertFalse(summary["accepted"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_sleeve_level_risk_release_pm_spec" / "current"
        expected = [
            "v5e_sleeve_level_risk_release_summary.json",
            "v5e_sleeve_level_risk_release_report.md",
            "v5e_sleeve_level_rule_boundary.csv",
            "v5e_sleeve_level_candidate_direction_matrix.csv",
            "v5e_sleeve_level_trigger_visibility.csv",
            "v5e_sleeve_level_cash_policy_interaction.csv",
            "v5e_sleeve_level_v57f_boundary.csv",
            "v5e_sleeve_level_v5c_erc_conflict_matrix.csv",
            "v5e_sleeve_level_v5d_boundary.csv",
            "v5e_sleeve_level_data_gate.csv",
            "v5e_sleeve_level_blocked_actions.csv",
            "v5e_sleeve_level_pm_admission_decision.csv",
            "v5e_sleeve_level_next_quant_spec_queue.csv",
            "v5e_sleeve_level_blockers.csv",
            "v5e_sleeve_level_next_prompt.md",
            "v5e_sleeve_level_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_sleeve_level_candidate_direction_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            directions = list(csv.DictReader(f))
        admitted = [row for row in directions if row["pm_status"] == "admit_to_quant_spec_boundary"]
        self.assertEqual({row["direction_id"] for row in admitted}, {
            "sleeve_level_daily_profit_lock",
            "sleeve_level_trailing_risk_release",
        })
        self.assertTrue(all(row["uses_intraday_trigger"] == "False" for row in directions))
        self.assertTrue(all(row["reentry_allowed"] == "False" for row in directions))

        with (out / "v5e_sleeve_level_blocked_actions.csv").open("r", encoding="utf-8-sig", newline="") as f:
            blocked = {row["action"] for row in csv.DictReader(f)}
        self.assertIn("single_name_reentry_before_next_rebalance", blocked)
        self.assertIn("same_sleeve_replacement_stock_buy", blocked)
        self.assertIn("use_5min_intraday_trigger", blocked)


if __name__ == "__main__":
    unittest.main()
