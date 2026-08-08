from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_511360_cash_proxy_limited_engineering_runner import (
    run_v5e_511360_cash_proxy_limited_engineering,
)


class V5e511360CashProxyLimitedEngineeringRunnerTest(unittest.TestCase):
    def test_runner_improves_hold_cash_without_acceptance(self) -> None:
        summary = run_v5e_511360_cash_proxy_limited_engineering(Path("."))

        self.assertEqual(summary["status"], "completed_511360_cash_proxy_limited_engineering")
        self.assertEqual(
            summary["pm_gate_decision"],
            "promote_511360_cash_proxy_to_pm_quant_review_candidate_not_accepted",
        )
        self.assertGreater(summary["proxy_delta_return_vs_v57f"], 0)
        self.assertGreater(summary["proxy_delta_return_vs_hold_cash"], 0)
        self.assertLess(summary["proxy_delta_max_drawdown_vs_v57f"], 0)
        self.assertGreater(summary["proxy_net_pnl"], 0)
        self.assertEqual(summary["proxy_trade_count"], 174)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_511360_cash_proxy_limited_engineering") / "current"
        self.assertTrue((out / "v5e_511360_cash_proxy_variant_metrics.csv").exists())
        self.assertTrue((out / "v5e_511360_cash_proxy_daily_returns.csv").exists())
        self.assertTrue((out / "v5e_511360_cash_proxy_pm_gate_decision.csv").exists())


if __name__ == "__main__":
    unittest.main()
