from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_full_holding_5min_data_gate_runner import run_v5e_full_holding_5min_data_gate


class V5eFullHolding5minDataGateRunnerTest(unittest.TestCase):
    def test_runner_confirms_full_holding_coverage_without_refetch(self) -> None:
        summary = run_v5e_full_holding_5min_data_gate(Path("."), fetch=False)

        self.assertEqual(summary["status"], "completed_full_holding_5min_data_gate")
        self.assertEqual(summary["scope"], "full_holding_period_5min")
        self.assertGreater(summary["required_stock_dates"], 0)
        self.assertEqual(summary["missing_stock_dates"], 0)
        self.assertEqual(summary["effective_coverage_rate_pct"], 100.0)
        self.assertFalse(summary["minute_data_used_for_trigger"])
        self.assertTrue(summary["rolling_research_required"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)


if __name__ == "__main__":
    unittest.main()
