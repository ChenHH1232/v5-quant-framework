from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_sleeve_level_risk_release_limited_engineering_runner import (
    run_v5e_sleeve_level_risk_release_limited_engineering,
)


class V5eSleeveLevelRiskReleaseLimitedEngineeringRunnerTest(unittest.TestCase):
    def test_runner_keeps_sleeve_level_diagnostic_without_acceptance(self) -> None:
        summary = run_v5e_sleeve_level_risk_release_limited_engineering(Path("."))

        self.assertEqual(summary["status"], "completed_sleeve_level_risk_release_limited_engineering")
        self.assertEqual(summary["pm_gate_decision"], "remain_diagnostic_sleeve_level_release")
        self.assertEqual(summary["best_version_id"], "sleeve_level_daily_profit_release_main")
        self.assertLess(abs(summary["best_delta_return_vs_v57f"]), 0.001)
        self.assertLess(summary["best_delta_return_vs_hold_cash"], 0)
        self.assertLess(summary["best_delta_max_drawdown_vs_v57f"], 0)
        self.assertGreater(summary["trigger_count"], 0)
        self.assertEqual(summary["execution_price_policy"], "daily_close_proxy_diagnostic")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_sleeve_level_risk_release_limited_engineering") / "current"
        self.assertTrue((out / "v5e_sleeve_level_release_summary.json").exists())
        self.assertTrue((out / "v5e_sleeve_level_release_variant_metrics.csv").exists())
        self.assertTrue((out / "v5e_sleeve_level_release_next_prompt.md").exists())


if __name__ == "__main__":
    unittest.main()
