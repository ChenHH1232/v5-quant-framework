from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5f_1min_microstructure_signal_quality_gate_runner import (
    run_v5f_1min_microstructure_signal_quality_gate,
)


class V5f1minMicrostructureSignalQualityGateRunnerTest(unittest.TestCase):
    def test_runner_builds_1min_signal_quality_gate_without_frequency_change(self) -> None:
        summary = run_v5f_1min_microstructure_signal_quality_gate(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_1min_microstructure_signal_quality_gate")
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "one_minute_quality_gate_pass_for_diagnostic_precision_not_trading",
                "one_minute_quality_gate_pass_vwap_precision_review_needed_not_trading",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["diagnosed_event_count"], 0)

        out = Path("v5f_1min_microstructure_signal_quality_gate") / "current"
        for name in [
            "v5f_1min_microstructure_summary.json",
            "v5f_1min_microstructure_report.md",
            "v5f_1min_microstructure_signal_quality_spec.csv",
            "v5f_1min_microstructure_data_gate.csv",
            "v5f_1min_event_coverage_audit.csv",
            "v5f_1min_file_read_audit.csv",
            "v5f_1min_event_path_diagnostics.csv",
            "v5f_1min_event_type_quality_summary.csv",
            "v5f_1min_vwap_precision_diagnostics.csv",
            "v5f_1min_execution_path_diagnostics.csv",
            "v5f_1min_quality_filter_recommendation.csv",
            "v5f_1min_pit_governance_audit.csv",
            "v5f_1min_pm_gate_decision.csv",
            "v5f_1min_next_agent_queue.csv",
            "v5f_1min_blockers.csv",
            "v5f_1min_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_1min_pit_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            audit = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_1min_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            decision = list(csv.DictReader(handle))[0]
        self.assertEqual(decision["trading_frequency_increased"], "False")
        self.assertEqual(decision["accepted"], "False")


if __name__ == "__main__":
    unittest.main()
