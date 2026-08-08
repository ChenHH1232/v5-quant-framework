from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5k_strategy_development_workflow_audit_runner import run_v5k_strategy_development_workflow_audit


class V5kStrategyDevelopmentWorkflowAuditRunnerTest(unittest.TestCase):
    def test_audit_writes_repairable_findings_without_strategy_promotion(self) -> None:
        summary = run_v5k_strategy_development_workflow_audit(Path("."))
        self.assertEqual(summary["status"], "completed_workflow_audit_repair_plan_ready")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertGreaterEqual(summary["p0_count"], 4)

        out = Path("v5k_strategy_development_workflow_audit") / "current"
        for name in [
            "v5k_workflow_finding_register.csv",
            "v5k_workflow_state_matrix.csv",
            "v5k_workflow_repair_queue.csv",
            "v5k_strategy_development_workflow_audit_report.md",
            "v5k_workflow_audit_summary.json",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5k_workflow_finding_register.csv").open(encoding="utf-8-sig", newline="") as handle:
            findings = {row["finding_id"]: row for row in csv.DictReader(handle)}
        self.assertIn("WF_P0_FORWARD_TARGET_AND_RECEIPT_GAP", findings)
        self.assertIn("WF_P0_PRE2021_EXACT_PIT_BOUNDARY", findings)
        self.assertEqual(findings["WF_P1_CASH_PATH_NOT_EXECUTABLE"]["status"], "open")


if __name__ == "__main__":
    unittest.main()
