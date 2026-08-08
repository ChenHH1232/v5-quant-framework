from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_spike_funded_mr_borrowing_independent_validation_runner import (
    run_v5f_spike_funded_mr_borrowing_independent_validation_gate,
)


class V5fSpikeFundedMrBorrowingIndependentValidationRunnerTest(unittest.TestCase):
    def test_runner_builds_limited_pre2021_validation_without_promoting_rule(self) -> None:
        summary = run_v5f_spike_funded_mr_borrowing_independent_validation_gate(
            Path("."),
            allow_baostock_fetch=False,
        )

        self.assertEqual(
            summary["status"],
            "completed_v5f_spike_funded_mr_borrowing_independent_validation_gate",
        )
        self.assertEqual(
            summary["pm_gate_decision"],
            "limited_2020q4_positive_keep_forward_validation_not_candidate",
        )
        self.assertEqual(summary["validation_window_start"], "2020-10-09")
        self.assertEqual(summary["validation_window_end"], "2020-12-31")
        self.assertEqual(
            summary["validation_window_classification"],
            "pre2021_limited_independent_micro_validation_not_full_v57f_equivalent",
        )
        self.assertFalse(summary["independent_validation_pass"])
        self.assertTrue(summary["limited_2020q4_directional_pass"])
        self.assertFalse(summary["formal_promotion_allowed"])
        self.assertEqual(summary["candidate_count"], 28)
        self.assertGreaterEqual(summary["feature_row_count"], 1000)
        self.assertGreater(summary["event_group_count"], 0)
        self.assertGreater(summary["trade_group_count"], 0)
        self.assertIn(summary["best_policy"], {"paired_drop_spike_net0", "spike_only_strict"})
        self.assertEqual(summary["best_horizon"], "next2")
        self.assertGreater(summary["best_net_incremental_return_pct_points"], 0.0)
        self.assertGreaterEqual(summary["best_win_rate"], 0.5)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreaterEqual(summary["validation_gap_count"], 1)

        out = Path("v5f_spike_funded_mr_borrowing_independent_validation_gate") / "current"
        for name in [
            "v5f_spike_mr_validation_summary.json",
            "v5f_spike_mr_validation_report.md",
            "v5f_spike_mr_validation_source_audit.csv",
            "v5f_spike_mr_validation_2020q4_fetch_log.csv",
            "v5f_spike_mr_validation_feature_panel.csv",
            "v5f_spike_mr_validation_event_log.csv",
            "v5f_spike_mr_validation_trade_log.csv",
            "v5f_spike_mr_validation_metrics.csv",
            "v5f_spike_mr_validation_funding_policy_comparison.csv",
            "v5f_spike_mr_validation_sleeve_stability.csv",
            "v5f_spike_mr_validation_governance_audit.csv",
            "v5f_spike_mr_validation_gap_register.csv",
            "v5f_spike_mr_validation_pm_gate_decision.csv",
            "v5f_spike_mr_validation_next_agent_queue.csv",
            "v5f_spike_mr_validation_blockers.csv",
            "v5f_spike_mr_validation_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_spike_mr_validation_metrics.csv").open("r", encoding="utf-8-sig", newline="") as f:
            metrics = {row["version_id"]: row for row in csv.DictReader(f)}
        best_key = "independent2020q4_paired_drop_spike_net0_cap10_next2"
        self.assertIn(best_key, metrics)
        self.assertGreater(float(metrics[best_key]["net_incremental_return_pct_points"]), 0.0)
        self.assertEqual(metrics[best_key]["fixed_budget_reserved"], "False")
        self.assertEqual(metrics[best_key]["same_sleeve_only"], "True")
        self.assertEqual(metrics[best_key]["formal_independent_pass"], "False")
        self.assertEqual(metrics[best_key]["accepted"], "False")

        with (out / "v5f_spike_mr_validation_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = {row["audit_id"]: row for row in csv.DictReader(f)}
        for audit_id in [
            "backtest_scope_not_used_as_oos",
            "validation_window_pre2021",
            "minute_fetch_coverage",
            "feature_panel_nonempty",
            "metrics_nonempty",
            "fixed_abs_threshold_no_training",
            "same_sleeve_only",
            "no_fixed_mean_reversion_budget",
            "no_full_market_selection",
            "no_new_buy_signal",
            "no_v57f_core_modified",
            "accepted_false",
        ]:
            self.assertEqual(governance[audit_id]["status"], "pass", audit_id)

        with (out / "v5f_spike_mr_validation_gap_register.csv").open("r", encoding="utf-8-sig", newline="") as f:
            gaps = {row["gap_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(gaps["pre2020_5min_not_confirmed"]["blocks_formal_promotion"], "True")
        self.assertEqual(gaps["pre2021_preview_not_full_v57f_equivalent"]["blocks_formal_promotion"], "True")


if __name__ == "__main__":
    unittest.main()
