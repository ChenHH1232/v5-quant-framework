from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_locked_pool_daily_momentum_governance_runner import (
    run_v5f_locked_pool_daily_momentum_governance,
)


class V5fLockedPoolDailyMomentumGovernanceRunnerTest(unittest.TestCase):
    def test_runner_completes_locked_pool_daily_momentum_without_acceptance(self) -> None:
        summary = run_v5f_locked_pool_daily_momentum_governance(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_locked_pool_daily_momentum_governance")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "promote_locked_pool_daily_momentum_to_forward_paper_candidate_not_accepted",
                "weekly_locked_pool_momentum_positive_daily_diagnostic",
                "daily_locked_pool_momentum_diagnostic_only_keep_rebalance_7030_primary",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_locked_pool_daily_momentum_governance") / "current"
        for name in [
            "v5f_locked_pool_daily_momentum_summary.json",
            "v5f_locked_pool_daily_momentum_prompt.md",
            "v5f_locked_pool_daily_momentum_report.md",
            "v5f_locked_pool_daily_momentum_metrics.csv",
            "v5f_locked_pool_daily_momentum_comparison.csv",
            "v5f_locked_pool_daily_momentum_governance_audit.csv",
            "v5f_locked_pool_daily_momentum_pit_audit.csv",
            "v5f_locked_pool_daily_momentum_pm_decision.csv",
            "v5f_locked_pool_daily_momentum_next_queue.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_locked_pool_daily_momentum_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_locked_pool_daily_momentum_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        self.assertIn("locked_pool_daily_mom12_70_30", rows)
        self.assertIn("locked_pool_weekly_mom12_70_30", rows)
        self.assertIn("internal_subsleeve_mom12_70_30_rebalance_only", rows)


if __name__ == "__main__":
    unittest.main()
