from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_1min_volume_amount_timing_runner import run_v5h_1min_volume_amount_timing


class V5h1minVolumeAmountTimingRunnerTest(unittest.TestCase):
    def test_runner_tests_volume_amount_and_defines_v5h_line_without_trading_change(self) -> None:
        summary = run_v5h_1min_volume_amount_timing(Path("."))

        self.assertEqual(summary["status"], "completed_v5h_1min_volume_amount_timing_test")
        self.assertEqual(summary["v5h_line_id"], "v5h_1min_microstructure_execution_research")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "v5h_volume_amount_diagnostic_positive_ready_for_fixed_execution_spec_not_trading",
                "v5h_volume_amount_diagnostic_only_no_material_incremental_edge",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["feature_row_count"], 0)

        out = Path("v5h_1min_volume_amount_timing_test") / "current"
        for name in [
            "v5h_1min_volume_amount_summary.json",
            "v5h_1min_volume_amount_report.md",
            "v5h_1min_volume_amount_feature_schema.csv",
            "v5h_1min_volume_amount_feature_panel.csv",
            "v5h_1min_volume_amount_context_summary.csv",
            "v5h_1min_volume_amount_bucket_summary.csv",
            "v5h_1min_volume_amount_candidate_matrix.csv",
            "v5h_1min_volume_amount_data_gate.csv",
            "v5h_1min_volume_amount_governance_audit.csv",
            "v5h_1min_volume_amount_pm_gate_decision.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        gov = Path("v5h_1min_research_line_governance") / "current"
        for name in [
            "v5h_1min_research_line_summary.json",
            "v5h_1min_component_mapping.csv",
            "v5h_1min_line_governance_audit.csv",
            "v5h_1min_line_pm_gate_decision.csv",
        ]:
            self.assertTrue((gov / name).exists(), name)

        with (out / "v5h_1min_volume_amount_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            audit = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (gov / "v5h_1min_component_mapping.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            mapping = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(mapping), 6)
        self.assertTrue(any(row["v5h_component_id"] == "v5h_volume_amount_timing" for row in mapping))


if __name__ == "__main__":
    unittest.main()
