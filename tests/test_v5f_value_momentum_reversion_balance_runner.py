from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_value_momentum_reversion_balance_runner import (
    run_v5f_value_momentum_reversion_balance,
)


class V5fValueMomentumReversionBalanceRunnerTest(unittest.TestCase):
    def test_runner_separates_budget_substitution_from_event_satellite(self) -> None:
        summary = run_v5f_value_momentum_reversion_balance(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_value_momentum_reversion_balance_test")
        self.assertEqual(
            summary["pm_gate_decision"],
            "retain_70_30_champion_allow_mean_reversion_satellite_diagnostic_not_candidate",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["best_variant"], "vmr_70_30_plus_10_symmetric_shock")
        self.assertEqual(summary["best_family"], "event_satellite")
        self.assertGreater(summary["best_delta_return_pct_points_vs_champion"], 0.0)
        self.assertLess(summary["best_substitution_delta_vs_champion"], 0.0)
        self.assertEqual(summary["full_5min_coverage_rate_pct"], 100.0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_value_momentum_reversion_balance_test") / "current"
        for name in [
            "v5f_vmr_balance_summary.json",
            "v5f_vmr_balance_report.md",
            "v5f_vmr_balance_budget_matrix.csv",
            "v5f_vmr_balance_daily_returns.csv",
            "v5f_vmr_balance_variant_metrics.csv",
            "v5f_vmr_balance_yearly.csv",
            "v5f_vmr_balance_mean_reversion_source_audit.csv",
            "v5f_vmr_balance_sleeve_attribution.csv",
            "v5f_vmr_balance_governance_audit.csv",
            "v5f_vmr_balance_pm_gate_decision.csv",
            "v5f_vmr_balance_next_agent_queue.csv",
            "v5f_vmr_balance_blockers.csv",
            "v5f_vmr_balance_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_vmr_balance_variant_metrics.csv").open("r", encoding="utf-8-sig", newline="") as f:
            metrics = {row["version_id"]: row for row in csv.DictReader(f)}
        self.assertIn("vmr_70_30_0_champion", metrics)
        self.assertIn("vmr_70_25_5_symmetric_shock", metrics)
        self.assertIn("vmr_70_30_plus_5_symmetric_shock", metrics)
        self.assertLess(float(metrics["vmr_70_25_5_symmetric_shock"]["delta_return_pct_points_vs_champion"]), 0.0)
        self.assertGreater(float(metrics["vmr_70_30_plus_5_symmetric_shock"]["delta_return_pct_points_vs_champion"]), 0.0)
        self.assertEqual(metrics["vmr_70_30_plus_10_symmetric_shock"]["accepted"], "False")

        with (out / "v5f_vmr_balance_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = {row["audit_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(governance["full_5min_coverage_100pct"]["status"], "pass")
        self.assertEqual(governance["no_new_buy_signal"]["status"], "pass")
        self.assertEqual(governance["accepted_false"]["status"], "pass")
        self.assertEqual(governance["mean_reversion_oos_missing"]["status"], "review")


if __name__ == "__main__":
    unittest.main()
