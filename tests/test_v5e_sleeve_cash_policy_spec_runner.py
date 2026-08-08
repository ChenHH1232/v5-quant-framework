from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_sleeve_cash_policy_spec_runner import run_v5e_sleeve_cash_policy_spec


class V5eSleeveCashPolicySpecRunnerTest(unittest.TestCase):
    def test_runner_generates_spec_without_backtest_or_reentry(self) -> None:
        root = Path(".")
        summary = run_v5e_sleeve_cash_policy_spec(root)

        self.assertEqual(summary["status"], "completed_sleeve_cash_policy_quant_spec")
        self.assertEqual(summary["pm_admission_decision"], "admit_sleeve_cash_bucket_accounting_to_limited_engineering")
        self.assertGreater(summary["cash_drag_delta_vs_baseline"], 0)
        self.assertFalse(summary["engineering_backtest_run"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_profit_lock_threshold_added"])
        self.assertFalse(summary["reentry_allowed"])
        self.assertFalse(summary["cross_sleeve_transfer_allowed"])
        self.assertFalse(summary["cash_proxy_asset_selected"])
        self.assertFalse(summary["accepted"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_sleeve_cash_policy_quant_spec" / "current"
        expected = [
            "v5e_sleeve_cash_policy_summary.json",
            "v5e_sleeve_cash_policy_report.md",
            "v5e_sleeve_cash_policy_rule_spec.csv",
            "v5e_sleeve_cash_bucket_schema.csv",
            "v5e_sleeve_cash_restore_rule_matrix.csv",
            "v5e_sleeve_cash_event_lifecycle.csv",
            "v5e_sleeve_cash_policy_comparison.csv",
            "v5e_cash_proxy_asset_data_gate.csv",
            "v5e_sleeve_cash_v5c_erc_boundary.csv",
            "v5e_sleeve_cash_v5d_execution_boundary.csv",
            "v5e_sleeve_cash_blocked_actions.csv",
            "v5e_sleeve_cash_pm_admission_decision.csv",
            "v5e_sleeve_cash_next_engineering_queue.csv",
            "v5e_sleeve_cash_blockers.csv",
            "v5e_sleeve_cash_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_sleeve_cash_policy_rule_spec.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rule = list(csv.DictReader(f))[0]
        self.assertEqual(rule["rule_id"], "sleeve_cash_bucket_accounting")
        self.assertEqual(rule["reentry_allowed"], "False")
        self.assertEqual(rule["cross_sleeve_transfer_allowed"], "False")
        self.assertEqual(rule["proxy_asset_allowed"], "False")

        with (out / "v5e_sleeve_cash_blocked_actions.csv").open("r", encoding="utf-8-sig", newline="") as f:
            blocked = {row["action"] for row in csv.DictReader(f)}
        self.assertIn("reentry_before_next_rebalance", blocked)
        self.assertIn("same_sleeve_replacement_stock_buy", blocked)
        self.assertIn("cash_proxy_asset_without_data_gate_and_user_approval", blocked)


if __name__ == "__main__":
    unittest.main()
