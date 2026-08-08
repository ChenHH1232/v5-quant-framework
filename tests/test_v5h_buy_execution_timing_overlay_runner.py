from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_buy_execution_timing_overlay_runner import (
    run_v5h_buy_execution_timing_overlay,
)


class V5hBuyExecutionTimingOverlayRunnerTest(unittest.TestCase):
    def test_runner_builds_buy_timing_overlay_without_trading_policy_change(self) -> None:
        summary = run_v5h_buy_execution_timing_overlay(Path("."))

        self.assertEqual(summary["status"], "completed_v5h_buy_execution_timing_overlay")
        self.assertEqual(summary["v5h_line_id"], "v5h_1min_microstructure_execution_research")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "v5h_buy_execution_overlay_positive_ready_for_quant_spec_not_trading",
                "v5h_buy_execution_overlay_diagnostic_only_no_material_edge",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["sell_rules_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["scheduled_buy_intent_count"], 0)
        self.assertGreater(summary["mean_reversion_buy_event_count"], 0)

        out = Path("v5h_buy_execution_timing_overlay") / "current"
        for name in [
            "v5h_buy_execution_timing_overlay_summary.json",
            "v5h_buy_execution_timing_overlay_report.md",
            "v5h_buy_execution_timing_overlay_spec.csv",
            "v5h_buy_execution_timing_order_decision_log.csv",
            "v5h_buy_execution_timing_variant_metrics.csv",
            "v5h_buy_execution_timing_variant_comparison.csv",
            "v5h_buy_execution_timing_by_family.csv",
            "v5h_buy_execution_timing_by_sleeve.csv",
            "v5h_buy_execution_timing_data_gate.csv",
            "v5h_buy_execution_timing_governance_audit.csv",
            "v5h_buy_execution_timing_pm_gate_decision.csv",
            "v5h_buy_execution_timing_next_agent_queue.csv",
            "v5h_buy_execution_timing_blockers.csv",
            "v5h_buy_execution_timing_v5h_line_mapping.csv",
            "v5h_buy_execution_timing_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_buy_execution_timing_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            audit = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5h_buy_execution_timing_variant_comparison.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            comparison = list(csv.DictReader(handle))
        self.assertTrue(any(row["variant_id"] == "combined_v5h_buy_execution_overlay_v1" for row in comparison))
        self.assertTrue(all(row["accepted"] == "False" for row in comparison))
        self.assertTrue(all(row["trading_frequency_change_allowed"] == "False" for row in comparison))
        self.assertTrue(all(row["comparison_scope"] for row in comparison))

        combined = next(row for row in comparison if row["variant_id"] == "combined_v5h_buy_execution_overlay_v1")
        self.assertEqual(combined["comparison_scope"], "all_orders")
        self.assertIn("comparable_incremental_decision_edge_vs_baseline", combined)


if __name__ == "__main__":
    unittest.main()
