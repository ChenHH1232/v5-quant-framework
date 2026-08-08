from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_buy_execution_queue_123_runner import run_v5h_buy_execution_queue_123


class V5hBuyExecutionQueue123RunnerTest(unittest.TestCase):
    def test_runner_executes_forward_mapping_and_combined_observation_without_mainline_change(self) -> None:
        summary = run_v5h_buy_execution_queue_123(Path("."))

        self.assertEqual(summary["status"], "completed_v5h_buy_execution_queue_123")
        self.assertEqual(summary["frozen_variant"], "pressure_positive_1000_else_1400_buy")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["sell_rules_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["broker_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreaterEqual(summary["source_forward_stock_day_count"], 0)

        expected = {
            Path("v5h_buy_execution_spec_v1_forward_observation") / "current": [
                "v5h_buy_execution_v1_forward_observation_summary.json",
                "v5h_buy_execution_v1_forward_target_readiness.csv",
                "v5h_buy_execution_v1_forward_planned_buy_observation_rows.csv",
                "v5h_buy_execution_v1_forward_data_boundary.csv",
                "v5h_buy_execution_v1_forward_governance_audit.csv",
                "v5h_buy_execution_v1_forward_pm_gate_decision.csv",
            ],
            Path("v5h_buy_execution_spec_v1_jq_broker_paper_mapping") / "current": [
                "v5h_buy_execution_v1_jq_broker_mapping_summary.json",
                "v5h_buy_execution_v1_jq_broker_mapping.csv",
                "v5h_buy_execution_v1_paper_order_state_machine.csv",
                "v5h_buy_execution_v1_platform_data_contract.csv",
                "v5h_buy_execution_v1_jq_broker_pm_gate_decision.csv",
            ],
            Path("v5h_combined_buy_execution_overlay_v1_observation") / "current": [
                "v5h_combined_buy_execution_observation_summary.json",
                "v5h_combined_buy_execution_component_evidence.csv",
                "v5h_combined_buy_execution_observation_spec.csv",
                "v5h_combined_buy_execution_governance_audit.csv",
                "v5h_combined_buy_execution_pm_gate_decision.csv",
            ],
            Path("v5h_buy_execution_queue_123") / "current": [
                "v5h_buy_execution_queue_123_summary.json",
                "v5h_buy_execution_queue_123_child_summary.csv",
                "v5h_buy_execution_queue_123_pm_gate_decision.csv",
                "v5h_buy_execution_queue_123_next_agent_queue.csv",
            ],
        }
        for directory, names in expected.items():
            for name in names:
                self.assertTrue((directory / name).exists(), f"{directory / name}")

        for path in [
            Path("v5h_buy_execution_spec_v1_forward_observation/current/v5h_buy_execution_v1_forward_governance_audit.csv"),
            Path("v5h_buy_execution_spec_v1_jq_broker_paper_mapping/current/v5h_buy_execution_v1_jq_broker_governance_audit.csv"),
            Path("v5h_combined_buy_execution_overlay_v1_observation/current/v5h_combined_buy_execution_governance_audit.csv"),
        ]:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                audit = list(csv.DictReader(handle))
            self.assertTrue(all(row["status"] == "pass" for row in audit))

        with Path(
            "v5h_buy_execution_spec_v1_forward_observation/current/v5h_buy_execution_v1_forward_pm_gate_decision.csv"
        ).open("r", encoding="utf-8-sig", newline="") as handle:
            forward_decision = list(csv.DictReader(handle))[0]
        self.assertEqual(forward_decision["accepted"], "False")
        self.assertEqual(forward_decision["new_buy_signal_used"], "False")
        self.assertEqual(forward_decision["one_min_ohlcv_amount_available"], "True")
        self.assertEqual(forward_decision["order_book_available"], "False")
        self.assertEqual(forward_decision["bid_ask_available"], "False")
        self.assertEqual(forward_decision["active_buy_sell_flow_available"], "False")

        with Path(
            "v5h_buy_execution_spec_v1_forward_observation/current/v5h_buy_execution_v1_forward_observation_summary.json"
        ).open("r", encoding="utf-8-sig") as handle:
            forward_summary_text = handle.read()
        self.assertIn('"one_min_data_granularity": "ohlcv_amount_1min"', forward_summary_text)
        self.assertIn('"order_book_available": false', forward_summary_text)
        self.assertIn('"active_buy_sell_flow_available": false', forward_summary_text)

        with Path(
            "v5h_buy_execution_spec_v1_forward_observation/current/v5h_buy_execution_v1_forward_data_boundary.csv"
        ).open("r", encoding="utf-8-sig", newline="") as handle:
            data_boundary = {row["boundary_id"]: row for row in csv.DictReader(handle)}
        self.assertEqual(data_boundary["one_min_ohlcv_amount"]["available"], "True")
        self.assertEqual(data_boundary["bid_ask_quote"]["available"], "False")
        self.assertEqual(data_boundary["order_book_depth"]["available"], "False")
        self.assertEqual(data_boundary["tick_active_buy_sell_flow"]["available"], "False")

        with Path(
            "v5h_buy_execution_spec_v1_jq_broker_paper_mapping/current/v5h_buy_execution_v1_jq_broker_pm_gate_decision.csv"
        ).open("r", encoding="utf-8-sig", newline="") as handle:
            mapping_decision = list(csv.DictReader(handle))[0]
        self.assertEqual(mapping_decision["joinquant_started"], "False")
        self.assertEqual(mapping_decision["broker_started"], "False")
        self.assertEqual(mapping_decision["deployment_approved"], "False")

        with Path(
            "v5h_combined_buy_execution_overlay_v1_observation/current/v5h_combined_buy_execution_pm_gate_decision.csv"
        ).open("r", encoding="utf-8-sig", newline="") as handle:
            combined_decision = list(csv.DictReader(handle))[0]
        self.assertEqual(combined_decision["status"], "observation_only")
        self.assertEqual(combined_decision["v5f_mainline_modified"], "False")


if __name__ == "__main__":
    unittest.main()
