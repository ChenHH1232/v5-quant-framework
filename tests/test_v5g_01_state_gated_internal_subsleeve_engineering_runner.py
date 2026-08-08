from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5g_01_state_gated_internal_subsleeve_engineering_runner import (
    run_v5g_01_state_gated_internal_subsleeve_engineering,
)


class V5g01StateGatedInternalSubSleeveEngineeringRunnerTest(unittest.TestCase):
    def test_runner_keeps_state_gate_secondary_when_it_does_not_beat_champion(self) -> None:
        summary = run_v5g_01_state_gated_internal_subsleeve_engineering(Path("."))

        self.assertEqual(summary["status"], "completed_v5g_01_state_gated_limited_engineering")
        self.assertEqual(
            summary["pm_gate_decision"],
            "v5g_01_limited_engineering_pass_but_do_not_replace_internal_subsleeve_champion",
        )
        self.assertGreater(summary["state_gated_delta_return_pct_points_vs_repaired_baseline"], 0.0)
        self.assertLess(summary["state_gated_delta_return_pct_points_vs_internal_subsleeve_champion"], 0.0)
        self.assertEqual(summary["hot_gate_event_count"], 2)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["cash_proxy_used"])
        self.assertTrue(summary["limited_engineering_started"])
        self.assertTrue(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5g_01_state_gated_internal_subsleeve_limited_engineering") / "current"
        expected = [
            "v5g_01_state_gated_engineering_summary.json",
            "v5g_01_state_gated_engineering_report.md",
            "v5g_01_state_gated_engineering_weights.csv",
            "v5g_01_state_gated_engineering_daily_returns.csv",
            "v5g_01_state_gated_engineering_metrics.csv",
            "v5g_01_state_gated_engineering_yearly.csv",
            "v5g_01_state_gated_engineering_rebalance_period.csv",
            "v5g_01_state_gate_event_impact.csv",
            "v5g_01_state_gated_sleeve_impact.csv",
            "v5g_01_state_gated_governance_audit.csv",
            "v5g_01_state_gated_pm_gate_decision.csv",
            "v5g_01_state_gated_next_agent_queue.csv",
            "v5g_01_state_gated_engineering_blockers.csv",
            "v5g_01_state_gated_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5g_01_state_gated_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5g_01_state_gated_engineering_metrics.csv").open("r", encoding="utf-8-sig", newline="") as f:
            metrics = {row["version_id"]: row for row in csv.DictReader(f)}
        self.assertIn("v5g_01_state_gated_internal_subsleeve_70_30", metrics)
        self.assertIn("internal_subsleeve_mom12_70_30", metrics)
        self.assertGreater(
            float(metrics["v5g_01_state_gated_internal_subsleeve_70_30"]["delta_return_pct_points_vs_repaired_baseline"]),
            0.0,
        )
        self.assertLess(
            float(metrics["v5g_01_state_gated_internal_subsleeve_70_30"]["delta_return_pct_points_vs_internal_subsleeve_champion"]),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
