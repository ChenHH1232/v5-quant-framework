from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_511360_pit_data_audit_runner import run_v5e_511360_pit_data_audit


class V5e511360PitDataAuditRunnerTest(unittest.TestCase):
    def test_runner_audits_511360_without_trading_or_acceptance(self) -> None:
        summary = run_v5e_511360_pit_data_audit(Path("."))

        self.assertEqual(summary["status"], "completed_511360_pit_data_audit")
        self.assertEqual(summary["pm_gate_decision"], "ready_for_511360_cash_proxy_limited_engineering_spec")
        self.assertEqual(summary["candidate_asset_code"], "511360.SH")
        self.assertGreater(summary["price_rows"], 1200)
        self.assertGreater(summary["nav_rows"], 1200)
        self.assertGreater(summary["execution_windows_checked"], 0)
        self.assertEqual(summary["low_liquidity_event_count"], 0)
        self.assertFalse(summary["engineering_backtest_run"])
        self.assertFalse(summary["trade_allowed"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_511360_pit_data_audit") / "current"
        for name in [
            "v5e_511360_pit_data_audit_summary.json",
            "v5e_511360_pit_data_audit_report.md",
            "v5e_511360_daily_price.csv",
            "v5e_511360_nav_history.csv",
            "v5e_511360_nav_discount_audit.csv",
            "v5e_511360_execution_liquidity_audit.csv",
            "v5e_511360_pm_gate_decision.csv",
            "v5e_511360_next_prompt.md",
        ]:
            self.assertTrue((out / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
