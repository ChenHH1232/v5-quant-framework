from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_internal_subsleeve_robustness_packet_runner import (
    run_v5f_internal_subsleeve_robustness_packet,
)


class V5fInternalSubSleeveRobustnessPacketRunnerTest(unittest.TestCase):
    def test_runner_builds_robustness_packet_without_acceptance(self) -> None:
        summary = run_v5f_internal_subsleeve_robustness_packet(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_internal_subsleeve_robustness_packet")
        self.assertEqual(
            summary["pm_gate_decision"],
            "robustness_packet_pass_continue_forward_paper_not_accepted",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertGreater(summary["delta_return_pct_points_vs_repaired_baseline"], 10.0)
        self.assertLessEqual(summary["delta_max_drawdown_pct_points_vs_repaired_baseline"], 0.0)
        self.assertEqual(summary["yearly_win_count"], 4)
        self.assertGreaterEqual(summary["yearly_win_rate"], 0.60)
        self.assertEqual(summary["rebalance_period_win_count"], 13)
        self.assertGreaterEqual(summary["rebalance_period_win_rate"], 0.55)
        self.assertLessEqual(summary["max_stock_active_weight_delta_share"], 0.05)
        self.assertLessEqual(summary["max_sleeve_active_weight_delta_share"], 0.35)
        self.assertEqual(summary["cost_health"], "pass")
        self.assertLess(summary["v5g01_delta_return_pct_points_vs_primary"], 0.0)
        self.assertEqual(summary["target_population_status"], "not_populated_waiting_next_clean_official_repaired_v57f_targets")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_internal_subsleeve_robustness_packet") / "current"
        expected = [
            "v5f_internal_subsleeve_robustness_summary.json",
            "v5f_internal_subsleeve_robustness_report.md",
            "v5f_internal_subsleeve_robustness_input_manifest.csv",
            "v5f_internal_subsleeve_robustness_metric_snapshot.csv",
            "v5f_internal_subsleeve_robustness_yearly_review.csv",
            "v5f_internal_subsleeve_robustness_rebalance_period_review.csv",
            "v5f_internal_subsleeve_robustness_sleeve_contribution.csv",
            "v5f_internal_subsleeve_robustness_stock_concentration.csv",
            "v5f_internal_subsleeve_robustness_top_events.csv",
            "v5f_internal_subsleeve_robustness_cost_health.csv",
            "v5f_internal_subsleeve_robustness_stress_notes.csv",
            "v5f_internal_subsleeve_robustness_governance_audit.csv",
            "v5f_internal_subsleeve_robustness_pm_gate_decision.csv",
            "v5f_internal_subsleeve_robustness_next_agent_queue.csv",
            "v5f_internal_subsleeve_robustness_next_prompt.md",
            "v5f_internal_subsleeve_robustness_blockers.csv",
            "v5f_internal_subsleeve_robustness_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_internal_subsleeve_robustness_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5f_internal_subsleeve_robustness_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")
        self.assertEqual(decision["deployment_approved"], "False")
        self.assertEqual(decision["threshold_scan_used"], "False")

        prompt = (out / "v5f_internal_subsleeve_robustness_next_prompt.md").read_text(encoding="utf-8")
        self.assertIn("not accepted", prompt)
        self.assertIn("2026-05-31", prompt)
        self.assertIn("startup preload repaired", prompt)


if __name__ == "__main__":
    unittest.main()
