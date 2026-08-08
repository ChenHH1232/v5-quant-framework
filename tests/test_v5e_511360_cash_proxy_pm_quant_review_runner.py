from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_511360_cash_proxy_pm_quant_review_runner import (
    run_v5e_511360_cash_proxy_pm_quant_review,
)


class V5e511360CashProxyPMQuantReviewRunnerTest(unittest.TestCase):
    def test_review_promotes_forward_candidate_not_accepted(self) -> None:
        summary = run_v5e_511360_cash_proxy_pm_quant_review(Path("."))

        self.assertEqual(summary["status"], "completed_511360_cash_proxy_pm_quant_review")
        self.assertEqual(
            summary["pm_gate_decision"],
            "promote_511360_cash_proxy_to_forward_review_candidate_not_accepted",
        )
        self.assertGreater(summary["delta_return_vs_v57f"], 0)
        self.assertGreater(summary["delta_return_vs_hold_cash"], 0)
        self.assertLess(summary["delta_max_drawdown_vs_v57f"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"
        self.assertTrue((out / "v5e_511360_pm_quant_review_summary.json").exists())
        self.assertTrue((out / "v5e_511360_pm_quant_gate_decision.csv").exists())
        self.assertTrue((out / "v5e_511360_pm_quant_next_prompt.md").exists())


if __name__ == "__main__":
    unittest.main()
