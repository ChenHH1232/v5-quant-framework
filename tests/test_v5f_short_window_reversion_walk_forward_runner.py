from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_short_window_reversion_walk_forward_runner import (
    run_v5f_short_window_reversion_walk_forward,
)


class V5fShortWindowReversionWalkForwardRunnerTest(unittest.TestCase):
    def test_runner_builds_prior_year_sleeve_threshold_packet(self) -> None:
        summary = run_v5f_short_window_reversion_walk_forward(Path("."), probe_baostock=False)

        self.assertEqual(summary["status"], "completed_v5f_short_window_backtest_scope_internal_rolling_diagnostic")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertEqual(summary["backtest_scope_classification"], "historical_backtest_in_sample_engineering_window")
        self.assertFalse(summary["oos_validation_used"])
        self.assertFalse(summary["rolling_validation_used"])
        self.assertTrue(summary["internal_rolling_diagnostic_used"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["threshold_source"], "prior_years_by_sleeve_only")
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_short_window_reversion_walk_forward_robustness") / "current"
        for name in [
            "v5f_walk_forward_summary.json",
            "v5f_walk_forward_report.md",
            "v5f_walk_forward_data_source_audit.csv",
            "v5f_pre2021_v4_source_audit.csv",
            "v5f_pre2021_5min_fetch_feasibility.csv",
            "v5f_sleeve_specific_thresholds.csv",
            "v5f_walk_forward_event_log.csv",
            "v5f_walk_forward_trade_log.csv",
            "v5f_walk_forward_nav_metrics.csv",
            "v5f_walk_forward_yearly.csv",
            "v5f_walk_forward_governance_audit.csv",
            "v5f_walk_forward_pm_decision.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_sleeve_specific_thresholds.csv").open("r", encoding="utf-8-sig", newline="") as f:
            thresholds = list(csv.DictReader(f))
        self.assertTrue(thresholds)
        self.assertTrue(all(row["threshold_source"] == "prior_years_same_sleeve_only" for row in thresholds))
        self.assertTrue(all(row["used_future_test_year_data"] == "False" for row in thresholds))

        with (out / "v5f_walk_forward_pit_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))


if __name__ == "__main__":
    unittest.main()
