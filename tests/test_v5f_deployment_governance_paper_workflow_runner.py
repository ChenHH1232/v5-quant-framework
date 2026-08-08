from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_deployment_governance_paper_workflow_runner import (
    run_v5f_deployment_governance_paper_workflow,
)


class V5fDeploymentGovernancePaperWorkflowRunnerTest(unittest.TestCase):
    def test_runner_prepares_paper_workflow_without_deployment_approval(self) -> None:
        summary = run_v5f_deployment_governance_paper_workflow(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_deployment_governance_paper_workflow")
        self.assertEqual(
            summary["v5f_governance_decision"],
            "paper_workflow_preparation_ready_not_deployment_approved",
        )
        self.assertEqual(summary["workflow_step_count"], 6)
        self.assertEqual(summary["candidate_count"], 3)
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v5e_accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_deployment_governance_paper_workflow") / "current"
        expected = [
            "v5f_governance_summary.json",
            "v5f_governance_report.md",
            "v5f_paper_workflow.csv",
            "v5f_candidate_registry.csv",
            "v5f_preflight_checks.csv",
            "v5f_paper_signal_templates.csv",
            "v5f_governance_audit_controls.csv",
            "v5f_acceptance_gate_matrix.csv",
            "v5f_allowed_blocked_actions.csv",
            "v5f_governance_decision.csv",
            "v5f_next_queue.csv",
            "v5f_governance_blockers.csv",
            "v5f_next_prompt.md",
            "v5f_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_governance_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(
            decision["v5f_governance_decision"],
            "paper_workflow_preparation_ready_not_deployment_approved",
        )
        self.assertEqual(decision["deployment_approved"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")
        self.assertEqual(decision["v5e_accepted"], "False")
        self.assertEqual(decision["threshold_scan_used"], "False")

        with (out / "v5f_candidate_registry.csv").open("r", encoding="utf-8-sig", newline="") as f:
            registry = {row["candidate_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(registry["v57f_repaired_baseline"]["status"], "formal_etf_candidate_not_live_approved")
        self.assertEqual(registry["v5e_profit_lock_main_20pct_sell50"]["accepted"], "False")
        self.assertEqual(registry["v5e_511360_cash_proxy"]["live_trading_approved"], "False")

        with (out / "v5f_next_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_task"]: row for row in csv.DictReader(f)}
        self.assertEqual(queue["V5f paper workflow artifact generation"]["allowed"], "True")
        self.assertEqual(queue["V5e forward/paper tracking continuation"]["allowed"], "True")
        self.assertEqual(queue["Deployment approval review"]["allowed"], "False")


if __name__ == "__main__":
    unittest.main()
