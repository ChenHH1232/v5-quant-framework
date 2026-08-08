from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_market_cap_pit_segmentation_gate_runner import (
    run_v5h_market_cap_pit_segmentation_gate,
)


class V5hMarketCapPitSegmentationGateRunnerTest(unittest.TestCase):
    def test_runner_builds_pit_market_cap_panel_and_keeps_mainline_unchanged(self) -> None:
        summary = run_v5h_market_cap_pit_segmentation_gate(Path("."))

        self.assertEqual(summary["status"], "completed_market_cap_pit_segmentation_gate")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "market_cap_segmentation_diagnostic_positive_needs_independent_validation",
                "market_cap_segmentation_diagnostic_only_no_incremental_edge",
                "market_cap_segmentation_blocked_by_pit_data",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["sell_rules_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertGreater(summary["market_cap_panel_rows"], 0)

        out = Path("v5h_market_cap_pit_segmentation_gate") / "current"
        for name in [
            "v5h_market_cap_pit_segmentation_summary.json",
            "v5h_market_cap_pit_segmentation_report.md",
            "v5h_market_cap_source_audit.csv",
            "v5h_pit_market_cap_panel.csv",
            "v5h_market_cap_coverage_by_sleeve.csv",
            "v5h_market_cap_segmented_order_panel.csv",
            "v5h_market_cap_segment_result.csv",
            "v5h_market_cap_segmentation_variant_metrics.csv",
            "v5h_market_cap_segmentation_data_gate.csv",
            "v5h_market_cap_segmentation_governance_audit.csv",
            "v5h_market_cap_segmentation_pm_gate_decision.csv",
            "v5h_market_cap_segmentation_next_queue.csv",
            "v5h_market_cap_pit_segmentation_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_market_cap_segmentation_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            governance = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5h_market_cap_segmentation_data_gate.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            gate = {row["gate_id"]: row for row in csv.DictReader(handle)}
        self.assertIn(gate["total_market_cap_coverage"]["status"], {"pass", "fail"})
        self.assertIn(gate["free_float_market_cap_coverage"]["status"], {"pass", "warn"})

        with (out / "v5h_market_cap_segmentation_variant_metrics.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            metrics = list(csv.DictReader(handle))
        self.assertTrue(any(row["version_id"] == "v5h_spec_v1_global_reference" for row in metrics))
        self.assertTrue(all(row["accepted"] == "False" for row in metrics))


if __name__ == "__main__":
    unittest.main()
