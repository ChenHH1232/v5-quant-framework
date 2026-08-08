from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_momentum_weight_tilt_runner import run_v5f_momentum_weight_tilt


class V5fMomentumWeightTiltRunnerTest(unittest.TestCase):
    def test_runner_completes_fixed_weight_tilt_without_acceptance(self) -> None:
        summary = run_v5f_momentum_weight_tilt(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_momentum_weight_tilt_limited_engineering")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "admit_momentum_weight_tilt_to_pm_quant_review_not_accepted",
                "diagnostic_positive_but_primary_not_confirmed",
                "diagnostic_only_no_weight_tilt_candidate",
            },
        )
        self.assertEqual(summary["primary_version"], "mom_12_1_sleeve_tilt_10pct")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        spec = Path("v5f_momentum_weight_tilt_quant_spec") / "current"
        eng = Path("v5f_momentum_weight_tilt_limited_engineering") / "current"
        for path in [
            spec / "v5f_momentum_weight_tilt_summary.json",
            spec / "v5f_momentum_weight_tilt_rule_spec.csv",
            spec / "v5f_momentum_weight_tilt_boundary.csv",
            eng / "v5f_momentum_weight_tilt_summary.json",
            eng / "v5f_momentum_weight_tilt_metrics.csv",
            eng / "v5f_momentum_weight_tilt_governance_audit.csv",
            eng / "v5f_momentum_weight_tilt_pm_gate_decision.csv",
        ]:
            self.assertTrue(path.exists(), str(path))

        with (eng / "v5f_momentum_weight_tilt_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (eng / "v5f_momentum_weight_tilt_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")
        self.assertEqual(decision["v57f_core_modified"], "False")
        self.assertEqual(decision["threshold_scan_used"], "False")
        self.assertEqual(decision["new_buy_signal"], "False")


if __name__ == "__main__":
    unittest.main()
