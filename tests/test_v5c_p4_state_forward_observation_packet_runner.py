from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_p4_state_forward_observation_packet_runner import run_v5c_p4_state_forward_observation_packet


class V5cP4StateForwardObservationPacketRunnerTest(unittest.TestCase):
    def test_runner_builds_observe_only_forward_observation_packet(self) -> None:
        summary = run_v5c_p4_state_forward_observation_packet(Path("."))

        self.assertEqual(summary["status"], "completed_p4_state_forward_observation_packet")
        self.assertEqual(
            summary["pm_gate_decision"],
            "p4_forward_observation_packet_pass_ready_for_future_v57f_rebalance_tracking",
        )
        self.assertTrue(summary["p3_dependency_pass"])
        self.assertGreater(summary["seed_observation_rows"], 0)
        self.assertGreater(summary["watchlist_seed_rows"], 0)
        self.assertGreater(summary["pm_review_queue_rows"], 0)
        self.assertGreater(summary["blocked_action_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_strategy_rule_added"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5c_p4_state_forward_observation_packet") / "current"
        expected = [
            "v5c_p4_state_forward_observation_summary.json",
            "v5c_p4_state_forward_observation_report.md",
            "v5c_p4_input_dependency_audit.csv",
            "v5c_p4_forward_observation_template.csv",
            "v5c_p4_historical_seed_observation_log.csv",
            "v5c_p4_watchlist_seed.csv",
            "v5c_p4_pm_review_queue.csv",
            "v5c_p4_observation_governance_rules.csv",
            "v5c_p4_blocked_actions.csv",
            "v5c_p4_pm_gate_decision.csv",
            "v5c_p4_next_agent_queue.csv",
            "v5c_p4_blockers.csv",
            "v5c_p4_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_p4_historical_seed_observation_log.csv").open("r", encoding="utf-8-sig", newline="") as f:
            seed = list(csv.DictReader(f))
        self.assertEqual(len(seed), summary["seed_observation_rows"])
        self.assertTrue(all(row["action_taken"] == "observe_only" for row in seed))
        self.assertTrue(all(row["trade_impact"] == "none" for row in seed))

        with (out / "v5c_p4_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["p4_pass"], "True")
        self.assertEqual(decision["admit_forward_tracking"], "True")
        self.assertEqual(decision["admit_engineering_backtest"], "False")
        self.assertEqual(decision["admit_trading_rule"], "False")


if __name__ == "__main__":
    unittest.main()
