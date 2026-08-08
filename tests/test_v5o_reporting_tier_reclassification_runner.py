from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5o_reporting_tier_reclassification_runner import run_v5o_reporting_tier_reclassification


class V5oReportingTierReclassificationRunnerTest(unittest.TestCase):
    def test_all_units_receive_one_tier_without_status_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "v5n_model_performance_reporting/current"; source.mkdir(parents=True)
            (source / "v5n_unified_model_reporting_summary.json").write_text(json.dumps({"model_count": 335, "required_baseline": "v57f_startup_preload_repaired_baseline"}), encoding="utf-8")
            ids = [f"unit_{i}" for i in range(335)]
            _csv(source / "v5n_all_models_status_and_limitations.csv", [{"canonical_model_id": i, "report_status": "report_complete_validation_not_independent" if i == "unit_0" else "diagnostic_only_no_nav_claim", "daily_series_status": "available" if i == "unit_0" else "daily_nav_unavailable", "benchmark_status": "coverage_pass" if i == "unit_0" else "benchmark_coverage_insufficient"} for i in ids])
            _csv(source / "v5n_all_models_benchmark_register.csv", [{"canonical_model_id": i, "benchmark_type": "parent_strategy" if i == "unit_0" else "not_available", "benchmark_id": "baseline", "primary_benchmark_statement": "parent"} for i in ids])
            _csv(source / "v5n_validation_period_statistics.csv", [{"canonical_model_id": i, "validation_result": "validation_not_independent_or_overlapping"} for i in ids])
            _csv(source / "v5n_model_report_link_index.csv", [{"canonical_model_id": i, "addendum_path": "addendum", "source_evidence_paths": "source"} for i in ids])
            _csv(source / "v5n_model_identity_and_lineage.csv", [{"canonical_model_id": i, "family": "test", "role": "test", "alpha_beta_ir_computable": "True" if i == "unit_0" else "False"} for i in ids])
            result = run_v5o_reporting_tier_reclassification(root, root / "out")
            self.assertEqual(result["total_units"], 335); self.assertFalse(result["model_status_modified"])
            self.assertEqual(result["tier_counts"]["tier_a1_comparable_parent_or_market_benchmark"], 1)


def _csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__": unittest.main()
