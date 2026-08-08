from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_cash_proxy_asset_data_gate_runner import run_v5e_cash_proxy_asset_data_gate


class V5eCashProxyAssetDataGateRunnerTest(unittest.TestCase):
    def test_runner_generates_data_gate_without_asset_selection(self) -> None:
        root = Path(".")
        summary = run_v5e_cash_proxy_asset_data_gate(root)

        self.assertEqual(summary["status"], "completed_cash_proxy_asset_data_gate")
        self.assertEqual(
            summary["pm_gate_decision"],
            "cash_proxy_asset_data_gate_complete_requires_user_asset_selection",
        )
        self.assertEqual(summary["candidate_type_count"], 4)
        self.assertFalse(summary["specific_asset_selected"])
        self.assertFalse(summary["cash_proxy_asset_trade_allowed"])
        self.assertFalse(summary["engineering_backtest_run"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["reentry_allowed"])
        self.assertFalse(summary["cross_sleeve_transfer_allowed"])
        self.assertFalse(summary["accepted"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = root / "v5e_cash_proxy_asset_data_gate" / "current"
        expected = [
            "v5e_cash_proxy_asset_data_gate_summary.json",
            "v5e_cash_proxy_asset_data_gate_report.md",
            "v5e_cash_proxy_asset_candidate_type_matrix.csv",
            "v5e_cash_proxy_asset_data_requirement.csv",
            "v5e_cash_proxy_asset_tradability_gate.csv",
            "v5e_cash_proxy_asset_risk_register.csv",
            "v5e_cash_proxy_asset_cost_liquidity_gate.csv",
            "v5e_cash_proxy_asset_income_accounting_spec.csv",
            "v5e_cash_proxy_asset_v57f_boundary.csv",
            "v5e_cash_proxy_asset_v5d_execution_boundary.csv",
            "v5e_cash_proxy_asset_blocked_actions.csv",
            "v5e_cash_proxy_asset_pm_gate_decision.csv",
            "v5e_cash_proxy_asset_next_agent_queue.csv",
            "v5e_cash_proxy_asset_blockers.csv",
            "v5e_cash_proxy_asset_next_prompt.md",
            "v5e_cash_proxy_asset_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_cash_proxy_asset_candidate_type_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            candidates = list(csv.DictReader(f))
        self.assertEqual({row["asset_type"] for row in candidates}, {
            "money_market_etf",
            "short_term_treasury_etf",
            "short_duration_bond_etf",
            "reverse_repo_or_cash_yield_proxy",
        })
        self.assertTrue(all(row["specific_asset_selected"] == "False" for row in candidates))
        self.assertTrue(all(row["trade_allowed"] == "False" for row in candidates))

        with (out / "v5e_cash_proxy_asset_blocked_actions.csv").open("r", encoding="utf-8-sig", newline="") as f:
            blocked = {row["action"] for row in csv.DictReader(f)}
        self.assertIn("select_specific_cash_proxy_asset_without_user_approval", blocked)
        self.assertIn("buy_cash_proxy_asset_in_current_task", blocked)
        self.assertIn("parameter_scan_cash_proxy", blocked)


if __name__ == "__main__":
    unittest.main()
