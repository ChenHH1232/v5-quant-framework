from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_overheat_no_new_overweight_engineering_runner import (
    run_v5c_overheat_no_new_overweight_engineering,
)


class V5cOverheatNoNewOverweightEngineeringRunnerTest(unittest.TestCase):
    def test_runner_keeps_guard_diagnostic_when_it_lags_v5f_champion(self) -> None:
        summary = run_v5c_overheat_no_new_overweight_engineering(Path("."))

        self.assertEqual(summary["status"], "completed_v5c_overheat_no_new_overweight_limited_engineering")
        self.assertEqual(
            summary["pm_gate_decision"],
            "overheat_no_new_overweight_diagnostic_only_do_not_replace_v5f_champion",
        )
        self.assertEqual(summary["candidate_id"], "v5c_overheat_no_new_overweight_on_v5f_mom12_70_30")
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertLess(summary["candidate_delta_return_pct_points_vs_primary"], 0.0)
        self.assertEqual(summary["candidate_delta_drawdown_pct_points_vs_primary"], 0.0)
        self.assertEqual(summary["touched_rebalance_sleeve_count"], 1)
        self.assertEqual(summary["touched_stock_rows"], 1)
        self.assertFalse(summary["v5f_champion_replaced"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5c_overheat_no_new_overweight_limited_engineering") / "current"
        expected = [
            "v5c_overheat_no_new_overweight_summary.json",
            "v5c_overheat_no_new_overweight_report.md",
            "v5c_overheat_no_new_overweight_weights.csv",
            "v5c_overheat_no_new_overweight_daily_returns.csv",
            "v5c_overheat_no_new_overweight_metrics.csv",
            "v5c_overheat_no_new_overweight_yearly.csv",
            "v5c_overheat_no_new_overweight_rebalance_period_comparison.csv",
            "v5c_overheat_no_new_overweight_trigger_touch_set.csv",
            "v5c_overheat_no_new_overweight_governance_audit.csv",
            "v5c_overheat_no_new_overweight_pm_gate_decision.csv",
            "v5c_overheat_no_new_overweight_next_agent_queue.csv",
            "v5c_overheat_no_new_overweight_blockers.csv",
            "v5c_overheat_no_new_overweight_next_prompt.md",
            "v5c_overheat_no_new_overweight_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_overheat_no_new_overweight_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5c_overheat_no_new_overweight_trigger_touch_set.csv").open("r", encoding="utf-8-sig", newline="") as f:
            touch = list(csv.DictReader(f))
        self.assertEqual(len(touch), 1)
        self.assertEqual(touch[0]["rebalance_date"], "2024-10-08")
        self.assertEqual(touch[0]["sleeve_id"], "highway_infrastructure")
        self.assertEqual(touch[0]["single_stock_sell"], "False")
        self.assertEqual(touch[0]["cross_sleeve_transfer"], "False")

        with (out / "v5c_overheat_no_new_overweight_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["replace_v5f_champion"], "False")
        self.assertLess(float(decision["triggered_period_delta_return_pct_points_vs_primary"]), 0.0)


if __name__ == "__main__":
    unittest.main()
