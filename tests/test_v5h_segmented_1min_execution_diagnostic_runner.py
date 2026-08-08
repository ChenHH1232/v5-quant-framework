from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_segmented_1min_execution_diagnostic_runner import (
    run_v5h_segmented_1min_execution_diagnostic,
)


class V5hSegmented1minExecutionDiagnosticRunnerTest(unittest.TestCase):
    def test_runner_segments_1min_execution_without_promoting_backtest_selected_rules(self) -> None:
        summary = run_v5h_segmented_1min_execution_diagnostic(Path("."))

        self.assertEqual(summary["status"], "completed_v5h_segmented_1min_execution_diagnostic")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "segmented_1min_execution_diagnostic_positive_needs_pre2021_or_forward_validation",
                "segmented_1min_execution_no_improvement_over_global_v1",
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
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["order_count"], 0)

        out = Path("v5h_segmented_1min_execution_diagnostic") / "current"
        for name in [
            "v5h_segmented_execution_summary.json",
            "v5h_segmented_execution_report.md",
            "v5h_segmented_execution_order_panel.csv",
            "v5h_segmented_execution_by_sleeve.csv",
            "v5h_segmented_execution_by_10am_liquidity.csv",
            "v5h_segmented_execution_by_10am_zone.csv",
            "v5h_segmented_execution_by_sleeve_liquidity.csv",
            "v5h_segmented_execution_variant_rule_spec.csv",
            "v5h_segmented_execution_variant_metrics.csv",
            "v5h_segmented_execution_candidate_matrix.csv",
            "v5h_segmented_execution_market_cap_data_gate.csv",
            "v5h_segmented_execution_data_gate.csv",
            "v5h_segmented_execution_governance_audit.csv",
            "v5h_segmented_execution_pm_gate_decision.csv",
            "v5h_segmented_execution_next_agent_queue.csv",
            "v5h_segmented_execution_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_segmented_execution_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            governance = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5h_segmented_execution_candidate_matrix.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            candidates = list(csv.DictReader(handle))
        self.assertTrue(any(row["candidate_id"] == "v5h_segment_liquidity_quiet_or_active_diagnostic" for row in candidates))
        self.assertTrue(all(row["accepted"] == "False" for row in candidates))
        self.assertTrue(
            any(row["selected_from_backtest_segments"] == "True" for row in candidates),
            "segmented variants must be labelled as backtest-selected diagnostics",
        )

        with (out / "v5h_segmented_execution_market_cap_data_gate.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            market_cap_gate = list(csv.DictReader(handle))[0]
        self.assertEqual(market_cap_gate["fatal"], "False")


if __name__ == "__main__":
    unittest.main()
