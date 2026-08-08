from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_cash_policy_review_runner import run_v5e_cash_policy_review


class V5eCashPolicyReviewRunnerTest(unittest.TestCase):
    def test_runner_opens_sleeve_cash_spec_and_blocks_full_5min_trigger(self) -> None:
        root = Path(".")
        summary = run_v5e_cash_policy_review(root)

        self.assertEqual(summary["status"], "completed_cash_policy_review")
        self.assertEqual(summary["pm_gate_decision"], "open_sleeve_cash_policy_quant_spec")
        self.assertEqual(summary["secondary_gate"], "open_post_exit_5min_monitoring_data_gate")
        self.assertEqual(summary["blocked_gate"], "block_full_holding_period_5min_trigger_until_forward_evidence")
        self.assertTrue(summary["post_exit_5min_monitoring_recommended"])
        self.assertFalse(summary["full_holding_period_5min_trigger_recommended"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["engineering_backtest_run"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertGreater(summary["medium_5min_stock_dates"], 0)
        self.assertGreater(summary["full_5min_stock_dates"], summary["medium_5min_stock_dates"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_cash_policy_review" / "current"
        with (out / "v5e_cash_policy_pm_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        by_policy = {row["policy_id"]: row["pm_decision"] for row in rows}
        self.assertEqual(by_policy["hold_cash_until_next_rebalance"], "retain_as_baseline_policy")
        self.assertEqual(by_policy["sleeve_cash_policy"], "admit_to_quant_spec")
        self.assertEqual(by_policy["cash_proxy_asset_policy"], "admit_to_data_gate_only")
        self.assertEqual(by_policy["reentry_before_next_rebalance"], "blocked")


if __name__ == "__main__":
    unittest.main()
