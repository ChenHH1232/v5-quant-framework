from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_locked_pool_conditional_momentum_runner import run_v5f_locked_pool_conditional_momentum


class V5fLockedPoolConditionalMomentumRunnerTest(unittest.TestCase):
    def test_runner_completes_conditional_variants_without_acceptance(self) -> None:
        summary = run_v5f_locked_pool_conditional_momentum(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_locked_pool_conditional_momentum")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "promote_conditional_locked_pool_momentum_to_forward_paper_candidate_not_accepted",
                "risk_warning_diagnostic_positive_no_trade_change",
                "conditional_momentum_diagnostic_only_keep_fixed_7030_primary",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_locked_pool_conditional_momentum") / "current"
        for name in [
            "v5f_locked_pool_conditional_momentum_summary.json",
            "v5f_locked_pool_conditional_momentum_prompt.md",
            "v5f_locked_pool_conditional_momentum_report.md",
            "v5f_locked_pool_conditional_momentum_metrics.csv",
            "v5f_locked_pool_conditional_momentum_comparison.csv",
            "v5f_locked_pool_conditional_momentum_update_events.csv",
            "v5f_locked_pool_conditional_momentum_update_summary.csv",
            "v5f_locked_pool_risk_warning_events.csv",
            "v5f_locked_pool_risk_warning_summary.csv",
            "v5f_locked_pool_conditional_momentum_governance_audit.csv",
            "v5f_locked_pool_conditional_momentum_pm_decision.csv",
            "v5f_locked_pool_conditional_momentum_next_queue.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_locked_pool_conditional_momentum_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_locked_pool_conditional_momentum_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        for version in [
            "internal_subsleeve_mom12_70_30_rebalance_only",
            "locked_pool_biweekly_mom12_70_30",
            "locked_pool_monthly_mom12_70_30",
            "locked_pool_major_bucket_change_mom12_70_30",
            "locked_pool_weight_drift_1pct_mom12_70_30",
            "locked_pool_risk_warning_only_no_trade",
        ]:
            self.assertIn(version, rows)


if __name__ == "__main__":
    unittest.main()
