from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5f_1min_intraday_relative_zone_timing_runner import (
    run_v5f_1min_intraday_relative_zone_timing,
)


class V5f1minIntradayRelativeZoneTimingRunnerTest(unittest.TestCase):
    def test_runner_builds_relative_zone_timing_diagnostic_without_trading_change(self) -> None:
        summary = run_v5f_1min_intraday_relative_zone_timing(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_1min_intraday_relative_zone_timing_test")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "relative_zone_timing_diagnostic_positive_ready_for_fixed_execution_spec_not_trading",
                "relative_zone_timing_diagnostic_only_no_material_edge",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["value_momentum_zone_row_count"], 0)
        self.assertGreater(summary["mean_reversion_zone_row_count"], 0)

        out = Path("v5f_1min_intraday_relative_zone_timing_test") / "current"
        for name in [
            "v5f_1min_intraday_relative_zone_summary.json",
            "v5f_1min_intraday_relative_zone_report.md",
            "v5f_1min_zone_definition.csv",
            "v5f_1min_value_momentum_trade_intent.csv",
            "v5f_1min_value_momentum_zone_panel.csv",
            "v5f_1min_value_momentum_execution_timing_summary.csv",
            "v5f_1min_value_momentum_zone_bucket_summary.csv",
            "v5f_1min_mean_reversion_zone_panel.csv",
            "v5f_1min_mean_reversion_zone_summary.csv",
            "v5f_1min_execution_timing_candidate_matrix.csv",
            "v5f_1min_intraday_zone_pit_governance_audit.csv",
            "v5f_1min_intraday_zone_pm_gate_decision.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_1min_intraday_zone_pit_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            audit = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_1min_intraday_zone_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            decision = list(csv.DictReader(handle))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["trading_frequency_increased"], "False")


if __name__ == "__main__":
    unittest.main()
