from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_full_intraday_nav_engineering_runner import run_v5e_full_intraday_nav_engineering


class V5eFullIntradayNavEngineeringRunnerTest(unittest.TestCase):
    def test_runner_downgrades_full_intraday_nav_to_diagnostic(self) -> None:
        summary = run_v5e_full_intraday_nav_engineering(Path("."))

        self.assertEqual(summary["status"], "completed_full_intraday_nav_engineering_test")
        self.assertEqual(summary["pm_gate_decision"], "downgrade_full_intraday_to_diagnostic")
        self.assertLess(summary["rolling_delta_return_pct_points_vs_baseline"], 0)
        self.assertLess(summary["rolling_delta_max_drawdown_pct_points_vs_baseline"], 0)
        self.assertGreater(summary["selected_event_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["future_information_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)


if __name__ == "__main__":
    unittest.main()
