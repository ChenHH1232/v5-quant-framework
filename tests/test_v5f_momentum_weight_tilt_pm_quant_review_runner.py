from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_momentum_weight_tilt_pm_quant_review_runner import run_v5f_momentum_weight_tilt_pm_quant_review


class V5fMomentumWeightTiltPmQuantReviewRunnerTest(unittest.TestCase):
    def test_runner_promotes_primary_to_forward_candidate_without_acceptance(self) -> None:
        summary = run_v5f_momentum_weight_tilt_pm_quant_review(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_momentum_weight_tilt_pm_quant_review")
        self.assertEqual(
            summary["pm_gate_decision"],
            "promote_momentum_weight_tilt_to_forward_paper_candidate_not_accepted",
        )
        self.assertEqual(summary["primary_candidate"], "mom_12_1_sleeve_tilt_10pct")
        self.assertGreater(summary["primary_delta_return_pct_points_vs_baseline_proxy"], 0.0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_momentum_weight_tilt_pm_quant_review") / "current"
        expected = [
            "v5f_momentum_weight_tilt_pm_quant_summary.json",
            "v5f_momentum_weight_tilt_variant_review.csv",
            "v5f_momentum_weight_tilt_candidate_checks.csv",
            "v5f_momentum_weight_tilt_risk_benefit_matrix.csv",
            "v5f_momentum_weight_tilt_attribution_review.csv",
            "v5f_momentum_weight_tilt_governance_review.csv",
            "v5f_momentum_weight_tilt_pm_gate_decision.csv",
            "v5f_momentum_weight_tilt_next_queue.csv",
            "v5f_momentum_weight_tilt_pm_quant_blockers.csv",
            "v5f_momentum_weight_tilt_report.md",
            "v5f_momentum_weight_tilt_next_prompt.md",
            "v5f_momentum_weight_tilt_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_momentum_weight_tilt_candidate_checks.csv").open("r", encoding="utf-8-sig", newline="") as f:
            checks = list(csv.DictReader(f))
        self.assertTrue(all(row["pass"] == "True" for row in checks))

        with (out / "v5f_momentum_weight_tilt_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")


if __name__ == "__main__":
    unittest.main()
