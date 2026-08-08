from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_momentum_weight_tilt_backtest_scope_runner import run_v5f_momentum_weight_tilt_backtest_scope


class V5fMomentumWeightTiltBacktestScopeRunnerTest(unittest.TestCase):
    def test_runner_validates_fixed_backtest_scope_without_acceptance(self) -> None:
        summary = run_v5f_momentum_weight_tilt_backtest_scope(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_momentum_weight_tilt_backtest_scope")
        self.assertEqual(
            summary["pm_gate_decision"],
            "backtest_scope_positive_keep_forward_paper_candidate_not_accepted",
        )
        self.assertEqual(summary["backtest_scope_start"], "2021-05-01")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertGreaterEqual(summary["actual_first_trade_date"], "2021-05-01")
        self.assertLessEqual(summary["actual_last_trade_date"], "2026-05-31")
        self.assertEqual(summary["primary_candidate"], "mom_12_1_sleeve_tilt_10pct")
        self.assertGreater(summary["primary_delta_return_pct_points_vs_baseline_proxy"], 0.0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_momentum_weight_tilt_backtest_scope") / "current"
        expected = [
            "v5f_momentum_weight_tilt_backtest_summary.json",
            "v5f_momentum_weight_tilt_backtest_scope_audit.csv",
            "v5f_momentum_weight_tilt_backtest_metrics.csv",
            "v5f_momentum_weight_tilt_backtest_yearly_performance.csv",
            "v5f_momentum_weight_tilt_backtest_rebalance_period_performance.csv",
            "v5f_momentum_weight_tilt_backtest_drawdown_review.csv",
            "v5f_momentum_weight_tilt_backtest_contribution_summary.csv",
            "v5f_momentum_weight_tilt_backtest_pm_gate_decision.csv",
            "v5f_momentum_weight_tilt_backtest_next_queue.csv",
            "v5f_momentum_weight_tilt_backtest_blockers.csv",
            "v5f_momentum_weight_tilt_backtest_report.md",
            "v5f_momentum_weight_tilt_backtest_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_momentum_weight_tilt_backtest_scope_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_momentum_weight_tilt_backtest_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")


if __name__ == "__main__":
    unittest.main()
