from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_511360_cash_proxy_limited_engineering_spec_runner import (
    run_v5e_511360_cash_proxy_limited_engineering_spec,
)


class V5e511360CashProxyLimitedEngineeringSpecRunnerTest(unittest.TestCase):
    def test_spec_admits_limited_engineering_without_acceptance(self) -> None:
        summary = run_v5e_511360_cash_proxy_limited_engineering_spec(Path("."))

        self.assertEqual(summary["status"], "completed_511360_cash_proxy_limited_engineering_spec")
        self.assertEqual(
            summary["pm_gate_decision"],
            "admit_511360_cash_proxy_to_limited_engineering_test_not_accepted",
        )
        self.assertTrue(summary["engineering_test_allowed"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_511360_cash_proxy_limited_engineering_spec") / "current"
        self.assertTrue((out / "v5e_511360_cash_proxy_rule_spec.csv").exists())
        self.assertTrue((out / "v5e_511360_cash_proxy_next_prompt.md").exists())


if __name__ == "__main__":
    unittest.main()
