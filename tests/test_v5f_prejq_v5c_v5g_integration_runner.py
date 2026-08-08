from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_prejq_v5c_v5g_integration_runner import run_v5f_prejq_v5c_v5g_integration


class V5fPreJqV5cV5gIntegrationRunnerTest(unittest.TestCase):
    def test_runner_integrates_v5c_tags_and_seals_v5g_without_acceptance(self) -> None:
        summary = run_v5f_prejq_v5c_v5g_integration(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_prejq_v5c_v5g_integration")
        self.assertEqual(
            summary["pm_gate_decision"],
            "prejq_v5c_v5g_integration_pass_observe_only_and_overheat_candidate_ready",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertEqual(summary["joined_stock_rebalance_rows"], 582)
        self.assertGreater(summary["any_watch_row_count"], 0)
        self.assertEqual(summary["composite_overheat_row_count"], 7)
        self.assertEqual(summary["active_overweight_on_composite_overheat_count"], 3)
        self.assertEqual(summary["composite_candidate_touched_rebalance_sleeve_count"], 1)
        self.assertEqual(summary["v5g_primary_challenge_status"], "sealed_secondary_underperforms_v5f_champion")
        self.assertTrue(summary["observe_only_forward_integration"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_prejq_v5c_v5g_integration") / "current"
        expected = [
            "v5f_prejq_v5c_v5g_integration_summary.json",
            "v5f_prejq_v5c_v5g_integration_report.md",
            "v5f_prejq_input_manifest.csv",
            "v5c_v5f_state_active_weight_audit.csv",
            "v5c_v5f_overheat_exposure_by_sleeve.csv",
            "v5c_v5f_overheat_exposure_by_period.csv",
            "v5c_v5f_state_bucket_result.csv",
            "v5c_v5f_forward_observe_only_tags.csv",
            "v5c_overheat_no_new_overweight_candidate_matrix.csv",
            "v5g_secondary_diagnostic_closeout.csv",
            "v5f_prejq_v5c_v5g_governance_audit.csv",
            "v5f_prejq_v5c_v5g_pm_gate_decision.csv",
            "v5f_prejq_v5c_v5g_next_agent_queue.csv",
            "v5f_prejq_blockers.csv",
            "v5f_prejq_v5c_v5g_next_prompt.md",
            "v5f_prejq_v5c_v5g_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_prejq_v5c_v5g_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5c_overheat_no_new_overweight_candidate_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            candidates = {row["candidate_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(
            candidates["sleeve_composite_overheat_no_new_overweight_build"]["pm_status"],
            "approved_for_next_limited_engineering_fixed_rule_not_accepted",
        )
        self.assertEqual(candidates["sleeve_composite_overheat_no_new_overweight_build"]["historical_nav_backtest_started"], "False")

        with (out / "v5g_secondary_diagnostic_closeout.csv").open("r", encoding="utf-8-sig", newline="") as f:
            v5g = {row["model_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(v5g["v5g_01_state_gated_internal_subsleeve_70_30"]["beats_v5f_champion"], "False")
        self.assertEqual(v5g["v5g_02_quality_guarded_momentum_factor_validation"]["role"], "diagnostic")


if __name__ == "__main__":
    unittest.main()
