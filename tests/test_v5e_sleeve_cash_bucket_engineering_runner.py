from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_sleeve_cash_bucket_engineering_runner import run_v5e_sleeve_cash_bucket_engineering


class V5eSleeveCashBucketEngineeringRunnerTest(unittest.TestCase):
    def test_runner_builds_ledger_without_trade_path_changes(self) -> None:
        root = Path(".")
        summary = run_v5e_sleeve_cash_bucket_engineering(root)

        self.assertEqual(summary["status"], "completed_sleeve_cash_bucket_engineering")
        self.assertEqual(summary["pm_gate_decision"], "sleeve_cash_bucket_accounting_pass_ready_for_cash_proxy_data_gate")
        self.assertEqual(summary["ledger_event_count"], 87)
        self.assertGreater(summary["daily_balance_rows"], 0)
        self.assertEqual(summary["no_reentry_violation_count"], 0)
        self.assertEqual(summary["no_cross_sleeve_violation_count"], 0)
        self.assertEqual(summary["no_proxy_violation_count"], 0)
        self.assertFalse(summary["engineering_backtest_run"])
        self.assertFalse(summary["trade_path_changed"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_sleeve_cash_bucket_engineering" / "current"
        expected = [
            "v5e_sleeve_cash_bucket_summary.json",
            "v5e_sleeve_cash_bucket_report.md",
            "v5e_sleeve_cash_event_ledger.csv",
            "v5e_daily_sleeve_cash_balance.csv",
            "v5e_sleeve_cash_restore_event_log.csv",
            "v5e_no_reentry_audit.csv",
            "v5e_no_cross_sleeve_transfer_audit.csv",
            "v5e_no_proxy_asset_audit.csv",
            "v5e_no_trade_path_change_audit.csv",
            "v5e_cash_reconciliation_audit.csv",
            "v5e_sleeve_cash_drag_by_sleeve.csv",
            "v5e_sleeve_cash_drag_by_year.csv",
            "v5e_sleeve_cash_drag_by_rebalance_period.csv",
            "v5e_top_cash_bucket_periods.csv",
            "v5e_top_cash_drag_exit_events.csv",
            "v5e_sleeve_cash_pm_gate_decision.csv",
            "v5e_sleeve_cash_next_agent_queue.csv",
            "v5e_sleeve_cash_blockers.csv",
            "v5e_sleeve_cash_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_sleeve_cash_event_ledger.csv").open("r", encoding="utf-8-sig", newline="") as f:
            ledger = list(csv.DictReader(f))
        self.assertTrue(all(row["reentry_allowed"] == "False" for row in ledger))
        self.assertTrue(all(row["cross_sleeve_transfer_allowed"] == "False" for row in ledger))
        self.assertTrue(all(row["proxy_asset_allowed"] == "False" for row in ledger))

        with (out / "v5e_cash_reconciliation_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            reconciliation = list(csv.DictReader(f))
        self.assertEqual(reconciliation[0]["status"], "pass")

        with (out / "v5e_sleeve_cash_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            gate = list(csv.DictReader(f))[0]
        self.assertEqual(gate["no_reentry_pass"], "True")
        self.assertEqual(gate["no_cross_sleeve_pass"], "True")
        self.assertEqual(gate["no_proxy_pass"], "True")
        self.assertEqual(gate["no_trade_path_change_pass"], "True")


if __name__ == "__main__":
    unittest.main()
