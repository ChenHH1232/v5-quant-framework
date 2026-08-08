from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_capital_sensitivity_runner import run_v5e_capital_sensitivity


class V5eCapitalSensitivityRunnerTest(unittest.TestCase):
    def test_runner_compares_fixed_capital_levels_without_acceptance(self) -> None:
        root = Path(".")
        summary = run_v5e_capital_sensitivity(root)

        self.assertEqual(summary["status"], "completed_capital_sensitivity_test")
        self.assertEqual(summary["pm_gate_decision"], "open_cash_policy_review")
        self.assertEqual(summary["capital_levels"], ["50w", "200w", "800w"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["minute_data_used_for_trigger"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertEqual(summary["minimum_efficient_capital_wanyi_28_names"], 1_400_000.0)
        self.assertEqual(summary["capital_efficiency_by_level"]["50w"], "below_min_commission_efficient_band")
        self.assertEqual(summary["capital_efficiency_by_level"]["200w"], "reasonable_200w_plus_band")

        out = root / "v5e_capital_sensitivity_test" / "current"
        with (out / "v5e_capital_level_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual({row["capital_level"] for row in rows}, {"50w", "200w", "800w"})
        self.assertIn("v5e_profit_lock_main_20pct_sell50", {row["version_id"] for row in rows})
        self.assertTrue((out / "v5e_capital_min_commission_efficiency.csv").exists())
        self.assertTrue((out / "v5e_capital_wanyi_commission_supplement.csv").exists())


if __name__ == "__main__":
    unittest.main()
