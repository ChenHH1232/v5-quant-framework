from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_internal_subsleeve_deep_research_spec_runner import run_v5f_internal_subsleeve_deep_research_spec


class V5fInternalSubSleeveDeepResearchSpecRunnerTest(unittest.TestCase):
    def test_runner_admits_only_internal_subsleeve_candidates(self) -> None:
        summary = run_v5f_internal_subsleeve_deep_research_spec(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_internal_subsleeve_deep_research_spec")
        self.assertEqual(summary["pm_gate_decision"], "admit_internal_subsleeve_to_deep_research_not_accepted")
        self.assertEqual(summary["admitted_count"], 2)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_internal_subsleeve_deep_research_spec") / "current"
        with (out / "v5f_internal_subsleeve_admitted_candidates.csv").open("r", encoding="utf-8-sig", newline="") as f:
            admitted = {row["direction_id"] for row in csv.DictReader(f)}
        self.assertEqual(
            admitted,
            {"internal_subsleeve_mom12_70_30", "internal_subsleeve_mom12_80_20"},
        )

        with (out / "v5f_internal_subsleeve_diagnostic_archive.csv").open("r", encoding="utf-8-sig", newline="") as f:
            archived = {row["direction_id"] for row in csv.DictReader(f)}
        self.assertIn("dual_sleeve_mom12_60_40", archived)
        self.assertIn("state_routed_mom12_70_30_or_100_0", archived)


if __name__ == "__main__":
    unittest.main()
