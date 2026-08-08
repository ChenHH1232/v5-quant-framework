from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_physics_curve_diagnostic_spec_runner import run_v5f_physics_curve_diagnostic_spec


class V5fPhysicsCurveDiagnosticSpecRunnerTest(unittest.TestCase):
    def test_runner_builds_physics_spec_without_trading_approval(self) -> None:
        summary = run_v5f_physics_curve_diagnostic_spec(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_physics_curve_diagnostic_spec")
        self.assertEqual(summary["pm_gate_decision"], "physics_curve_diagnostic_spec_ready_not_engineering")
        self.assertTrue(summary["physics_curve_can_be_used_in_v5"])
        self.assertEqual(summary["recommended_use"], "diagnostic_explanation_and_feature_panel_spec")
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertFalse(summary["limited_engineering_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_physics_curve_diagnostic_spec") / "current"
        expected = [
            "v5f_physics_curve_diagnostic_summary.json",
            "v5f_physics_curve_diagnostic_report.md",
            "v5f_physics_factor_mapping.csv",
            "v5f_physics_v4_reference_manifest.csv",
            "v5f_physics_v5_data_availability.csv",
            "v5f_physics_allowed_diagnostic_uses.csv",
            "v5f_physics_blocked_trading_uses.csv",
            "v5f_physics_candidate_feature_schema.csv",
            "v5f_physics_model_hypothesis_matrix.csv",
            "v5f_physics_pm_gate_decision.csv",
            "v5f_physics_next_agent_queue.csv",
            "v5f_physics_blockers.csv",
            "v5f_physics_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_physics_factor_mapping.csv").open("r", encoding="utf-8-sig", newline="") as f:
            roles = {row["physics_component"] for row in csv.DictReader(f)}
        self.assertTrue({"position", "velocity", "acceleration", "restoring_force", "shock", "temperature_pressure"}.issubset(roles))

        with (out / "v5f_physics_blocked_trading_uses.csv").open("r", encoding="utf-8-sig", newline="") as f:
            blocked = {row["blocked_use_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(blocked["full_market_stock_selection"]["blocked"], "True")
        self.assertEqual(blocked["accepted_strategy_status"]["blocked"], "True")
        self.assertEqual(blocked["parameter_scan"]["blocked"], "True")

        with (out / "v5f_physics_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["limited_engineering_allowed_now"], "False")
        self.assertEqual(decision["engineering_backtest_started"], "False")
        self.assertEqual(decision["primary_candidate_remains"], "internal_subsleeve_mom12_70_30")


if __name__ == "__main__":
    unittest.main()
