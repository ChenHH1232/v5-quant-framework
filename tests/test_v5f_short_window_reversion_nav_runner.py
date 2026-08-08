from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_short_window_reversion_nav_runner import run_v5f_short_window_reversion_nav


class V5fShortWindowReversionNavRunnerTest(unittest.TestCase):
    def test_runner_engineers_focused_short_window_nav_without_acceptance(self) -> None:
        summary = run_v5f_short_window_reversion_nav(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_short_window_reversion_nav_engineering")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "promote_short_window_reversion_to_pm_quant_review_not_accepted",
                "short_window_reversion_positive_but_needs_robustness_keep_momentum_primary",
                "short_window_reversion_nav_failed_keep_momentum_primary",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_short_window_reversion_nav_engineering") / "current"
        for name in [
            "v5f_short_window_reversion_nav_summary.json",
            "v5f_short_window_reversion_nav_report.md",
            "v5f_short_window_reversion_nav_spec.csv",
            "v5f_short_window_reversion_nav_trade_log.csv",
            "v5f_short_window_reversion_nav_funding_audit.csv",
            "v5f_short_window_reversion_nav_daily_returns.csv",
            "v5f_short_window_reversion_nav_metrics.csv",
            "v5f_short_window_reversion_nav_yearly.csv",
            "v5f_short_window_reversion_nav_sleeve_attribution.csv",
            "v5f_short_window_reversion_nav_governance_audit.csv",
            "v5f_short_window_reversion_nav_pm_decision.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_short_window_reversion_nav_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_short_window_reversion_nav_metrics.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        for version in [
            "morning30_repair_next1_same_sleeve_add10_on_momentum_champion_estimate",
            "morning30_repair_next2_same_sleeve_add10_on_momentum_champion_estimate",
            "late_vwap_repair_next1_same_sleeve_add10_on_momentum_champion_estimate",
            "combo_morning30_next2_plus_late_vwap_next1_add10_on_momentum_champion_estimate",
        ]:
            self.assertIn(version, rows)


if __name__ == "__main__":
    unittest.main()
