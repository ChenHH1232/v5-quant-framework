from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_forward_continuation_v5g01_closeout_runner import (
    run_v5f_forward_continuation_v5g01_closeout,
)


class V5fForwardContinuationV5g01CloseoutRunnerTest(unittest.TestCase):
    def test_runner_continues_primary_and_seals_v5g01_secondary(self) -> None:
        summary = run_v5f_forward_continuation_v5g01_closeout(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_forward_continuation_v5g01_closeout")
        self.assertEqual(
            summary["pm_gate_decision"],
            "continue_internal_subsleeve_forward_paper_tracking_v5g01_sealed_secondary",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["secondary_candidate"], "v5g_01_state_gated_internal_subsleeve_70_30")
        self.assertGreater(summary["primary_delta_return_pct_points_vs_repaired_baseline"], 10.0)
        self.assertGreater(summary["secondary_delta_return_pct_points_vs_repaired_baseline"], 10.0)
        self.assertLess(summary["secondary_delta_return_pct_points_vs_primary"], 0.0)
        self.assertEqual(summary["target_population_status"], "not_populated_waiting_next_clean_official_repaired_v57f_targets")
        self.assertEqual(summary["v5g01_closeout_status"], "sealed_secondary_observation_not_primary")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_forward_continuation_v5g01_closeout") / "current"
        expected = [
            "v5f_forward_continuation_summary.json",
            "v5f_forward_continuation_report.md",
            "v5f_forward_tracking_status_update.csv",
            "v5f_clean_forward_target_audit.csv",
            "v5f_paper_target_population_queue.csv",
            "v5g01_secondary_observation_closeout.csv",
            "v5f_v5g_model_priority_matrix.csv",
            "v5f_forward_continuation_governance_audit.csv",
            "v5f_forward_continuation_pm_gate_decision.csv",
            "v5f_forward_continuation_next_agent_queue.csv",
            "v5f_forward_continuation_blockers.csv",
            "v5f_forward_continuation_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_clean_forward_target_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            target_audit = {row["source_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(target_audit["late_shadow_signal_20260701"]["audit_status"], "reference_only_not_clean_forward")
        self.assertEqual(target_audit["late_shadow_signal_20260701"]["use_for_paper_population_now"], "False")
        self.assertEqual(target_audit["paper_input_preflight_20261008"]["audit_status"], "forward_only_pending")
        self.assertEqual(target_audit["paper_input_preflight_20261008"]["historical_backtest_blocker"], "False")

        with (out / "v5g01_secondary_observation_closeout.csv").open("r", encoding="utf-8-sig", newline="") as f:
            secondary = list(csv.DictReader(f))[0]
        self.assertEqual(secondary["closeout_status"], "sealed_secondary_observation_not_primary")
        self.assertEqual(secondary["beats_primary"], "False")
        self.assertEqual(secondary["accepted"], "False")

        with (out / "v5f_forward_continuation_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in governance))


if __name__ == "__main__":
    unittest.main()
