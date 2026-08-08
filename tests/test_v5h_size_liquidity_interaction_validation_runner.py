from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_size_liquidity_interaction_validation_runner import (
    run_v5h_size_liquidity_interaction_validation,
)


class V5hSizeLiquidityInteractionValidationRunnerTest(unittest.TestCase):
    def test_runner_builds_interaction_packet_without_changing_mainline(self) -> None:
        summary = run_v5h_size_liquidity_interaction_validation(Path("."))

        self.assertEqual(summary["status"], "completed_size_liquidity_interaction_validation")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "size_liquidity_interaction_positive_ready_for_forward_observation_not_accepted",
                "size_liquidity_interaction_formal_positive_but_independent_unconfirmed",
                "size_liquidity_interaction_no_incremental_edge_over_global_v1",
                "blocked_by_data_or_governance_issue",
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
        self.assertFalse(summary["free_float_market_cap_used"])
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertGreater(summary["formal_order_count"], 0)
        self.assertGreater(summary["pre2021_order_count"], 0)

        out = Path("v5h_size_liquidity_interaction_independent_validation") / "current"
        for name in [
            "v5h_size_liquidity_interaction_summary.json",
            "v5h_size_liquidity_interaction_report.md",
            "v5h_size_liquidity_formal_order_panel.csv",
            "v5h_size_liquidity_formal_interaction_segment_result.csv",
            "v5h_size_liquidity_formal_variant_metrics.csv",
            "v5h_size_liquidity_pre2021_order_panel.csv",
            "v5h_size_liquidity_pre2021_market_cap_source_audit.csv",
            "v5h_size_liquidity_pre2021_variant_metrics.csv",
            "v5h_size_liquidity_interaction_data_gate.csv",
            "v5h_size_liquidity_interaction_governance_audit.csv",
            "v5h_size_liquidity_interaction_pm_gate_decision.csv",
            "v5h_size_liquidity_interaction_next_queue.csv",
            "v5h_size_liquidity_interaction_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_size_liquidity_interaction_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            governance = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5h_size_liquidity_interaction_data_gate.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            gates = {row["gate_id"]: row for row in csv.DictReader(handle)}
        self.assertEqual(gates["formal_total_market_cap_coverage"]["status"], "pass")
        self.assertIn(gates["pre2021_market_cap_primary_coverage"]["status"], {"pass", "warn"})


if __name__ == "__main__":
    unittest.main()
