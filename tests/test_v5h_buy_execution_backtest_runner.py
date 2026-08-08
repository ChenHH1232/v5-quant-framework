from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_buy_execution_backtest_runner import run_v5h_buy_execution_backtest


class V5hBuyExecutionBacktestRunnerTest(unittest.TestCase):
    def test_runner_backtests_v5h_buy_execution_without_mainline_or_sell_change(self) -> None:
        summary = run_v5h_buy_execution_backtest(Path("."))

        self.assertEqual(summary["status"], "completed_v5h_buy_execution_backtest")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertEqual(summary["primary_backtest_variant"], "v5h_spec_v1_on_v5f_champion")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "v5h_buy_execution_v1_backtest_positive_ready_for_paper_observation_not_accepted",
                "v5h_buy_execution_v1_backtest_diagnostic_only_no_nav_edge",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["sell_rules_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["v5f_champion_buy_order_count"], 0)

        out = Path("v5h_buy_execution_backtest") / "current"
        for name in [
            "v5h_buy_execution_backtest_summary.json",
            "v5h_buy_execution_backtest_report.md",
            "v5h_buy_execution_backtest_daily_nav.csv",
            "v5h_buy_execution_backtest_execution_adjustment_by_date.csv",
            "v5h_buy_execution_backtest_variant_metrics.csv",
            "v5h_buy_execution_backtest_yearly.csv",
            "v5h_buy_execution_backtest_drawdown.csv",
            "v5h_buy_execution_backtest_family_attribution.csv",
            "v5h_buy_execution_backtest_sleeve_attribution.csv",
            "v5h_buy_execution_backtest_order_health.csv",
            "v5h_buy_execution_backtest_data_gate.csv",
            "v5h_buy_execution_backtest_governance_audit.csv",
            "v5h_buy_execution_backtest_pm_gate_decision.csv",
            "v5h_buy_execution_backtest_next_agent_queue.csv",
            "v5h_buy_execution_backtest_blockers.csv",
            "v5h_buy_execution_backtest_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_buy_execution_backtest_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            governance = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5h_buy_execution_backtest_variant_metrics.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            metrics = list(csv.DictReader(handle))
        primary = next(row for row in metrics if row["version_id"] == "v5h_spec_v1_on_v5f_champion")
        diagnostic = next(row for row in metrics if row["version_id"] == "v5h_spec_v1_all_scheduled_diagnostic")
        self.assertEqual(primary["nav_comparable"], "True")
        self.assertEqual(diagnostic["nav_comparable"], "False")
        self.assertEqual(primary["accepted"], "False")

        with (out / "v5h_buy_execution_backtest_pm_gate_decision.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            decision = list(csv.DictReader(handle))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["sell_rules_modified"], "False")
        self.assertEqual(decision["new_buy_signal_used"], "False")


if __name__ == "__main__":
    unittest.main()
