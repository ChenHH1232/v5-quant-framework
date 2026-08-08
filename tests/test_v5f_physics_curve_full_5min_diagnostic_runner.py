from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_physics_curve_full_5min_diagnostic_runner import (
    run_v5f_physics_curve_full_5min_diagnostic,
)


class V5fPhysicsCurveFull5minDiagnosticRunnerTest(unittest.TestCase):
    def test_runner_uses_full_5min_data_without_approving_trade_rule(self) -> None:
        summary = run_v5f_physics_curve_full_5min_diagnostic(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_physics_curve_full_5min_diagnostic")
        self.assertEqual(
            summary["pm_gate_decision"],
            "full_5min_physics_diagnostic_positive_for_explanation_not_trade_rule",
        )
        self.assertTrue(summary["full_5min_test_completed"])
        self.assertEqual(summary["full_5min_scope"], "full_holding_period_5min")
        self.assertEqual(summary["effective_coverage_rate_pct"], 100.0)
        self.assertGreaterEqual(summary["held_stock_day_count"], 30000)
        self.assertEqual(summary["force_balance_panel_rows"], summary["held_stock_day_count"])
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertFalse(summary["intraday_momentum_nav_effective"])
        self.assertGreater(summary["short_window_shock_best_delta_vs_champion"], 0.0)
        self.assertEqual(summary["physics_full5min_verdict"], "usable_as_diagnostic_not_trade_rule")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertFalse(summary["limited_engineering_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_physics_curve_full_5min_diagnostic") / "current"
        for name in [
            "v5f_physics_full5min_summary.json",
            "v5f_physics_full5min_report.md",
            "v5f_physics_full5min_data_audit.csv",
            "v5f_physics_full5min_force_balance_panel.csv",
            "v5f_physics_full5min_component_effect_summary.csv",
            "v5f_physics_full5min_force_balance_diagnostics.csv",
            "v5f_physics_full5min_shock_reversion_diagnostics.csv",
            "v5f_physics_full5min_sleeve_response.csv",
            "v5f_physics_full5min_yearly_response.csv",
            "v5f_physics_full5min_reliability_audit.csv",
            "v5f_physics_full5min_governance_audit.csv",
            "v5f_physics_full5min_pm_gate_decision.csv",
            "v5f_physics_full5min_next_agent_queue.csv",
            "v5f_physics_full5min_blockers.csv",
            "v5f_physics_full5min_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_physics_full5min_data_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = {row["audit_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(audit["full_holding_5min_gate"]["status"], "pass")
        self.assertEqual(audit["full_holding_5min_gate"]["coverage_rate_pct"], "100.0")

        with (out / "v5f_physics_full5min_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5f_physics_full5min_component_effect_summary.csv").open("r", encoding="utf-8-sig", newline="") as f:
            components = {(row["physics_component"], row["state"]): row for row in csv.DictReader(f)}
        self.assertIn(("shock", "vwap_discount_shock"), components)
        self.assertEqual(components[("shock", "vwap_discount_shock")]["used_for_trade_rule"], "False")


if __name__ == "__main__":
    unittest.main()
