from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_spike_mr_prebacktest_to_backtest_jq_sim_runner import (
    run_v5f_spike_mr_prebacktest_to_backtest_jq_sim,
)


class V5fSpikeMrPrebacktestToBacktestJqSimRunnerTest(unittest.TestCase):
    def test_runner_excludes_forward_and_keeps_shock_borrowing_observation_only(self) -> None:
        summary = run_v5f_spike_mr_prebacktest_to_backtest_jq_sim(Path("."))

        self.assertEqual(summary["status"], "completed_prebacktest_validation_and_backtest_scope_local_jq_sim")
        self.assertEqual(
            summary["pm_gate_decision"],
            "backtest_positive_prebacktest_limited_keep_observation_not_candidate",
        )
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertTrue(summary["post_20260531_forward_excluded"])
        self.assertTrue(summary["daily_forward_automation_revoked"])
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline"], "v57f_startup_preload_repaired_baseline")
        self.assertTrue(summary["pretest_directional_support"])
        self.assertFalse(summary["pretest_formal_independent_pass"])
        self.assertGreater(summary["backtest_delta_vs_primary_pct_points"], 0.0)
        self.assertGreater(summary["backtest_delta_vs_v57f_pct_points"], 0.0)
        self.assertTrue(summary["sleeve_specific_thresholds_required"])
        self.assertFalse(summary["candidate_promoted"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertTrue(summary["local_joinquant_style_simulation_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_spike_mr_prebacktest_to_backtest_jq_sim") / "current"
        for name in [
            "v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json",
            "v5f_spike_mr_prebacktest_to_backtest_jq_sim_report.md",
            "v5f_spike_mr_input_manifest.csv",
            "v5f_spike_mr_prebacktest_validation_matrix.csv",
            "v5f_spike_mr_backtest_local_jq_sim_comparison.csv",
            "v5f_spike_mr_sleeve_sensitivity_matrix.csv",
            "v5f_spike_mr_yearly_backtest_comparison.csv",
            "v5f_spike_mr_scope_governance_audit.csv",
            "v5f_spike_mr_pm_gate_decision.csv",
            "v5f_spike_mr_next_queue.csv",
            "v5f_spike_mr_blockers.csv",
            "v5f_spike_mr_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_spike_mr_backtest_local_jq_sim_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            comparison = {row["role"]: row for row in csv.DictReader(f)}
        self.assertIn("baseline", comparison)
        self.assertIn("primary_v5f_line", comparison)
        self.assertIn("governance_preferred_shock_borrowing", comparison)
        self.assertGreater(
            float(comparison["governance_preferred_shock_borrowing"]["delta_return_pct_points_vs_primary"]),
            0.0,
        )

        with (out / "v5f_spike_mr_scope_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = {row["audit_id"]: row for row in csv.DictReader(f)}
        for audit_id in [
            "daily_forward_automation_revoked",
            "backtest_scope_end_20260531",
            "prebacktest_validation_before_backtest",
            "local_joinquant_style_backtest_used",
            "sleeve_specific_thresholds_required",
            "no_candidate_promotion",
            "accepted_false",
        ]:
            self.assertEqual(governance[audit_id]["status"], "pass", audit_id)


if __name__ == "__main__":
    unittest.main()
