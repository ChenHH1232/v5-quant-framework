from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_quiet_or_active_independent_validation_runner import (
    run_v5h_quiet_or_active_independent_validation,
)


class V5hQuietOrActiveIndependentValidationRunnerTest(unittest.TestCase):
    def test_runner_validates_quiet_or_active_without_mainline_changes(self) -> None:
        summary = run_v5h_quiet_or_active_independent_validation(Path("."))

        self.assertEqual(summary["status"], "completed_quiet_or_active_independent_validation")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "quiet_or_active_limited_independent_positive_low_power_not_accepted",
                "quiet_or_active_independent_validation_low_power_no_confirmation",
                "quiet_or_active_independent_validation_positive_ready_for_forward_observation",
                "quiet_or_active_independent_validation_does_not_confirm",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["sell_rules_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["primary_scope_order_count"], 0)

        out = Path("v5h_quiet_or_active_independent_validation") / "current"
        for name in [
            "v5h_quiet_or_active_independent_summary.json",
            "v5h_quiet_or_active_independent_report.md",
            "v5h_quiet_or_active_independent_order_panel.csv",
            "v5h_quiet_or_active_independent_read_audit.csv",
            "v5h_quiet_or_active_independent_segment_result.csv",
            "v5h_quiet_or_active_independent_scope_metrics.csv",
            "v5h_quiet_or_active_independent_variant_metrics.csv",
            "v5h_quiet_or_active_independent_data_gate.csv",
            "v5h_quiet_or_active_independent_governance_audit.csv",
            "v5h_quiet_or_active_independent_pm_gate_decision.csv",
            "v5h_quiet_or_active_independent_next_queue.csv",
            "v5h_quiet_or_active_independent_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_quiet_or_active_independent_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            governance = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5h_quiet_or_active_independent_variant_metrics.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            metrics = list(csv.DictReader(handle))
        self.assertTrue(any(row["version_id"] == "pre2021_liquidity_quiet_or_active_gate" for row in metrics))
        self.assertTrue(all(row["accepted"] == "False" for row in metrics))


if __name__ == "__main__":
    unittest.main()
