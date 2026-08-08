from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.pre2021_financial_expectation_panel_extension_runner import (
    FORMAL_BACKTEST_START,
    OUT_DIR,
    run_pre2021_financial_expectation_panel_extension,
)


class Pre2021FinancialExpectationPanelExtensionRunnerTest(unittest.TestCase):
    def test_runner_replays_pre2021_without_opening_weight_engineering(self) -> None:
        summary = run_pre2021_financial_expectation_panel_extension(Path("."))

        self.assertEqual(summary["status"], "completed_pre2021_financial_expectation_panel_extension")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "pre2021_expectation_extension_diagnostic_only",
                "pre2021_expectation_extension_supportive_observation_not_trading",
            },
        )
        self.assertGreater(summary["expectation_rows"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_primary_modified"])
        self.assertFalse(summary["trade_rule_added"])
        self.assertFalse(summary["weight_change_added"])
        self.assertFalse(summary["formal_backtest_used_as_validation"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertEqual(summary["v5f_weight_confidence_spec_status"], "still_blocked")

        out = Path(".") / OUT_DIR
        expected = [
            "pre2021_financial_expectation_summary.json",
            "pre2021_financial_expectation_report.md",
            "pre2021_financial_expectation_historical_panel.csv",
            "pre2021_financial_expectation_accuracy_audit.csv",
            "pre2021_financial_expectation_sample_split_audit.csv",
            "pre2021_v5f_weight_confidence_freeze_decision.csv",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "pre2021_financial_expectation_historical_panel.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(rows)
        self.assertLess(max(row["trade_date"] for row in rows), FORMAL_BACKTEST_START)
        self.assertTrue(all(row["trade_impact"] == "none" for row in rows))
        self.assertTrue(all(row["weight_impact"] == "none" for row in rows))


if __name__ == "__main__":
    unittest.main()
