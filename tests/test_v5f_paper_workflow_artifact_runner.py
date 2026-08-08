from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_paper_workflow_artifact_runner import run_v5f_paper_workflow_artifacts


class V5fPaperWorkflowArtifactRunnerTest(unittest.TestCase):
    def test_runner_generates_templates_without_deployment_approval(self) -> None:
        summary = run_v5f_paper_workflow_artifacts(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_paper_workflow_artifacts")
        self.assertEqual(summary["paper_artifact_decision"], "paper_artifacts_ready_not_deployment_approved")
        self.assertEqual(summary["artifact_count"], 13)
        self.assertEqual(summary["candidate_count"], 3)
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v5e_accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_paper_workflow_artifacts") / "current"
        expected = [
            "v5f_paper_artifact_summary.json",
            "v5f_paper_artifact_report.md",
            "v5f_daily_paper_signal_log_template.csv",
            "v5f_v57f_reference_snapshot_template.csv",
            "v5f_v5e_profit_lock_observation_template.csv",
            "v5f_511360_proxy_observation_template.csv",
            "v5f_governance_audit_log_template.csv",
            "v5f_pm_review_cadence.csv",
            "v5f_handoff_checklist.csv",
            "v5f_candidate_status_dashboard.csv",
            "v5f_allowed_blocked_actions.csv",
            "v5f_next_queue.csv",
            "v5f_paper_artifact_blockers.csv",
            "v5f_next_prompt.md",
            "v5f_paper_artifact_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_candidate_status_dashboard.csv").open("r", encoding="utf-8-sig", newline="") as f:
            dashboard = {row["candidate_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(dashboard["v5e_profit_lock_main_20pct_sell50"]["accepted"], "False")
        self.assertEqual(dashboard["v5e_511360_cash_proxy"]["live_trading_approved"], "False")

        with (out / "v5f_next_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_task"]: row for row in csv.DictReader(f)}
        self.assertEqual(queue["V5e forward/paper tracking daily packet"]["allowed"], "True")
        self.assertEqual(queue["511360 official restore closeout"]["allowed"], "False")
        self.assertEqual(queue["V5e threshold scan"]["allowed"], "False")


if __name__ == "__main__":
    unittest.main()
