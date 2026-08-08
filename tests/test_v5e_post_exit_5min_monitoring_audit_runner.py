from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_post_exit_5min_monitoring_audit_runner import run_v5e_post_exit_5min_monitoring_audit


class V5ePostExit5minMonitoringAuditRunnerTest(unittest.TestCase):
    def test_runner_completes_monitoring_audit_and_keeps_ideal_model_diagnostic(self) -> None:
        root = Path(".")
        summary = run_v5e_post_exit_5min_monitoring_audit(root)

        self.assertEqual(summary["status"], "completed_post_exit_5min_monitoring_audit")
        self.assertEqual(summary["scope"], "medium_post_exit_to_next_rebalance")
        self.assertGreater(summary["event_count"], 0)
        self.assertEqual(summary["ideal_model_count"], 3)
        self.assertFalse(summary["trade_trigger_allowed"])
        self.assertFalse(summary["minute_data_used_for_trigger"])
        self.assertFalse(summary["full_holding_period_fetch"])
        self.assertFalse(summary["full_holding_period_5min_trigger_allowed"])
        self.assertFalse(summary["ideal_model_tradable"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_post_exit_5min_monitoring_audit_packet" / "current"
        with (out / "v5e_post_exit_5min_ideal_model_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            models = {row["model_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(models["ideal_hindsight_cash_or_continue_hold_upper_bound"]["uses_future_information"], "True")
        self.assertEqual(models["ideal_hindsight_cash_or_continue_hold_upper_bound"]["trade_trigger_allowed"], "False")
        self.assertEqual(models["actual_v5e_hold_cash_until_next_rebalance"]["uses_future_information"], "False")

        with (out / "v5e_post_exit_5min_missing_data_reason.csv").open("r", encoding="utf-8-sig", newline="") as f:
            missing_rows = list(csv.DictReader(f))
        self.assertTrue(all(row["can_use_daily_to_fabricate_5min"] == "False" for row in missing_rows))


if __name__ == "__main__":
    unittest.main()
