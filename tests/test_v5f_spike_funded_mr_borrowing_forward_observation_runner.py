from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_spike_funded_mr_borrowing_forward_observation_runner import (
    run_v5f_spike_funded_mr_borrowing_forward_observation,
)


class V5fSpikeFundedMrBorrowingForwardObservationRunnerTest(unittest.TestCase):
    def test_runner_keeps_spike_funded_borrowing_observe_only(self) -> None:
        summary = run_v5f_spike_funded_mr_borrowing_forward_observation(
            Path("."),
            allow_baostock_fetch=False,
        )

        self.assertEqual(summary["status"], "completed_v5f_spike_funded_mr_borrowing_forward_observation")
        self.assertEqual(summary["pm_gate_decision"], "forward_observation_initial_mixed_keep_diagnostic")
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["observation_id"], "spike_funded_mr_borrowing_observe_only")
        self.assertEqual(summary["paper_signal_packet_date"], "2026-07-19")
        self.assertEqual(summary["observation_start"], "2026-07-20")
        self.assertEqual(summary["observation_end"], "2026-07-31")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertTrue(summary["paper_only"])
        self.assertTrue(summary["forward_observation_started"])
        self.assertFalse(summary["candidate_promoted"])
        self.assertFalse(summary["independent_validation_pass"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertEqual(summary["paper_target_count"], 28)
        self.assertGreater(summary["feature_row_count"], 0)
        self.assertGreater(summary["event_group_count"], 0)
        self.assertGreater(summary["observation_trade_group_count"], 0)
        self.assertLess(summary["best_observation_net_pct_points"], 0.0)
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_spike_funded_mr_borrowing_forward_observation") / "current"
        for name in [
            "v5f_spike_mr_forward_summary.json",
            "v5f_spike_mr_forward_report.md",
            "v5f_spike_mr_forward_input_manifest.csv",
            "v5f_spike_mr_forward_candidate_status.csv",
            "v5f_spike_mr_forward_observation_schema.csv",
            "v5f_spike_mr_forward_daily_observation_template.csv",
            "v5f_spike_mr_forward_paper_target_universe.csv",
            "v5f_spike_mr_forward_thresholds.csv",
            "v5f_spike_mr_forward_fetch_log.csv",
            "v5f_spike_mr_forward_feature_panel.csv",
            "v5f_spike_mr_forward_event_log.csv",
            "v5f_spike_mr_forward_observation_trade_log.csv",
            "v5f_spike_mr_forward_daily_observation_log.csv",
            "v5f_spike_mr_forward_metrics.csv",
            "v5f_spike_mr_forward_sleeve_observation.csv",
            "v5f_spike_mr_forward_source_evidence_matrix.csv",
            "v5f_spike_mr_forward_allowed_blocked_actions.csv",
            "v5f_spike_mr_forward_governance_audit.csv",
            "v5f_spike_mr_forward_pm_gate_decision.csv",
            "v5f_spike_mr_forward_next_agent_queue.csv",
            "v5f_spike_mr_forward_blockers.csv",
            "v5f_spike_mr_forward_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_spike_mr_forward_candidate_status.csv").open("r", encoding="utf-8-sig", newline="") as f:
            status = {row["line_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(status["internal_subsleeve_mom12_70_30"]["role"], "primary_v5f_forward_paper_line")
        self.assertEqual(status["spike_funded_mr_borrowing_observe_only"]["role"], "secondary_observation_only")
        self.assertEqual(status["spike_funded_mr_borrowing_observe_only"]["candidate_promoted"], "False")

        with (out / "v5f_spike_mr_forward_metrics.csv").open("r", encoding="utf-8-sig", newline="") as f:
            metrics = {row["version_id"]: row for row in csv.DictReader(f)}
        best = "forward202607_paired_drop_spike_net0_cap10_next1"
        self.assertIn(best, metrics)
        self.assertLess(float(metrics[best]["net_incremental_return_pct_points"]), 0.0)
        self.assertEqual(metrics[best]["paper_only"], "True")
        self.assertEqual(metrics[best]["formal_candidate"], "False")
        self.assertEqual(metrics[best]["accepted"], "False")

        with (out / "v5f_spike_mr_forward_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = {row["audit_id"]: row for row in csv.DictReader(f)}
        for audit_id in [
            "primary_line_retained",
            "observation_line_not_candidate",
            "post_20260531_forward_only",
            "backtest_scope_end_unchanged",
            "paper_targets_available",
            "forward_5min_fetch_pass",
            "thresholds_pit_train_end_20251231",
            "same_sleeve_only",
            "no_fixed_mean_reversion_budget",
            "no_trade_order",
            "no_v57f_core_modified",
            "accepted_false",
            "live_trading_approved_false",
            "formal_promotion_blocked",
        ]:
            self.assertEqual(governance[audit_id]["status"], "pass", audit_id)


if __name__ == "__main__":
    unittest.main()
