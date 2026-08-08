from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from v5.v5s_report_draft_review_runner import _recompute_pair, run_v5s_report_draft_review


class V5sReportDraftReviewRunnerTest(unittest.TestCase):
    def test_canonical_pair_has_1228_common_observations(self) -> None:
        stats = _recompute_pair(Path("."))
        self.assertEqual(stats["internal_subsleeve_mom12_70_30"]["observations"], 1228)
        self.assertEqual(stats["v57f_startup_preload_repaired_baseline"]["observations"], 1228)

    def test_review_requires_disclosures_and_does_not_change_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            result = run_v5s_report_draft_review(Path("."), output / "q", output / "r")
            self.assertEqual(result["release_decision"], "draft_review_pass_with_disclosures")
            self.assertFalse(result["model_status_modified"])


if __name__ == "__main__": unittest.main()
