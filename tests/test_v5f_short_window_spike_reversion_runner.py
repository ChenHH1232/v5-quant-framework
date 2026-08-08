from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_short_window_spike_reversion_runner import run_v5f_short_window_spike_reversion


class V5fShortWindowSpikeReversionRunnerTest(unittest.TestCase):
    def test_runner_tests_spike_reversion_symmetry_without_acceptance(self) -> None:
        summary = run_v5f_short_window_spike_reversion(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_short_window_spike_reversion_symmetry")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "spike_reversion_positive_ready_for_pm_quant_review_not_accepted",
                "spike_reversion_positive_but_weak_keep_diagnostic",
                "spike_reversion_not_symmetric_keep_drop_repair_only",
            },
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_short_window_spike_reversion_symmetry") / "current"
        for name in [
            "v5f_short_window_spike_reversion_summary.json",
            "v5f_short_window_spike_reversion_report.md",
            "v5f_short_window_spike_reversion_spec.csv",
            "v5f_short_window_spike_reversion_event_log.csv",
            "v5f_short_window_spike_reversion_diagnostics.csv",
            "v5f_short_window_spike_reversion_trade_log.csv",
            "v5f_short_window_spike_reversion_metrics.csv",
            "v5f_short_window_spike_reversion_yearly.csv",
            "v5f_short_window_spike_reversion_sleeve_attribution.csv",
            "v5f_short_window_spike_reversion_governance_audit.csv",
            "v5f_short_window_spike_reversion_pm_decision.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_short_window_spike_reversion_governance_audit.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_short_window_spike_reversion_metrics.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = {row["version_id"]: row for row in csv.DictReader(f)}
        for version in [
            "morning30_spike_revert_next1_trim10_on_momentum_champion_estimate",
            "morning30_spike_revert_next2_trim10_on_momentum_champion_estimate",
            "late_vwap_premium_revert_next1_trim10_on_momentum_champion_estimate",
            "combo_morning30_spike_next1_plus_late_vwap_premium_next1_trim10_on_momentum_champion_estimate",
        ]:
            self.assertIn(version, rows)


if __name__ == "__main__":
    unittest.main()
