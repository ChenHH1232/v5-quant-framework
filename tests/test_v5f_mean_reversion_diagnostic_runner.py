from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_mean_reversion_diagnostic_runner import run_v5f_mean_reversion_diagnostic


class V5fMeanReversionDiagnosticRunnerTest(unittest.TestCase):
    def test_runner_completes_without_acceptance_or_new_stock_selection(self) -> None:
        summary = run_v5f_mean_reversion_diagnostic(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_mean_reversion_diagnostic")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "mean_reversion_positive_admit_to_pm_quant_review_not_accepted",
                "mean_reversion_positive_but_drawdown_note_diagnostic_only",
                "mean_reversion_event_signal_only_nav_failed",
            },
        )
        self.assertEqual(summary["backtest_scope_start"], "2021-05-01")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_mean_reversion_diagnostic") / "current"
        expected = [
            "v5f_mean_reversion_summary.json",
            "v5f_mean_reversion_feature_schema.csv",
            "v5f_mean_reversion_event_forward_diagnostics.csv",
            "v5f_mean_reversion_tilt_weights.csv",
            "v5f_mean_reversion_daily_returns.csv",
            "v5f_mean_reversion_metrics.csv",
            "v5f_mean_reversion_yearly_performance.csv",
            "v5f_mean_reversion_rebalance_period_performance.csv",
            "v5f_mean_reversion_governance_audit.csv",
            "v5f_mean_reversion_pm_gate_decision.csv",
            "v5f_mean_reversion_next_queue.csv",
            "v5f_mean_reversion_blockers.csv",
            "v5f_mean_reversion_report.md",
            "v5f_mean_reversion_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_mean_reversion_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_mean_reversion_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")


if __name__ == "__main__":
    unittest.main()
