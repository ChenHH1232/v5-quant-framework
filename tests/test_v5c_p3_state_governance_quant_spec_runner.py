from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_p3_state_governance_quant_spec_runner import run_v5c_p3_state_governance_quant_spec


class V5cP3StateGovernanceQuantSpecRunnerTest(unittest.TestCase):
    def test_runner_builds_observe_only_state_governance_spec(self) -> None:
        summary = run_v5c_p3_state_governance_quant_spec(Path("."))

        self.assertEqual(summary["status"], "completed_p3_state_governance_quant_spec")
        self.assertEqual(
            summary["pm_gate_decision"],
            "p3_state_governance_spec_pass_ready_for_forward_observation_not_backtest",
        )
        self.assertTrue(summary["p2_dependency_pass"])
        self.assertGreater(summary["taxonomy_rows"], 0)
        self.assertGreater(summary["boundary_rows"], 0)
        self.assertGreater(summary["blocked_action_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_strategy_rule_added"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5c_p3_state_governance_quant_spec") / "current"
        expected = [
            "v5c_p3_state_governance_summary.json",
            "v5c_p3_state_governance_report.md",
            "v5c_p3_input_dependency_audit.csv",
            "v5c_p3_state_taxonomy.csv",
            "v5c_p3_state_observation_summary.csv",
            "v5c_p3_state_action_boundary_matrix.csv",
            "v5c_p3_allowed_diagnostic_uses.csv",
            "v5c_p3_blocked_actions.csv",
            "v5c_p3_forward_observation_schema.csv",
            "v5c_p3_state_transition_observation_spec.csv",
            "v5c_p3_overlay_engineering_approval_requirements.csv",
            "v5c_p3_pm_gate_decision.csv",
            "v5c_p3_next_agent_queue.csv",
            "v5c_p3_blockers.csv",
            "v5c_p3_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_p3_state_action_boundary_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            boundary = list(csv.DictReader(f))
        self.assertEqual(len(boundary), summary["boundary_rows"])
        self.assertTrue(all(row["trade_order_allowed"] == "False" for row in boundary))
        self.assertTrue(all(row["weight_change_allowed"] == "False" for row in boundary))
        self.assertTrue(all(row["engineering_backtest_allowed_now"] == "False" for row in boundary))
        self.assertTrue(all(row["requires_separate_pm_approval_for_any_trade_use"] == "True" for row in boundary))

        with (out / "v5c_p3_blocked_actions.csv").open("r", encoding="utf-8-sig", newline="") as f:
            blocked = list(csv.DictReader(f))
        self.assertEqual(len(blocked), summary["blocked_action_count"])
        self.assertTrue(all(row["blocked"] == "True" for row in blocked))
        self.assertIn("threshold_scan", {row["blocked_action"] for row in blocked})
        self.assertIn("accepted_or_live_approved", {row["blocked_action"] for row in blocked})

        with (out / "v5c_p3_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["p3_pass"], "True")
        self.assertEqual(decision["admit_forward_observation"], "True")
        self.assertEqual(decision["admit_engineering_backtest"], "False")
        self.assertEqual(decision["admit_trading_rule"], "False")
        self.assertEqual(decision["accepted"], "False")

        with (out / "v5c_p3_next_agent_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_gate"]: row for row in csv.DictReader(f)}
        self.assertEqual(queue["v5c_p4_state_forward_observation_packet"]["status"], "ready")
        self.assertEqual(queue["v5c_overheat_overlay_pm_quant_spec_separate_approval"]["status"], "blocked_until_separate_pm_approval")


if __name__ == "__main__":
    unittest.main()
