from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_internal_subsleeve_deployment_governance_runner import (
    run_v5f_internal_subsleeve_deployment_governance,
)


class V5fInternalSubSleeveDeploymentGovernanceRunnerTest(unittest.TestCase):
    def test_runner_replaces_equal_blend_for_paper_only_without_acceptance(self) -> None:
        summary = run_v5f_internal_subsleeve_deployment_governance(Path("."))

        governance = summary["governance"]
        replacement = summary["replacement"]
        self.assertEqual(governance["status"], "completed_v5f_internal_subsleeve_deployment_governance")
        self.assertEqual(replacement["status"], "completed_v5f_internal_subsleeve_candidate_replacement_packet")
        self.assertEqual(governance["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(replacement["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(governance["pm_gate_decision"], "deployment_governance_ready_for_forward_paper_not_live")
        self.assertEqual(
            replacement["pm_gate_decision"],
            "replace_equal_blend_with_internal_subsleeve_70_30_as_primary_forward_candidate_not_accepted",
        )
        self.assertGreater(governance["delta_return_pct_points_vs_repaired_baseline"], 10.0)
        self.assertGreater(replacement["incremental_delta_return_vs_prior_primary"], 10.0)
        self.assertFalse(governance["accepted"])
        self.assertFalse(governance["live_trading_approved"])
        self.assertFalse(governance["deployment_approved"])
        self.assertFalse(replacement["accepted"])
        self.assertFalse(replacement["live_trading_approved"])
        self.assertFalse(replacement["deployment_approved"])
        self.assertEqual(governance["fatal_blocker_count"], 0)
        self.assertEqual(replacement["fatal_blocker_count"], 0)

        governance_out = Path("v5f_internal_subsleeve_deployment_governance") / "current"
        replacement_out = Path("v5f_internal_subsleeve_candidate_replacement_packet") / "current"
        for name in [
            "v5f_internal_subsleeve_deployment_summary.json",
            "v5f_internal_subsleeve_deployment_preflight.csv",
            "v5f_internal_subsleeve_deployment_boundary_matrix.csv",
            "v5f_internal_subsleeve_implementation_control_checklist.csv",
            "v5f_internal_subsleeve_acceptance_gate_matrix.csv",
            "v5f_internal_subsleeve_component_conflict_matrix.csv",
            "v5f_internal_subsleeve_deployment_pm_decision.csv",
            "v5f_internal_subsleeve_deployment_next_queue.csv",
            "v5f_internal_subsleeve_deployment_report.md",
        ]:
            self.assertTrue((governance_out / name).exists(), name)

        for name in [
            "v5f_candidate_replacement_summary.json",
            "v5f_candidate_replacement_matrix.csv",
            "v5f_prior_candidate_demotion.csv",
            "v5f_candidate_replacement_pm_decision.csv",
            "v5f_candidate_replacement_next_queue.csv",
            "v5f_candidate_replacement_report.md",
        ]:
            self.assertTrue((replacement_out / name).exists(), name)

        with (replacement_out / "v5f_candidate_replacement_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["candidate_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(rows["internal_subsleeve_mom12_70_30"]["role_after"], "primary_forward_paper_candidate_not_accepted")
        self.assertEqual(rows["momentum_plus_mean_reversion_equal_blend"]["role_after"], "secondary_reference_archived_from_primary")

        with (governance_out / "v5f_internal_subsleeve_acceptance_gate_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            gates = {row["gate_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(gates["accepted"]["status"], "blocked")
        self.assertEqual(gates["live_approved"]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
