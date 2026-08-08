from __future__ import annotations

import csv
import unittest
from pathlib import Path

import v5.v5f_joinquant_now_execution_runner as runner


class V5fJoinQuantNowExecutionRunnerTest(unittest.TestCase):
    def test_runner_records_baostock_only_5min_source_without_promoting_model(self) -> None:
        original_auth = runner._authenticate
        original_daily = runner._daily_price_probe
        original_minute = runner._minute_permission_probe
        original_pit = runner._pit_fundamental_probe
        try:
            runner._authenticate = lambda: (object(), [{"test_id": "jqdata_auth", "status": "pass"}])
            runner._daily_price_probe = lambda jq, samples: [
                {
                    "test_id": "daily_price",
                    "code": "600036.XSHG",
                    "sleeve": "bank",
                    "test_date": "2019-12-31",
                    "status": "pass",
                    "row_count": 2,
                }
            ]
            runner._minute_permission_probe = lambda jq, samples: [
                {
                    "test_id": "pre2020_get_price_5m",
                    "code": "600036.XSHG",
                    "sleeve": "bank",
                    "test_date": "2019-12-31",
                    "status": "permission_blocked",
                    "row_count": 0,
                    "error_message": "paid module",
                }
            ]
            runner._pit_fundamental_probe = lambda jq, samples: [
                {
                    "test_id": "pit_fundamentals_valuation_indicator",
                    "code": "600036.XSHG",
                    "sleeve": "bank",
                    "test_date": "2019-12-31",
                    "status": "pass",
                    "row_count": 1,
                }
            ]

            summary = runner.run_v5f_joinquant_now_execution(Path("."))
        finally:
            runner._authenticate = original_auth
            runner._daily_price_probe = original_daily
            runner._minute_permission_probe = original_minute
            runner._pit_fundamental_probe = original_pit

        self.assertEqual(summary["status"], "completed_joinquant_now_execution_probe")
        self.assertEqual(
            summary["pm_gate_decision"],
            "jqdata_daily_pit_pass_baostock_pre2020_5min_unavailable_keep_spike_mr_observation",
        )
        self.assertTrue(summary["jqdata_auth_pass"])
        self.assertTrue(summary["daily_price_access"])
        self.assertTrue(summary["pit_fundamental_access"])
        self.assertFalse(summary["minute_5m_access"])
        self.assertEqual(summary["project_5min_source_policy"], "baostock_only")
        self.assertEqual(summary["local_5min_bar_source_policy"], "baostock_only")
        self.assertTrue(summary["joinquant_platform_minute_backtest_allowed"])
        self.assertFalse(summary["joinquant_minute_path_allowed"])
        self.assertFalse(summary["joinquant_minute_bar_data_source_allowed"])
        self.assertFalse(summary["joinquant_minute_permission_required"])
        self.assertFalse(summary["baostock_pre2020_5min_available"])
        self.assertTrue(summary["backtest_scope_5min_baostock_available"])
        self.assertFalse(summary["pre2020_5min_available"])
        self.assertFalse(summary["backtest_scope_5min_jqdata_available"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["backtest_end"], "2026-05-31")

        out = Path("v5f_joinquant_now_execution") / "current"
        for name in [
            "v5f_joinquant_now_execution_summary.json",
            "v5f_joinquant_now_execution_report.md",
            "v5f_jqdata_capability_matrix.csv",
            "v5f_pre2020_daily_price_probe.csv",
            "v5f_pre2020_minute_permission_probe.csv",
            "v5f_pre2020_pit_fundamental_probe.csv",
            "v5f_joinquant_required_test_status.csv",
            "v5f_joinquant_platform_export_status.csv",
            "v5f_joinquant_governance_audit.csv",
            "v5f_joinquant_pm_gate_decision.csv",
            "v5f_joinquant_next_queue.csv",
            "v5f_joinquant_blockers.csv",
            "v5f_joinquant_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_joinquant_required_test_status.csv").open("r", encoding="utf-8-sig", newline="") as f:
            statuses = {row["test_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(
            statuses["T01_pre2020_5min_independent_validation"]["status"],
            "blocked_by_baostock_pre2020_5min_unavailable",
        )
        self.assertEqual(
            statuses["T04_joinquant_platform_backtest_exports"]["status"],
            "requires_joinquant_platform_ui_exports",
        )

        with (out / "v5f_joinquant_blockers.csv").open("r", encoding="utf-8-sig", newline="") as f:
            blockers = {row["blocker_id"]: row for row in csv.DictReader(f)}
        self.assertIn("baostock_pre2020_5min_unavailable", blockers)
        self.assertIn("joinquant_platform_exports_missing", blockers)

        with (out / "v5f_joinquant_next_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue_tasks = {row["next_task"]: row for row in csv.DictReader(f)}
        self.assertIn("keep_5min_source_policy_baostock_only", queue_tasks)
        self.assertIn("run_joinquant_platform_minute_backtest_and_drop_required_exports", queue_tasks)
        self.assertEqual(
            queue_tasks["do_not_use_jqdata_sdk_minute_bars_as_local_5min_source"]["allowed"],
            "False",
        )


if __name__ == "__main__":
    unittest.main()
