from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_momentum_addenda_closeout_runner import run_v5e_momentum_addenda_closeout


class V5eMomentumAddendaCloseoutRunnerTest(unittest.TestCase):
    def test_runner_closes_momentum_addenda_as_diagnostic_watchlist(self) -> None:
        summary = run_v5e_momentum_addenda_closeout(Path("."))

        self.assertEqual(summary["status"], "completed_v5e_momentum_addenda_closeout_packet")
        self.assertEqual(summary["pm_gate_decision"], "close_momentum_addenda_as_diagnostic_watchlist")
        self.assertEqual(summary["addendum_count"], 4)
        self.assertEqual(summary["best_component"], "long_horizon_momentum")
        self.assertEqual(summary["recommended_range"], "9_1_to_12_1_diagnostic_only")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_replacement"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_momentum_addenda_closeout_packet") / "current"
        expected = [
            "v5e_momentum_closeout_summary.json",
            "v5e_momentum_closeout_report.md",
            "v5e_momentum_addenda_component_matrix.csv",
            "v5e_momentum_signal_quality_matrix.csv",
            "v5e_momentum_event_proxy_comparison.csv",
            "v5e_momentum_governance_matrix.csv",
            "v5e_momentum_theory_readthrough.csv",
            "v5e_momentum_allowed_blocked_actions.csv",
            "v5e_momentum_closeout_pm_decision.csv",
            "v5e_momentum_closeout_next_queue.csv",
            "v5e_momentum_closeout_blockers.csv",
            "v5e_momentum_closeout_next_prompt.md",
            "v5e_momentum_closeout_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_momentum_governance_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in governance))

        with (out / "v5e_momentum_closeout_pm_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["live_trading_approved"], "False")
        self.assertEqual(decision["open_delay_sell_quant_spec_now"], "False")
        self.assertEqual(decision["threshold_scan_used"], "False")
        self.assertEqual(decision["new_buy_signal"], "False")

        with (out / "v5e_momentum_closeout_next_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_task"]: row for row in csv.DictReader(f)}
        self.assertEqual(queue["Continue V5e forward/paper tracking"]["allowed"], "True")
        self.assertEqual(queue["Keep 9-1/12-1 momentum as future research watchlist"]["allowed"], "True")
        self.assertEqual(queue["Open V5e delay-sell Quant spec from momentum"]["allowed"], "False")
        self.assertEqual(queue["Momentum threshold scan"]["allowed"], "False")


if __name__ == "__main__":
    unittest.main()
