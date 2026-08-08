from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5f_1min_queue_123_runner import run_v5f_1min_queue_123


class V5f1minQueue123RunnerTest(unittest.TestCase):
    def test_runner_executes_three_1min_followup_queues_without_trading_change(self) -> None:
        summary = run_v5f_1min_queue_123(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_1min_queue_123_execution")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["vwap_event_count"], 0)
        self.assertGreater(summary["forward_stock_day_count"], 0)

        expected = {
            Path("v5f_1min_vwap_execution_precision_audit") / "current": [
                "v5f_1min_vwap_precision_summary.json",
                "v5f_1min_vwap_event_precision_audit.csv",
                "v5f_1min_vwap_pm_gate_decision.csv",
            ],
            Path("v5f_spike_mr_signal_quality_filter_spec") / "current": [
                "v5f_spike_mr_signal_quality_filter_summary.json",
                "v5f_spike_mr_event_type_quality_matrix.csv",
                "v5f_spike_mr_pm_gate_decision.csv",
            ],
            Path("v5f_1min_forward_observation_append") / "current": [
                "v5f_1min_forward_observation_summary.json",
                "v5f_1min_forward_observation_feature_panel.csv",
                "v5f_1min_forward_observation_event_log.csv",
                "v5f_1min_forward_pm_gate_decision.csv",
            ],
            Path("v5f_1min_queue_123_execution") / "current": [
                "v5f_1min_queue_123_summary.json",
                "v5f_1min_queue_123_child_summary.csv",
                "v5f_1min_queue_123_pm_gate_decision.csv",
            ],
        }
        for directory, names in expected.items():
            for name in names:
                self.assertTrue((directory / name).exists(), f"{directory / name}")

        for path in [
            Path("v5f_1min_vwap_execution_precision_audit/current/v5f_1min_vwap_pm_gate_decision.csv"),
            Path("v5f_spike_mr_signal_quality_filter_spec/current/v5f_spike_mr_pm_gate_decision.csv"),
            Path("v5f_1min_forward_observation_append/current/v5f_1min_forward_pm_gate_decision.csv"),
        ]:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                decision = list(csv.DictReader(handle))[0]
            self.assertEqual(decision["accepted"], "False")
            self.assertEqual(decision["trading_frequency_increased"], "False")
            self.assertEqual(decision["v57f_core_modified"], "False")


if __name__ == "__main__":
    unittest.main()
