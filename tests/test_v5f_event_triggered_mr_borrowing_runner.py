from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_event_triggered_mr_borrowing_runner import (
    run_v5f_event_triggered_mr_borrowing,
)


class V5fEventTriggeredMrBorrowingRunnerTest(unittest.TestCase):
    def test_runner_keeps_mean_reversion_event_triggered_and_same_sleeve(self) -> None:
        summary = run_v5f_event_triggered_mr_borrowing(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_event_triggered_mean_reversion_borrowing_test")
        self.assertEqual(
            summary["pm_gate_decision"],
            "event_triggered_borrowing_positive_needs_independent_validation_not_candidate",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertIn(summary["best_policy"], {"paired_drop_spike_net0", "spike_only_strict"})
        self.assertEqual(summary["best_horizon"], "next2")
        self.assertGreater(summary["best_delta_return_pct_points_vs_champion"], 0.0)
        self.assertGreater(summary["best_delta_return_pct_points_vs_v57f"], 0.0)
        self.assertGreater(summary["best_strict_spike_delta_vs_champion"], 0.0)
        self.assertLessEqual(summary["best_pro_rata_delta_vs_champion"], 0.01)
        self.assertGreater(summary["event_group_count"], 0)
        self.assertGreater(summary["trade_group_count"], 0)
        self.assertTrue(summary["no_fixed_mean_reversion_budget"])
        self.assertEqual(summary["full_5min_coverage_rate_pct"], 100.0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_event_triggered_mean_reversion_borrowing_test") / "current"
        for name in [
            "v5f_mr_borrowing_summary.json",
            "v5f_mr_borrowing_report.md",
            "v5f_mr_borrowing_rule_spec.csv",
            "v5f_mr_borrowing_event_log.csv",
            "v5f_mr_borrowing_trade_log.csv",
            "v5f_mr_borrowing_daily_returns.csv",
            "v5f_mr_borrowing_variant_metrics.csv",
            "v5f_mr_borrowing_yearly.csv",
            "v5f_mr_borrowing_funding_policy_comparison.csv",
            "v5f_mr_borrowing_sleeve_attribution.csv",
            "v5f_mr_borrowing_source_audit.csv",
            "v5f_mr_borrowing_governance_audit.csv",
            "v5f_mr_borrowing_pm_gate_decision.csv",
            "v5f_mr_borrowing_next_agent_queue.csv",
            "v5f_mr_borrowing_blockers.csv",
            "v5f_mr_borrowing_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_mr_borrowing_variant_metrics.csv").open("r", encoding="utf-8-sig", newline="") as f:
            metrics = {row["version_id"]: row for row in csv.DictReader(f)}
        self.assertIn("vmr_70_30_0_champion", metrics)
        self.assertIn("v57f_startup_preload_repaired_baseline", metrics)
        self.assertIn("mr_borrow_spike_only_strict_cap10_next2", metrics)
        self.assertIn("mr_borrow_pro_rata_non_drop_cap10_next2", metrics)
        self.assertGreater(
            float(metrics["mr_borrow_spike_only_strict_cap10_next2"]["delta_return_pct_points_vs_champion"]),
            0.0,
        )
        self.assertLess(
            float(metrics["mr_borrow_pro_rata_non_drop_cap10_next2"]["delta_return_pct_points_vs_champion"]),
            0.0,
        )
        self.assertEqual(metrics["mr_borrow_spike_only_strict_cap10_next2"]["fixed_budget_reserved"], "False")
        self.assertEqual(metrics["mr_borrow_spike_only_strict_cap10_next2"]["accepted"], "False")

        with (out / "v5f_mr_borrowing_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = {row["audit_id"]: row for row in csv.DictReader(f)}
        for audit_id in [
            "full_5min_coverage_100pct",
            "no_fixed_mean_reversion_budget",
            "same_sleeve_only",
            "no_v57f_core_modified",
            "no_full_market_selection",
            "no_new_buy_signal",
            "threshold_scan_used_false",
            "accepted_false",
        ]:
            self.assertEqual(governance[audit_id]["status"], "pass", audit_id)
        self.assertEqual(governance["independent_oos_missing"]["status"], "review")


if __name__ == "__main__":
    unittest.main()
