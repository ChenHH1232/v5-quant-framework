from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_repaired_baseline_overlay_comparison_runner import run_v5f_repaired_baseline_overlay_comparison


class V5fRepairedBaselineOverlayComparisonRunnerTest(unittest.TestCase):
    def test_runner_uses_startup_repaired_baseline_without_acceptance(self) -> None:
        summary = run_v5f_repaired_baseline_overlay_comparison(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_repaired_baseline_overlay_comparison")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "repaired_baseline_mismatch_blocker",
                "diagnostic_only_no_stable_edge",
                "positive_but_needs_forward_paper",
                "promote_to_v5f_overlay_candidate_not_accepted",
                "blocked_by_pit_or_pool_boundary_issue",
            },
        )
        self.assertEqual(summary["backtest_scope_start"], "2021-05-01")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertTrue(summary["repaired_baseline_confirmed"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_repaired_baseline_overlay_comparison") / "current"
        expected = [
            "v5f_repaired_overlay_summary.json",
            "v5f_repaired_overlay_report.md",
            "v5f_repaired_baseline_truth_table.csv",
            "v5f_baseline_mismatch_audit.csv",
            "v5f_stock_pool_boundary_audit.csv",
            "v5f_pit_leakage_audit.csv",
            "v5f_momentum_repaired_result.csv",
            "v5f_mean_reversion_repaired_result.csv",
            "v5f_combined_overlay_repaired_result.csv",
            "v5f_overlay_yearly_performance.csv",
            "v5f_overlay_drawdown_attribution.csv",
            "v5f_overlay_sleeve_contribution.csv",
            "v5f_overlay_turnover_cost_health.csv",
            "v5f_overlay_order_health.csv",
            "v5f_candidate_matrix.csv",
            "v5f_pm_quant_gate_decision.csv",
            "v5f_next_agent_queue.csv",
            "v5f_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_repaired_baseline_truth_table.csv").open("r", encoding="utf-8-sig", newline="") as f:
            truth = {row["item"]: row for row in csv.DictReader(f)}
        self.assertEqual(truth["repaired_first_signal_date"]["value"], "2021-05-06")
        self.assertEqual(truth["first_rebalance_signal_csv"]["value"], "2021-05-06")

        with (out / "v5f_stock_pool_boundary_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            pool = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in pool))

        with (out / "v5f_combined_overlay_repaired_result.csv").open("r", encoding="utf-8-sig", newline="") as f:
            combined = {row["version_id"] for row in csv.DictReader(f)}
        self.assertIn("momentum_primary_only", combined)
        self.assertIn("mean_reversion_secondary_only", combined)
        self.assertIn("momentum_plus_mean_reversion_equal_blend", combined)
        self.assertIn("momentum_primary_mean_reversion_tiebreaker", combined)


if __name__ == "__main__":
    unittest.main()
