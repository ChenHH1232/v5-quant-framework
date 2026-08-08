from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_adaptive_momentum_governance_runner import run_v5f_adaptive_momentum_governance


class V5fAdaptiveMomentumGovernanceRunnerTest(unittest.TestCase):
    def test_runner_tests_adaptive_variants_without_acceptance(self) -> None:
        summary = run_v5f_adaptive_momentum_governance(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_adaptive_momentum_governance")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "promote_adaptive_momentum_to_pm_quant_review_not_accepted",
                "adaptive_positive_but_risk_or_edge_insufficient_keep_champion_primary",
                "adaptive_diagnostic_only_keep_champion_primary",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_adaptive_momentum_governance") / "current"
        for name in [
            "v5f_adaptive_momentum_summary.json",
            "v5f_adaptive_momentum_prompt.md",
            "v5f_adaptive_momentum_report.md",
            "v5f_adaptive_momentum_metrics.csv",
            "v5f_adaptive_momentum_comparison.csv",
            "v5f_adaptive_momentum_update_events.csv",
            "v5f_adaptive_momentum_update_summary.csv",
            "v5f_adaptive_momentum_governance_audit.csv",
            "v5f_adaptive_momentum_pm_decision.csv",
            "v5f_adaptive_momentum_next_queue.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_adaptive_momentum_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_adaptive_momentum_comparison.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        for version in [
            "internal_subsleeve_mom12_70_30_current_champion",
            "adaptive_monthly_momentum_70_30",
            "adaptive_rank_change_ge3_momentum_70_30",
            "adaptive_weight_drift_rel5pct_momentum_70_30",
            "adaptive_risk_warning_60d_down20_budget_30_to_10",
        ]:
            self.assertIn(version, rows)


if __name__ == "__main__":
    unittest.main()
