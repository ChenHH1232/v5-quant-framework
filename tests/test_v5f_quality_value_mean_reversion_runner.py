from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_quality_value_mean_reversion_runner import run_v5f_quality_value_mean_reversion


class V5fQualityValueMeanReversionRunnerTest(unittest.TestCase):
    def test_runner_tests_quality_value_reversion_without_acceptance(self) -> None:
        summary = run_v5f_quality_value_mean_reversion(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_quality_value_mean_reversion")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "promote_qv_mean_reversion_to_pm_quant_review_not_accepted",
                "qv_mean_reversion_positive_but_insufficient_keep_champion_primary",
                "qv_mean_reversion_diagnostic_only_keep_champion_primary",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_quality_value_mean_reversion") / "current"
        for name in [
            "v5f_qv_mean_reversion_summary.json",
            "v5f_qv_mean_reversion_prompt.md",
            "v5f_qv_mean_reversion_report.md",
            "v5f_qv_mean_reversion_metrics.csv",
            "v5f_qv_mean_reversion_comparison.csv",
            "v5f_qv_mean_reversion_selection_concentration.csv",
            "v5f_qv_mean_reversion_governance_audit.csv",
            "v5f_qv_mean_reversion_pm_decision.csv",
            "v5f_qv_mean_reversion_next_queue.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_qv_mean_reversion_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_qv_mean_reversion_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        for version in [
            "internal_subsleeve_mom12_70_30_current_champion",
            "qv_score_only_70_30",
            "qv_mr_20d_rebalance_70_30",
            "qv_mr_60d_rebalance_70_30",
            "qv_mr_120d_rebalance_70_30",
            "qv_mr_60d_tilt10_rebalance",
            "qv_mr_60d_monthly_70_30",
        ]:
            self.assertIn(version, rows)


if __name__ == "__main__":
    unittest.main()
