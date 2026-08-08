from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5g_04_exit_policy_spec_runner import run_v5g_04_exit_policy_spec


class V5g04ExitPolicySpecRunnerTest(unittest.TestCase):
    def test_runner_builds_511360_attachment_spec_without_approving_attachment(self) -> None:
        summary = run_v5g_04_exit_policy_spec(Path("."))

        self.assertEqual(summary["status"], "completed_v5g_04_exit_policy_spec")
        self.assertEqual(
            summary["pm_gate_decision"],
            "v5g_04_exit_policy_spec_pass_cash_proxy_attachable_after_approved_cash_event_not_engineering",
        )
        self.assertTrue(summary["exit_policy_spec_pass"])
        self.assertEqual(summary["cash_proxy_asset"], "511360")
        self.assertFalse(summary["cash_proxy_attachment_approved"])
        self.assertFalse(summary["limited_engineering_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5g_04_exit_policy_spec") / "current"
        expected = [
            "v5g_04_exit_policy_summary.json",
            "v5g_04_exit_policy_report.md",
            "v5g_04_exit_policy_dependency_audit.csv",
            "v5g_04_exit_policy_rule_spec.csv",
            "v5g_04_cash_source_admission_matrix.csv",
            "v5g_04_511360_attachment_lifecycle.csv",
            "v5g_04_pit_execution_data_requirements.csv",
            "v5g_04_governance_boundary.csv",
            "v5g_04_exit_policy_pm_gate_decision.csv",
            "v5g_04_exit_policy_next_agent_queue.csv",
            "v5g_04_exit_policy_blockers.csv",
            "v5g_04_exit_policy_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5g_04_governance_boundary.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5g_04_cash_source_admission_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            sources = {row["cash_source_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(sources["v5g_01_state_gated_internal_subsleeve"]["511360_attachable"], "False")
        self.assertEqual(sources["baseline_idle_cash"]["511360_attachable"], "False")
        self.assertEqual(sources["v5e_profit_lock_sleeve_cash_bucket"]["511360_attachable"], "True")

        with (out / "v5g_04_exit_policy_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["cash_proxy_attachment_approved_now"], "False")
        self.assertEqual(decision["admit_limited_engineering_now"], "False")
        self.assertEqual(decision["accepted"], "False")


if __name__ == "__main__":
    unittest.main()
