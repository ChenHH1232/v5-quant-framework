from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_prejq_local_closeout_runner import run_v5f_prejq_local_closeout


class V5fPreJqLocalCloseoutRunnerTest(unittest.TestCase):
    def test_runner_closes_out_local_work_and_waits_external_inputs(self) -> None:
        summary = run_v5f_prejq_local_closeout(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_prejq_local_closeout")
        self.assertEqual(summary["pm_gate_decision"], "prejq_local_closeout_complete_wait_external_inputs")
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertGreater(summary["v5f_delta_return_pct_points_vs_repaired_baseline"], 10.0)
        self.assertLessEqual(summary["v5f_delta_drawdown_pct_points_vs_repaired_baseline"], 0.0)
        self.assertTrue(summary["v5c_state_tags_ready"])
        self.assertFalse(summary["clean_forward_target_ready"])
        self.assertFalse(summary["joinquant_exports_ready"])
        self.assertEqual(summary["external_input_count"], 7)
        self.assertEqual(summary["waiting_external_input_count"], 7)
        self.assertFalse(summary["local_work_remaining_without_external_inputs"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_prejq_local_closeout") / "current"
        expected = [
            "v5f_prejq_local_closeout_summary.json",
            "v5f_prejq_local_closeout_report.md",
            "v5f_prejq_local_closeout_input_manifest.csv",
            "v5f_prejq_component_status_matrix.csv",
            "v5f_prejq_external_input_matrix.csv",
            "v5f_prejq_model_decision_matrix.csv",
            "v5f_prejq_allowed_blocked_actions.csv",
            "v5f_prejq_governance_audit.csv",
            "v5f_prejq_pm_gate_decision.csv",
            "v5f_prejq_next_agent_queue.csv",
            "v5f_prejq_local_closeout_blockers.csv",
            "v5f_prejq_next_prompt.md",
            "v5f_prejq_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_prejq_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_prejq_external_input_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            external = list(csv.DictReader(f))
        self.assertEqual(len(external), 7)
        self.assertTrue(any(row["input_id"] == "official_repaired_v57f_targets" for row in external))
        self.assertTrue(any(row["input_id"] == "H01" for row in external))
        self.assertTrue(all(row["historical_backtest_blocker"] == "False" for row in external))

        with (out / "v5f_prejq_model_decision_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            models = {row["model_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(models["internal_subsleeve_mom12_70_30"]["decision"], "keep_primary_forward_paper_candidate_not_accepted")
        self.assertEqual(models["v5c_overheat_no_new_overweight_on_v5f_mom12_70_30"]["decision"], "diagnostic_only_do_not_replace")
        self.assertEqual(models["v5g_01_state_gated_internal_subsleeve_70_30"]["decision"], "secondary_observation_do_not_replace")


if __name__ == "__main__":
    unittest.main()
