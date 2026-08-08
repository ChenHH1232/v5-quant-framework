from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5p_benchmark_discovery_and_research_sequence_runner import run_v5p_benchmark_discovery_and_research_sequence


class V5pBenchmarkDiscoveryRunnerTest(unittest.TestCase):
    def test_reuses_tiers_without_fetching_or_changing_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); v5o = root / "v5o_reporting_tier_reclassification/current"; v5n = root / "v5n_model_performance_reporting/current"; v5o.mkdir(parents=True); v5n.mkdir(parents=True)
            (v5o / "v5o_reporting_tier_summary.json").write_text(json.dumps({"total_units": 335, "model_status_modified": False}), encoding="utf-8")
            _csv(v5o / "v5o_tier_a_comparable_models_table.csv", [{"canonical_model_id": "bank_demo", "family": "sector", "primary_benchmark": "proxy", "benchmark_type": "static_proxy_basket", "tier": "tier_a2", "classification_reason": "ok"}])
            _csv(v5o / "v5o_tier_b_evidence_only_models_table.csv", [{"canonical_model_id": "b", "tier": "tier_b1", "classification_reason": "missing"}]); _csv(v5o / "v5o_tier_c_archived_alias_table.csv", [{"canonical_model_id": "c", "tier": "tier_c", "classification_reason": "archived"}])
            _csv(v5n / "v5n_formal_backtest_performance_statistics.csv", [{"canonical_model_id": "bank_demo", "total_return_pct": "1"}]); _csv(v5n / "v5n_model_report_link_index.csv", [{"canonical_model_id": "bank_demo", "addendum_path": "a"}])
            (root / "v5f_structural_rough_screen/current").mkdir(parents=True)
            _csv(root / "v5f_structural_rough_screen/current/v5f_structural_rough_screen_daily_returns.csv", [{"trade_date": "2021-05-06", "version_id": "v57f_startup_preload_repaired_baseline"}])
            result = run_v5p_benchmark_discovery_and_research_sequence(root, root / "out", fetch_public_data=False)
            self.assertFalse(result["model_status_modified"]); self.assertTrue((root / "out/v5p_summary.json").exists())


def _csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__": unittest.main()
