from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_profit_lock_model_comparison_runner import run_v5e_profit_lock_model_comparison


class V5eProfitLockModelComparisonRunnerTest(unittest.TestCase):
    def test_runner_reports_improvement_without_accepting_or_engineering_oracle(self) -> None:
        root = Path(".")
        summary = run_v5e_profit_lock_model_comparison(root)

        self.assertEqual(summary["status"], "completed_profit_lock_model_comparison")
        self.assertEqual(summary["pm_gate_decision"], "retain_profit_lock_main_forward_paper_tracking_not_accepted")
        self.assertGreater(summary["daily_open_delta_return_pct_points_200w"], 0)
        self.assertGreater(summary["vwap_adjusted_delta_return_pct_points_200w"], 0)
        self.assertLess(summary["delta_max_drawdown_pct_points_200w"], 0)
        self.assertGreater(summary["post_exit_net_cash_value_vs_continue_hold"], 0)
        self.assertGreater(summary["ideal_upper_bound_value_vs_cash"], 0)
        self.assertFalse(summary["ideal_model_tradable"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_profit_lock_model_comparison" / "current"
        with (out / "v5e_profit_lock_model_ladder_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["model_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(rows["ideal_hindsight_cash_or_continue_hold_upper_bound"]["tradable"], "False")
        self.assertEqual(rows["v5e_profit_lock_main_daily_open_200w"]["accepted"], "False")


if __name__ == "__main__":
    unittest.main()
