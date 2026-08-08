from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from v5.v5t_report_publication_finalization_runner import run_v5t_publication


class V5tReportPublicationFinalizationTest(unittest.TestCase):
    def test_archive_release_uses_only_canonical_pair_and_retains_disclosures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "publication"
            summary = run_v5t_publication(Path("."), out)
            self.assertEqual(summary["release_decision"], "archive_release_pass_with_required_disclosures")
            self.assertEqual(summary["pairwise_observations"], 1228)
            self.assertFalse(summary["accepted"])
            with (out / "v5t_statistics_and_table_audit.csv").open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual({row["canonical_model_id"] for row in rows}, {"v57f_startup_preload_repaired_baseline", "internal_subsleeve_mom12_70_30"})
            with (out / "v5t_disclosure_coverage_audit.csv").open(encoding="utf-8-sig", newline="") as handle:
                disclosures = list(csv.DictReader(handle))
            self.assertTrue(all(row["status"] == "pass" for row in disclosures))


if __name__ == "__main__":
    unittest.main()
