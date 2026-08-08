from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_p0_local_data_gate_runner import run_v5c_p0_local_data_gate


class V5cP0LocalDataGateRunnerTest(unittest.TestCase):
    def test_runner_builds_p0_truth_tables_from_repaired_baseline(self) -> None:
        summary = run_v5c_p0_local_data_gate(Path("."))

        self.assertEqual(summary["status"], "completed_p0_local_data_gate")
        self.assertEqual(summary["pm_gate_decision"], "p0_local_data_gate_pass_ready_for_p1_p2")
        self.assertTrue(summary["p0_pass"])
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired")
        self.assertEqual(summary["first_signal_date"], "2021-05-06")
        self.assertEqual(summary["first_trade_date"], "2021-05-06")
        self.assertGreater(summary["daily_row_count"], 0)
        self.assertGreater(summary["rebalance_count"], 0)
        self.assertGreater(summary["holding_snapshot_rows"], 0)
        self.assertGreater(summary["trade_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_strategy_rule_added"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5c_p0_local_data_gate") / "current"
        expected = [
            "v5c_p0_local_data_gate_summary.json",
            "v5c_p0_local_data_gate_report.md",
            "v5c_p0_source_manifest.csv",
            "v5c_p0_baseline_truth_table.csv",
            "v5c_p0_daily_nav_returns.csv",
            "v5c_p0_rebalance_calendar.csv",
            "v5c_p0_rebalance_holdings_targets.csv",
            "v5c_p0_sleeve_weight_snapshots.csv",
            "v5c_p0_daily_cash_ledger.csv",
            "v5c_p0_transaction_cost_model.csv",
            "v5c_p0_trade_cost_audit.csv",
            "v5c_p0_data_quality_audit.csv",
            "v5c_p0_next_data_gate_queue.csv",
            "v5c_p0_blockers.csv",
            "v5c_p0_pm_gate_decision.csv",
            "v5c_p0_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_p0_baseline_truth_table.csv").open("r", encoding="utf-8-sig", newline="") as f:
            truth = list(csv.DictReader(f))[0]
        self.assertEqual(truth["first_signal_date"], "2021-05-06")
        self.assertEqual(truth["first_trade_date"], "2021-05-06")
        self.assertEqual(truth["old_baseline_used"], "False")
        self.assertEqual(truth["startup_preload_repaired"], "True")

        with (out / "v5c_p0_data_quality_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audits = list(csv.DictReader(f))
        self.assertTrue(audits)
        self.assertTrue(all(row["status"] == "pass" for row in audits))

        with (out / "v5c_p0_next_data_gate_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_gate"]: row for row in csv.DictReader(f)}
        self.assertIn("v5c_p1_financial_quality_pit_panel", queue)
        self.assertIn("v5c_p2_valuation_and_crowding_state_panel", queue)


if __name__ == "__main__":
    unittest.main()
