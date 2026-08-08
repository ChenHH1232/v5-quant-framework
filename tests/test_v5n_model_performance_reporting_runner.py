from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5n_model_performance_reporting_runner import run_v5n_model_performance_reporting


class V5nModelPerformanceReportingRunnerTest(unittest.TestCase):
    def test_generates_utf8_bom_companion_addenda_without_model_state_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "config").mkdir(); (root / "examples").mkdir(); (root / "v5f_demo/current").mkdir(parents=True)
            (root / "config/v5_historical_operation_boundary.json").write_text(json.dumps({"market_data_max_date": "2026-05-31"}), encoding="utf-8")
            (root / "config/v5_experiment_catalog.json").write_text(json.dumps({"experiments": [{"experiment_id": "demo_overlay", "baseline_id": "v57f_startup_preload_repaired_baseline"}]}), encoding="utf-8")
            (root / "config/v5_active_model_registry.json").write_text(json.dumps({"active_models": [], "research_lines": []}), encoding="utf-8")
            (root / "examples/demo_strategy.json").write_text(json.dumps({"strategy_id": "demo_strategy"}), encoding="utf-8")
            with (root / "v5f_demo/current/demo_daily_returns.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["trade_date", "strategy_return", "benchmark_return"]); writer.writeheader()
                for i in range(65): writer.writerow({"trade_date": f"2021-05-{(i % 28) + 1:02d}", "strategy_return": "0.001", "benchmark_return": "0.0005"})
            output = root / "out"
            summary = run_v5n_model_performance_reporting(root, output)
            self.assertFalse(summary["model_state_modified"])
            self.assertTrue((output / "v5n_unified_model_reporting_summary.json").exists())
            self.assertTrue((output / "v5n_model_report_completeness.csv").read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
