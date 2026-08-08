from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5g_cross_line_model_research_startup_runner import run_v5g_cross_line_model_research_startup


class V5gCrossLineModelResearchStartupRunnerTest(unittest.TestCase):
    def test_runner_builds_five_model_startup_packet_without_backtest(self) -> None:
        summary = run_v5g_cross_line_model_research_startup(Path("."))

        self.assertEqual(summary["status"], "completed_v5g_cross_line_model_research_startup")
        self.assertEqual(
            summary["pm_gate_decision"],
            "v5g_startup_pass_five_models_ready_for_spec_and_data_gates_not_backtest",
        )
        self.assertEqual(summary["model_count"], 5)
        self.assertEqual(summary["top_priority_model"], "v5g_01_state_gated_internal_subsleeve_70_30")
        self.assertEqual(summary["primary_v5f_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertGreater(float(summary["primary_v5f_delta_return_pct_points_vs_repaired_baseline"]), 0.0)
        self.assertTrue(summary["v5c_state_gate_available"])
        self.assertTrue(summary["v5e_cash_proxy_available"])
        self.assertGreaterEqual(summary["external_knowledge_sources"], 5)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_strategy_rule_added"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5g_cross_line_model_research_startup") / "current"
        expected = [
            "v5g_cross_line_model_research_summary.json",
            "v5g_cross_line_model_research_report.md",
            "v5g_input_source_manifest.csv",
            "v5g_midterm_success_transfer_matrix.csv",
            "v5g_external_data_knowledge_inventory.csv",
            "v5g_five_new_model_specs.csv",
            "v5g_model_research_priority_matrix.csv",
            "v5g_governance_boundary_matrix.csv",
            "v5g_data_gate_requirements.csv",
            "v5g_limited_research_queue.csv",
            "v5g_pm_gate_decision.csv",
            "v5g_next_agent_queue.csv",
            "v5g_blockers.csv",
            "v5g_agent_execution_rules.md",
            "v5g_next_prompt.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5g_five_new_model_specs.csv").open("r", encoding="utf-8-sig", newline="") as f:
            specs = list(csv.DictReader(f))
        self.assertEqual(len(specs), 5)
        self.assertTrue(all(row["accepted"] == "False" for row in specs))
        self.assertIn("v5g_04_profit_lock_cash_proxy_internal_subsleeve", {row["model_id"] for row in specs})
        self.assertIn("v5g_05_short_window_reversion_confirmation_overlay", {row["model_id"] for row in specs})

        with (out / "v5g_governance_boundary_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            boundary = list(csv.DictReader(f))
        self.assertEqual(len(boundary), 5)
        self.assertTrue(all(row["v57f_core_modified_allowed"] == "False" for row in boundary))
        self.assertTrue(all(row["engineering_backtest_allowed_now"] == "False" for row in boundary))
        self.assertTrue(all(row["threshold_scan_allowed"] == "False" for row in boundary))

        with (out / "v5g_next_agent_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = list(csv.DictReader(f))
        self.assertEqual(queue[0]["next_gate"], "v5g_01_state_gated_internal_subsleeve_quant_spec")
        self.assertEqual(queue[1]["next_gate"], "v5g_02_quality_guarded_momentum_factor_validation")


if __name__ == "__main__":
    unittest.main()
