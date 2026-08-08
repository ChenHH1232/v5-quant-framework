from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_v57f_qv_mr_combination_runner import run_v5f_v57f_qv_mr_combination


class V5fV57fQvMrCombinationRunnerTest(unittest.TestCase):
    def test_runner_tests_qv_mr_satellite_without_acceptance(self) -> None:
        summary = run_v5f_v57f_qv_mr_combination(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_v57f_qv_mr_combination")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "promote_v57f_mom_qv_mr_combo_to_pm_quant_review_not_accepted",
                "combo_positive_but_insufficient_keep_momentum_primary",
                "combo_diagnostic_only_keep_momentum_primary",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_v57f_qv_mr_combination") / "current"
        for name in [
            "v5f_v57f_qv_mr_combination_summary.json",
            "v5f_v57f_qv_mr_combination_prompt.md",
            "v5f_v57f_qv_mr_combination_report.md",
            "v5f_v57f_qv_mr_combination_metrics.csv",
            "v5f_v57f_qv_mr_combination_comparison.csv",
            "v5f_v57f_qv_mr_combination_governance_audit.csv",
            "v5f_v57f_qv_mr_combination_pit_audit.csv",
            "v5f_v57f_qv_mr_combination_pm_decision.csv",
            "v5f_v57f_qv_mr_combination_next_queue.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_v57f_qv_mr_combination_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_v57f_qv_mr_combination_comparison.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        for version in [
            "v5f_mom12_70_30_reference",
            "v5f_qv_mr60_70_30_reference",
            "v57f_core70_mom20_qv_mr10",
            "v57f_core70_mom15_qv_mr15",
            "v57f_core80_mom10_qv_mr10",
        ]:
            self.assertIn(version, rows)


if __name__ == "__main__":
    unittest.main()
