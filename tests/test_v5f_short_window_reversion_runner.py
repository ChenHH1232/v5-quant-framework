from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_short_window_reversion_runner import run_v5f_short_window_reversion


class V5fShortWindowReversionRunnerTest(unittest.TestCase):
    def test_runner_tests_short_window_reversion_without_acceptance(self) -> None:
        summary = run_v5f_short_window_reversion(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_short_window_reversion_diagnostic")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertEqual(summary["observation_count"], 33984)
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "short_window_reversion_positive_ready_for_pm_quant_review_not_accepted",
                "short_window_reversion_diagnostic_positive_but_not_portfolio_material",
                "short_window_reversion_diagnostic_only_no_material_edge",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_short_window_reversion_diagnostic") / "current"
        for name in [
            "v5f_short_window_reversion_summary.json",
            "v5f_short_window_reversion_report.md",
            "v5f_short_window_reversion_event_definitions.csv",
            "v5f_short_window_reversion_intraday_diagnostics.csv",
            "v5f_short_window_reversion_daily_1_2d_diagnostics.csv",
            "v5f_short_window_reversion_event_by_year.csv",
            "v5f_short_window_reversion_event_by_sleeve.csv",
            "v5f_short_window_reversion_micro_overlay_estimate.csv",
            "v5f_short_window_reversion_governance_audit.csv",
            "v5f_short_window_reversion_pm_decision.csv",
            "v5f_short_window_reversion_next_queue.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_short_window_reversion_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_short_window_reversion_micro_overlay_estimate.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = {row["event_type"] for row in csv.DictReader(f)}
        for event_type in [
            "morning_30m_micro_crash",
            "late_day_vwap_dislocation",
            "pool_crash_dislocation",
            "sector_rotation_outflow",
            "daily_1d_extreme_drop",
            "daily_2d_extreme_drop",
        ]:
            self.assertIn(event_type, rows)


if __name__ == "__main__":
    unittest.main()
