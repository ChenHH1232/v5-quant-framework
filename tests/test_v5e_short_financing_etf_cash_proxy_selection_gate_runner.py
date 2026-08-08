from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_short_financing_etf_cash_proxy_selection_gate_runner import (
    run_v5e_short_financing_etf_cash_proxy_selection_gate,
)


class V5eShortFinancingEtfCashProxySelectionGateRunnerTest(unittest.TestCase):
    def test_runner_selects_511360_for_data_audit_only(self) -> None:
        root = Path(".")
        summary = run_v5e_short_financing_etf_cash_proxy_selection_gate(root)

        self.assertEqual(summary["status"], "completed_short_financing_etf_cash_proxy_selection_gate")
        self.assertEqual(
            summary["pm_gate_decision"],
            "short_financing_etf_511360_admit_to_pit_data_audit_not_engineering",
        )
        self.assertEqual(summary["candidate_asset_code"], "511360.SH")
        self.assertTrue(summary["user_candidate_selected"])
        self.assertTrue(summary["specific_asset_selected_for_data_gate"])
        self.assertFalse(summary["engineering_test_allowed_now"])
        self.assertFalse(summary["trade_allowed"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["reentry_allowed"])
        self.assertFalse(summary["cross_sleeve_transfer_allowed"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_short_financing_etf_cash_proxy_selection_gate" / "current"
        expected = [
            "v5e_short_financing_etf_selection_summary.json",
            "v5e_short_financing_etf_selection_report.md",
            "v5e_short_financing_etf_candidate_profile.csv",
            "v5e_short_financing_etf_source_snapshot.csv",
            "v5e_short_financing_etf_pit_data_requirement.csv",
            "v5e_short_financing_etf_tradability_liquidity_checklist.csv",
            "v5e_short_financing_etf_risk_register.csv",
            "v5e_short_financing_etf_income_nav_accounting.csv",
            "v5e_short_financing_etf_v57f_boundary.csv",
            "v5e_short_financing_etf_v5d_execution_boundary.csv",
            "v5e_short_financing_etf_blocked_actions.csv",
            "v5e_short_financing_etf_pm_gate_decision.csv",
            "v5e_short_financing_etf_next_agent_queue.csv",
            "v5e_short_financing_etf_blockers.csv",
            "v5e_short_financing_etf_next_prompt.md",
            "v5e_short_financing_etf_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_short_financing_etf_candidate_profile.csv").open("r", encoding="utf-8-sig", newline="") as f:
            profile = list(csv.DictReader(f))[0]
        self.assertEqual(profile["candidate_asset_code"], "511360.SH")
        self.assertEqual(profile["asset_type"], "short_duration_bond_etf")
        self.assertEqual(profile["trade_allowed"], "False")
        self.assertEqual(profile["accepted"], "False")

        with (out / "v5e_short_financing_etf_blocked_actions.csv").open("r", encoding="utf-8-sig", newline="") as f:
            blocked = {row["action"] for row in csv.DictReader(f)}
        self.assertIn("buy_511360_in_current_task", blocked)
        self.assertIn("run_backtest_before_pit_data_audit", blocked)
        self.assertIn("compare_using_price_only_without_total_return", blocked)


if __name__ == "__main__":
    unittest.main()
