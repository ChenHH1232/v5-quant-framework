from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_repaired_overlay_forward_governance_runner import run_v5f_repaired_overlay_forward_governance


class V5fRepairedOverlayForwardGovernanceRunnerTest(unittest.TestCase):
    def test_runner_creates_forward_and_governance_packets_without_approval(self) -> None:
        summary = run_v5f_repaired_overlay_forward_governance(Path("."))

        tracking = summary["tracking"]
        governance = summary["governance"]
        self.assertEqual(tracking["status"], "completed_v5f_repaired_overlay_forward_paper_tracking_packet")
        self.assertEqual(governance["status"], "completed_v5f_overlay_deployment_governance_review")
        self.assertEqual(tracking["candidate_id"], "momentum_plus_mean_reversion_equal_blend")
        self.assertEqual(governance["candidate_id"], "momentum_plus_mean_reversion_equal_blend")
        self.assertFalse(tracking["accepted"])
        self.assertFalse(tracking["live_trading_approved"])
        self.assertFalse(tracking["deployment_approved"])
        self.assertFalse(governance["accepted"])
        self.assertFalse(governance["live_trading_approved"])
        self.assertFalse(governance["deployment_approved"])
        self.assertEqual(tracking["fatal_blocker_count"], 0)
        self.assertEqual(governance["fatal_blocker_count"], 0)

        tracking_out = Path("v5f_repaired_overlay_forward_paper_tracking") / "current"
        governance_out = Path("v5f_overlay_deployment_governance_review") / "current"
        for name in [
            "v5f_repaired_overlay_forward_summary.json",
            "v5f_repaired_overlay_forward_candidate_status.csv",
            "v5f_repaired_overlay_forward_tracking_schema.csv",
            "v5f_repaired_overlay_paper_signal_template.csv",
            "v5f_repaired_overlay_rebalance_day_checklist.csv",
            "v5f_repaired_overlay_forward_governance_audit.csv",
            "v5f_repaired_overlay_forward_next_queue.csv",
            "v5f_repaired_overlay_forward_blockers.csv",
            "v5f_repaired_overlay_forward_report.md",
            "v5f_repaired_overlay_forward_agent_execution_rules.md",
        ]:
            self.assertTrue((tracking_out / name).exists(), name)

        for name in [
            "v5f_overlay_governance_summary.json",
            "v5f_overlay_deployment_boundary_matrix.csv",
            "v5f_overlay_deployment_preflight.csv",
            "v5f_overlay_erc_v5e_conflict_matrix.csv",
            "v5f_overlay_implementation_control_checklist.csv",
            "v5f_overlay_acceptance_gate_matrix.csv",
            "v5f_overlay_turnover_cost_review.csv",
            "v5f_overlay_governance_pm_decision.csv",
            "v5f_overlay_governance_next_queue.csv",
            "v5f_overlay_governance_blockers.csv",
            "v5f_overlay_governance_report.md",
            "v5f_overlay_governance_agent_execution_rules.md",
        ]:
            self.assertTrue((governance_out / name).exists(), name)

        with (tracking_out / "v5f_repaired_overlay_forward_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (governance_out / "v5f_overlay_acceptance_gate_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            gates = {row["gate_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(gates["accepted"]["status"], "blocked")
        self.assertEqual(gates["live_approved"]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
