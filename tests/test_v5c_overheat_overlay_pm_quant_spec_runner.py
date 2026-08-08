from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_overheat_overlay_pm_quant_spec_runner import run_v5c_overheat_overlay_pm_quant_spec


class V5cOverheatOverlayPmQuantSpecRunnerTest(unittest.TestCase):
    def test_runner_builds_spec_only_packet_after_user_approval(self) -> None:
        summary = run_v5c_overheat_overlay_pm_quant_spec(Path("."))

        self.assertEqual(summary["status"], "completed_overheat_overlay_pm_quant_spec")
        self.assertEqual(
            summary["pm_gate_decision"],
            "overheat_overlay_pm_quant_spec_pass_ready_for_limited_engineering_decision_not_backtest",
        )
        self.assertTrue(summary["spec_opening_user_approved"])
        self.assertGreater(summary["candidate_spec_count"], 0)
        self.assertGreater(summary["admitted_spec_only_count"], 0)
        self.assertGreater(summary["blocked_action_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_strategy_rule_added"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5c_overheat_overlay_pm_quant_spec") / "current"
        expected = [
            "v5c_overheat_overlay_pm_quant_spec_summary.json",
            "v5c_overheat_overlay_pm_quant_spec_report.md",
            "v5c_overheat_overlay_input_dependency_audit.csv",
            "v5c_overheat_overlay_user_approval_scope.csv",
            "v5c_overheat_overlay_state_evidence_summary.csv",
            "v5c_overheat_overlay_trigger_state_mapping.csv",
            "v5c_overheat_overlay_fixed_rule_spec_candidates.csv",
            "v5c_overheat_overlay_allowed_blocked_actions.csv",
            "v5c_overheat_overlay_pit_contract_requirements.csv",
            "v5c_overheat_overlay_v5c_erc_v5e_boundary_matrix.csv",
            "v5c_overheat_overlay_engineering_readiness_checklist.csv",
            "v5c_overheat_overlay_pm_gate_decision.csv",
            "v5c_overheat_overlay_next_agent_queue.csv",
            "v5c_overheat_overlay_blockers.csv",
            "v5c_overheat_overlay_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_overheat_overlay_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["spec_pass"], "True")
        self.assertEqual(decision["user_approved_spec_opening"], "True")
        self.assertEqual(decision["admit_limited_engineering_now"], "False")
        self.assertEqual(decision["admit_trading_rule"], "False")
        self.assertEqual(decision["engineering_backtest_started"], "False")

        with (out / "v5c_overheat_overlay_fixed_rule_spec_candidates.csv").open("r", encoding="utf-8-sig", newline="") as f:
            candidates = list(csv.DictReader(f))
        self.assertTrue(any(row["pm_admission_status"] == "admit_to_spec_only" for row in candidates))
        self.assertTrue(all(row["engineering_backtest_allowed_now"] == "False" for row in candidates))

        with (out / "v5c_overheat_overlay_next_agent_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_gate"]: row for row in csv.DictReader(f)}
        self.assertEqual(
            queue["v5c_overheat_overlay_limited_engineering_approval_request"]["status"],
            "blocked_until_user_explicitly_approves_limited_engineering",
        )


if __name__ == "__main__":
    unittest.main()
