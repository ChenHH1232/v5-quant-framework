from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5k_workflow_repair_closeout_runner import run_v5k_workflow_repair_closeout


class V5kWorkflowRepairCloseoutRunnerTest(unittest.TestCase):
    def test_preserves_real_evidence_boundaries(self) -> None:
        summary = run_v5k_workflow_repair_closeout(Path("."))
        self.assertEqual(summary["market_data_max_date"], "2026-05-31")
        self.assertEqual(summary["unresolved_evidence_boundary_count"], 2)
        self.assertFalse(summary["accepted"])
        self.assertTrue((Path("v5k_workflow_repair_closeout") / "current" / "v5k_workflow_repair_status.csv").exists())


if __name__ == "__main__":
    unittest.main()
