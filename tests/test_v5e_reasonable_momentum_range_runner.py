from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_reasonable_momentum_range_runner import run_v5e_reasonable_momentum_range


class V5eReasonableMomentumRangeRunnerTest(unittest.TestCase):
    def test_runner_completes_reasonable_range_without_acceptance(self) -> None:
        summary = run_v5e_reasonable_momentum_range(Path("."))

        self.assertEqual(summary["status"], "completed_v5e_reasonable_momentum_range_test")
        self.assertEqual(summary["range"], "6_1_9_1_12_1_skip_20_trading_days")
        self.assertEqual(summary["research_pool"], "v57f_v5e_existing_value_dividend_lowvol_sleeve_pool_only")
        self.assertGreater(summary["held_stock_day_count"], 0)
        self.assertGreater(summary["feature_event_count"], 0)
        self.assertEqual(summary["primary_feature"], "mom_12_1_vs_sleeve_mean")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_replacement"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_reasonable_momentum_range_test") / "current"
        expected = [
            "v5e_reasonable_momentum_summary.json",
            "v5e_reasonable_momentum_report.md",
            "v5e_reasonable_momentum_v4_anchor.csv",
            "v5e_reasonable_momentum_feature_schema.csv",
            "v5e_reasonable_momentum_pit_governance_audit.csv",
            "v5e_reasonable_momentum_held_stock_features.csv",
            "v5e_reasonable_momentum_range_diagnostics.csv",
            "v5e_reasonable_momentum_trigger_overlay.csv",
            "v5e_reasonable_momentum_nav_proxy.csv",
            "v5e_reasonable_momentum_pm_gate_decision.csv",
            "v5e_reasonable_momentum_next_queue.csv",
            "v5e_reasonable_momentum_blockers.csv",
            "v5e_reasonable_momentum_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_reasonable_momentum_pit_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            pit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in pit))

        with (out / "v5e_reasonable_momentum_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")
        self.assertEqual(decision["v57f_replacement"], "False")
        self.assertEqual(decision["v57f_core_modified"], "False")
        self.assertEqual(decision["threshold_scan_used"], "False")
        self.assertEqual(decision["new_buy_signal"], "False")


if __name__ == "__main__":
    unittest.main()
