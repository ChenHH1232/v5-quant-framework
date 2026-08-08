from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5g_next_queue_execution_runner import run_v5g_next_queue_execution


class V5gNextQueueExecutionRunnerTest(unittest.TestCase):
    def test_runner_executes_five_v5g_gates_without_backtest_or_acceptance(self) -> None:
        summary = run_v5g_next_queue_execution(Path("."))

        self.assertEqual(summary["status"], "completed_v5g_next_queue_execution")
        self.assertEqual(summary["pm_gate_decision"], "v5g_next_queue_completed_specs_and_gates_not_backtest")
        self.assertEqual(summary["completed_gate_count"], 5)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        root_out = Path("v5g_next_queue_execution") / "current"
        expected_root = [
            "v5g_next_queue_execution_summary.json",
            "v5g_next_queue_execution_report.md",
            "v5g_next_queue_status.csv",
            "v5g_next_queue_pm_gate_decision.csv",
            "v5g_next_queue_blockers.csv",
        ]
        for name in expected_root:
            self.assertTrue((root_out / name).exists(), name)

        with (root_out / "v5g_next_queue_status.csv").open("r", encoding="utf-8-sig", newline="") as f:
            status_rows = list(csv.DictReader(f))
        self.assertEqual(len(status_rows), 5)
        self.assertTrue(all(row["accepted"] == "False" for row in status_rows))
        self.assertTrue(all(row["engineering_backtest_started"] == "False" for row in status_rows))

        out_01 = Path("v5g_01_state_gated_internal_subsleeve_quant_spec") / "current"
        out_02 = Path("v5g_02_quality_guarded_momentum_factor_validation") / "current"
        out_03 = Path("v5g_03_erc_state_budget_conflict_review") / "current"
        out_04 = Path("v5g_04_cash_proxy_policy_data_gate") / "current"
        out_05 = Path("v5g_05_short_window_reversion_independent_validation_gate") / "current"

        expected_outputs = [
            out_01 / "v5g_01_state_gated_quant_spec_summary.json",
            out_01 / "v5g_01_state_gate_rule_spec.csv",
            out_01 / "v5g_01_state_gate_event_queue.csv",
            out_02 / "v5g_02_quality_factor_validation_summary.json",
            out_02 / "v5g_02_quality_factor_features.csv",
            out_02 / "v5g_02_quality_factor_ic.csv",
            out_02 / "v5g_02_quality_factor_quantile_spread.csv",
            out_03 / "v5g_03_erc_conflict_review_summary.json",
            out_03 / "v5g_03_erc_conflict_matrix.csv",
            out_04 / "v5g_04_cash_proxy_policy_data_gate_summary.json",
            out_04 / "v5g_04_cash_proxy_policy_matrix.csv",
            out_05 / "v5g_05_short_window_validation_gate_summary.json",
            out_05 / "v5g_05_independent_validation_audit.csv",
            out_05 / "v5g_05_validation_gap_register.csv",
        ]
        for path in expected_outputs:
            self.assertTrue(path.exists(), str(path))

        with (out_01 / "v5g_01_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            gate_01 = list(csv.DictReader(f))[0]
        self.assertEqual(gate_01["pm_gate_decision"], "v5g_01_quant_spec_pass_ready_for_limited_engineering_approval_not_backtest")
        self.assertEqual(gate_01["admit_limited_engineering_now"], "False")
        self.assertEqual(gate_01["admit_trading_rule"], "False")

        with (out_02 / "v5g_02_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            gate_02 = list(csv.DictReader(f))[0]
        self.assertEqual(gate_02["pm_gate_decision"], "v5g_02_quality_factor_diagnostic_only_not_engineering")
        self.assertEqual(gate_02["factor_validation_pass"], "False")
        self.assertEqual(gate_02["admit_engineering_backtest_now"], "False")

        with (out_05 / "v5g_05_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            gate_05 = list(csv.DictReader(f))[0]
        self.assertEqual(gate_05["pm_gate_decision"], "v5g_05_independent_validation_gate_blocks_promotion_keep_diagnostic")
        self.assertEqual(gate_05["independent_validation_pass"], "False")
        self.assertEqual(gate_05["admit_engineering_backtest_now"], "False")
        self.assertEqual(gate_05["accepted"], "False")


if __name__ == "__main__":
    unittest.main()
