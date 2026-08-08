from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5q_overall_report_readiness_repair_runner import run_v5q_v5r_overall_report_readiness


class V5qOverallReportReadinessRepairRunnerTest(unittest.TestCase):
    def test_contract_excludes_etf_price_return_from_formal_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "v5o_reporting_tier_reclassification/current").mkdir(parents=True); (root / "v5n_model_performance_reporting/current").mkdir(parents=True); (root / "v5p_benchmark_discovery_and_research_sequence/current").mkdir(parents=True); (root / "v5c_sleeve_weighting_diagnostic/current").mkdir(parents=True); (root / "v5f_structural_rough_screen/current").mkdir(parents=True)
            tiers = [{"canonical_model_id": "v57f_startup_preload_repaired_baseline", "tier": "tier_a1", "primary_benchmark": "self", "family": "baseline"}, {"canonical_model_id": "internal_subsleeve_mom12_70_30", "tier": "tier_a1", "primary_benchmark": "v57f_startup_preload_repaired_baseline", "family": "overlay"}] + [{"canonical_model_id": f"u{i}", "tier": "tier_b1", "primary_benchmark": "na", "family": "research"} for i in range(333)]
            _csv(root / "v5o_reporting_tier_reclassification/current/v5o_model_tier_assignment.csv", tiers)
            _csv(root / "v5n_model_performance_reporting/current/v5n_formal_backtest_performance_statistics.csv", [{"canonical_model_id": x["canonical_model_id"], "total_return_pct": "1"} for x in tiers])
            _csv(root / "v5p_benchmark_discovery_and_research_sequence/current/v5p_benchmark_return_contract_audit.csv", [{"candidate_id": "etf", "adjusted": "yes", "return_contract": "adjusted_price_return_not_total_return", "status": "qualified"}])
            _csv(root / "v5c_sleeve_weighting_diagnostic/current/v5c_sleeve_weighting_daily_nav.csv", [{"trade_date": "2021-10-08", "scheme_id": "a"}, {"trade_date": "2021-10-09", "scheme_id": "b"}])
            result = run_v5q_v5r_overall_report_readiness(root, root / "q", root / "r")
            self.assertEqual(result["q"]["status"], "pass_with_required_disclosures")
            self.assertFalse(result["r"]["model_status_modified"])


def _csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__": unittest.main()
