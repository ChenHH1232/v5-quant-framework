from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_full_holding_rolling_intraday_research_runner import run_v5e_full_holding_rolling_intraday_research


class V5eFullHoldingRollingIntradayResearchRunnerTest(unittest.TestCase):
    def test_runner_promotes_rolling_research_candidate_without_acceptance(self) -> None:
        summary = run_v5e_full_holding_rolling_intraday_research(Path("."))

        self.assertEqual(summary["status"], "completed_full_holding_rolling_intraday_research")
        self.assertEqual(summary["pm_gate_decision"], "promote_full_intraday_rolling_candidate_to_nav_engineering_not_accepted")
        self.assertGreater(summary["event_count"], 0)
        self.assertGreater(summary["best_static_incremental_return_pct_points"], 0)
        self.assertGreater(summary["rolling_oos_incremental_return_pct_points"], 0)
        self.assertEqual(summary["full_5min_effective_coverage_rate_pct"], 100.0)
        self.assertTrue(summary["uses_5min_trigger"])
        self.assertTrue(summary["rolling_selection_used"])
        self.assertFalse(summary["future_information_used_for_selection"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertEqual(summary["fatal_blocker_count"], 0)


if __name__ == "__main__":
    unittest.main()
