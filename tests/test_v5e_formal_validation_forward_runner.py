from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_formal_validation_forward_runner import (
    MAIN_CANDIDATE,
    run_v5e_formal_validation_forward_packet,
)


class V5eFormalValidationForwardRunnerTest(unittest.TestCase):
    def test_runner_marks_effective_review_candidate_not_accepted(self) -> None:
        root = Path(".")
        summary = run_v5e_formal_validation_forward_packet(root)

        self.assertEqual(summary["status"], "completed_formal_validation_forward_packet")
        self.assertEqual(summary["model_effectiveness"], "effective_v5e_review_candidate_not_accepted")
        self.assertEqual(summary["next_gate"], "remain_candidate_needs_forward_or_paper_evidence")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_replacement"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["parameter_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_formal_validation_forward_packet" / "current"
        self.assertTrue((out / "v5e_forward_signal_template.csv").exists())
        self.assertTrue((out / "v5e_model_effectiveness_decision.csv").exists())
        with (out / "v5e_candidate_status.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        main = next(row for row in rows if row["candidate_id"] == MAIN_CANDIDATE)
        self.assertEqual(main["status"], "effective_model_candidate_not_accepted")


if __name__ == "__main__":
    unittest.main()
