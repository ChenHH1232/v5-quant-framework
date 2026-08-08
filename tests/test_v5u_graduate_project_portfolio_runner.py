from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from v5.v5u_graduate_project_portfolio_runner import run_v5u_graduate_project_portfolio


class V5uGraduateProjectPortfolioTest(unittest.TestCase):
    def test_portfolio_pack_preserves_sample_split_and_candidate_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "portfolio"
            result = run_v5u_graduate_project_portfolio(Path("."), out)
            self.assertEqual(result["historical_research_window"], "2013-01-01_to_2021-04-30")
            self.assertEqual(result["formal_backtest_window"], "2021-05-01_to_2026-05-31")
            self.assertEqual(result["primary_candidate_status"], "primary_forward_paper_candidate_not_accepted")
            self.assertFalse(result["strategy_or_status_modified"])
            with (out / "v5u_sector_extension_scorecard.csv").open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 6)
            self.assertTrue((out / "v5u_pre2021_validation_evidence_hierarchy.md").exists())


if __name__ == "__main__": unittest.main()
