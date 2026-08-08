from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_cash_drag_robustness_runner import (
    MAIN_CANDIDATE,
    SECONDARY_CANDIDATE,
    run_v5e_cash_drag_robustness,
)


class V5eCashDragRobustnessRunnerTest(unittest.TestCase):
    def test_runner_outputs_gate_without_acceptance_or_parameter_scan(self) -> None:
        root = Path(".")
        summary = run_v5e_cash_drag_robustness(root)

        self.assertEqual(summary["status"], "completed_cash_drag_robustness_packet")
        self.assertEqual(summary["pm_gate_decision"], "retain_v5e_combined_main_candidate_needs_forward_or_paper")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_replacement"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["parameter_scan_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_cash_drag_robustness_packet" / "current"
        self.assertTrue((out / "v5e_cash_periods.csv").exists())
        self.assertTrue((out / "v5e_exit_post_return_5d_10d_20d_60d.csv").exists())
        self.assertTrue((out / "v5e_clean_pm_quant_review_report.md").exists())

        with (out / "v5e_candidate_stability_review.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        versions = {row["version_id"] for row in rows}
        self.assertIn(MAIN_CANDIDATE, versions)
        self.assertIn(SECONDARY_CANDIDATE, versions)


if __name__ == "__main__":
    unittest.main()
