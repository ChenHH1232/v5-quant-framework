from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_buy_execution_spec_v1_runner import run_v5h_buy_execution_spec_v1


class V5hBuyExecutionSpecV1RunnerTest(unittest.TestCase):
    def test_runner_freezes_buy_execution_spec_without_mainline_or_sell_change(self) -> None:
        summary = run_v5h_buy_execution_spec_v1(Path("."))

        self.assertEqual(summary["status"], "completed_v5h_buy_execution_spec_v1_frozen")
        self.assertEqual(summary["v5h_line_id"], "v5h_1min_microstructure_execution_research")
        self.assertEqual(
            summary["pm_gate_decision"],
            "freeze_pressure_positive_1000_else_1400_buy_as_v5h_buy_execution_spec_v1_not_trading",
        )
        self.assertEqual(summary["frozen_variant"], "pressure_positive_1000_else_1400_buy")
        self.assertEqual(summary["combined_variant_status"], "observation_only_not_mainline")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertTrue(summary["buy_execution_spec_frozen"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["sell_rules_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["scheduled_buy_order_count"], 0)

        out = Path("v5h_buy_execution_spec_v1") / "current"
        for name in [
            "v5h_buy_execution_spec_v1_summary.json",
            "v5h_buy_execution_spec_v1_report.md",
            "v5h_buy_execution_spec_v1_frozen_rule_spec.csv",
            "v5h_buy_execution_spec_v1_execution_decision_matrix.csv",
            "v5h_buy_execution_spec_v1_signal_visibility_schema.csv",
            "v5h_buy_execution_spec_v1_applicable_order_scope.csv",
            "v5h_buy_execution_spec_v1_family_evidence.csv",
            "v5h_buy_execution_spec_v1_combined_observation_queue.csv",
            "v5h_buy_execution_spec_v1_data_gate.csv",
            "v5h_buy_execution_spec_v1_governance_audit.csv",
            "v5h_buy_execution_spec_v1_allowed_blocked_actions.csv",
            "v5h_buy_execution_spec_v1_pm_gate_decision.csv",
            "v5h_buy_execution_spec_v1_next_agent_queue.csv",
            "v5h_buy_execution_spec_v1_blockers.csv",
            "v5h_buy_execution_spec_v1_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_buy_execution_spec_v1_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            governance = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5h_buy_execution_spec_v1_frozen_rule_spec.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            spec = list(csv.DictReader(handle))[0]
        self.assertEqual(spec["frozen_variant"], "pressure_positive_1000_else_1400_buy")
        self.assertEqual(spec["order_scope"], "scheduled_buy_and_increase_orders_only")
        self.assertEqual(spec["sell_rules_modified"], "False")
        self.assertEqual(spec["trading_frequency_increased"], "False")
        self.assertEqual(spec["new_buy_signal_used"], "False")

        with (out / "v5h_buy_execution_spec_v1_combined_observation_queue.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            combined = list(csv.DictReader(handle))[0]
        self.assertEqual(combined["status"], "observation_only_not_mainline")
        self.assertEqual(combined["accepted"], "False")
        self.assertEqual(combined["mainline_modified"], "False")


if __name__ == "__main__":
    unittest.main()
