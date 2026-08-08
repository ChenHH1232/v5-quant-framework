from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_extreme_value_reversion_runner import run_v5f_extreme_value_reversion


class V5fExtremeValueReversionRunnerTest(unittest.TestCase):
    def test_runner_tests_extreme_value_repair_without_acceptance(self) -> None:
        summary = run_v5f_extreme_value_reversion(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_extreme_value_reversion")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "extreme_value_reversion_positive_ready_for_pm_quant_review_not_accepted",
                "extreme_value_reversion_positive_but_insufficient_keep_momentum_primary",
                "extreme_value_reversion_diagnostic_only_keep_momentum_primary",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_extreme_value_reversion") / "current"
        for name in [
            "v5f_extreme_value_reversion_summary.json",
            "v5f_extreme_value_reversion_report.md",
            "v5f_extreme_value_reversion_metrics.csv",
            "v5f_extreme_value_reversion_comparison.csv",
            "v5f_extreme_value_reversion_candidate_events.csv",
            "v5f_extreme_value_reversion_fundamental_attribution.csv",
            "v5f_extreme_value_reversion_data_gate.csv",
            "v5f_extreme_value_reversion_governance_audit.csv",
            "v5f_extreme_value_reversion_pit_audit.csv",
            "v5f_extreme_value_reversion_pm_decision.csv",
            "v5f_extreme_value_reversion_next_queue.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_extreme_value_reversion_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_extreme_value_reversion_comparison.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        for version in [
            "internal_subsleeve_mom12_70_30_current_champion",
            "extreme_60d_value_repair_70_30",
            "extreme_120d_value_repair_70_30",
            "core70_mom20_extreme60_10",
            "core80_mom10_extreme60_10",
        ]:
            self.assertIn(version, rows)


if __name__ == "__main__":
    unittest.main()
