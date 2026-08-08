from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_daily_momentum_diagnostic_runner import run_v5e_daily_momentum_diagnostic


class V5eDailyMomentumDiagnosticRunnerTest(unittest.TestCase):
    def test_runner_completes_daily_momentum_diagnostic_without_acceptance(self) -> None:
        summary = run_v5e_daily_momentum_diagnostic(Path("."))

        self.assertEqual(summary["status"], "completed_v5e_daily_momentum_diagnostic_addendum")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "diagnostic_only_no_trading_value",
                "diagnostic_positive_but_nav_failed",
                "diagnostic_positive_ready_for_separate_quant_spec_not_accepted",
            },
        )
        self.assertEqual(summary["research_pool"], "v57f_v5e_existing_value_dividend_lowvol_sleeve_pool_only")
        self.assertEqual(summary["backtest_scope_start"], "2021-05-01")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertGreater(summary["held_stock_day_count"], 0)
        self.assertGreater(summary["feature_event_count"], 0)
        self.assertFalse(summary["nav_level_effective"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_replacement"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_daily_momentum_diagnostic_addendum") / "current"
        expected = [
            "v5e_daily_momentum_summary.json",
            "v5e_daily_momentum_report.md",
            "v5e_daily_momentum_theory_check.csv",
            "v5e_daily_momentum_feature_schema.csv",
            "v5e_daily_momentum_pit_audit.csv",
            "v5e_daily_momentum_governance_audit.csv",
            "v5e_daily_held_stock_momentum_features.csv",
            "v5e_daily_momentum_forward_return_diagnostics.csv",
            "v5e_daily_momentum_bucket_result.csv",
            "v5e_daily_momentum_v5e_trigger_overlay.csv",
            "v5e_daily_momentum_nav_proxy_comparison.csv",
            "v5e_daily_momentum_pm_gate_decision.csv",
            "v5e_daily_momentum_next_agent_queue.csv",
            "v5e_daily_momentum_blockers.csv",
            "v5e_daily_momentum_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_daily_momentum_theory_check.csv").open("r", encoding="utf-8-sig", newline="") as f:
            theory = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in theory))

        with (out / "v5e_daily_momentum_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")
        self.assertEqual(decision["v57f_replacement"], "False")
        self.assertEqual(decision["v57f_core_modified"], "False")
        self.assertEqual(decision["threshold_scan_used"], "False")
        self.assertEqual(decision["new_buy_signal"], "False")

        with (out / "v5e_daily_momentum_nav_proxy_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            nav = {row["version_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(nav["daily_momentum_trigger_event_diagnostic_proxy"]["nav_level_valid"], "False")
        self.assertEqual(nav["daily_momentum_trigger_event_diagnostic_proxy"]["accepted"], "False")


if __name__ == "__main__":
    unittest.main()
