from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_trigger_day_5min_data_gate_runner import run_v5e_trigger_day_5min_data_gate


class V5eTriggerDay5minDataGateRunnerTest(unittest.TestCase):
    def test_runner_generates_trigger_day_only_fetch_queue(self) -> None:
        root = Path(".")
        summary = run_v5e_trigger_day_5min_data_gate(root)

        self.assertEqual(summary["status"], "completed_trigger_day_5min_execution_data_gate")
        self.assertEqual(summary["scope"], "trigger_day_execution_windows_only")
        self.assertFalse(summary["full_holding_period_checked"])
        self.assertFalse(summary["minute_data_used_for_trigger"])
        self.assertFalse(summary["engineering_backtest_run"])
        self.assertFalse(summary["baostock_network_fetch_started"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["exit_action_count"], 0)

        out = root / "v5e_trigger_day_5min_execution_data_gate" / "current"
        self.assertTrue((out / "v5e_exit_execution_window_requirement.csv").exists())
        self.assertTrue((out / "v5e_exit_5min_coverage_audit.csv").exists())
        self.assertTrue((out / "v5e_exit_5min_fetch_queue.csv").exists())

        with (out / "v5e_exit_5min_fetch_plan.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["full_holding_period_fetch"], "False")
        self.assertEqual(rows[0]["source_preference"], "BaoStock 5min")


if __name__ == "__main__":
    unittest.main()
