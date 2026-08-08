from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_511360_cash_proxy_forward_stress_runner import (
    run_v5e_511360_cash_proxy_forward_stress,
)


class V5e511360CashProxyForwardStressRunnerTest(unittest.TestCase):
    def test_runner_retains_forward_candidate_not_accepted(self) -> None:
        summary = run_v5e_511360_cash_proxy_forward_stress(Path("."))

        self.assertEqual(summary["status"], "completed_511360_cash_proxy_forward_stress_packet")
        self.assertEqual(summary["pm_gate_decision"], "retain_511360_forward_review_candidate_not_accepted")
        self.assertGreater(summary["delta_return_vs_v57f"], 0)
        self.assertGreater(summary["delta_return_vs_hold_cash"], 0)
        self.assertEqual(summary["open_forward_restore_count"], 3)
        self.assertLess(summary["worst_60d_return_pct"], 0)
        self.assertGreater(summary["max_abs_premium_discount_pct"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_511360_cash_proxy_forward_stress_packet") / "current"
        for name in [
            "v5e_511360_forward_stress_summary.json",
            "v5e_511360_forward_stress_report.md",
            "v5e_511360_open_forward_restore_watchlist.csv",
            "v5e_511360_price_stress_windows.csv",
            "v5e_511360_forward_stress_pm_gate_decision.csv",
            "v5e_511360_forward_stress_next_prompt.md",
        ]:
            self.assertTrue((out / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
