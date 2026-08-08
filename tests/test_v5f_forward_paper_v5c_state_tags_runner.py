from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_forward_paper_v5c_state_tags_runner import run_v5f_forward_paper_v5c_state_tags


class V5fForwardPaperV5cStateTagsRunnerTest(unittest.TestCase):
    def test_runner_attaches_state_tags_without_trade_impact(self) -> None:
        summary = run_v5f_forward_paper_v5c_state_tags(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_forward_paper_v5c_state_tags")
        self.assertEqual(
            summary["pm_gate_decision"],
            "v5c_state_tags_attached_to_v5f_forward_observation_not_trade_rule",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertGreater(summary["seed_tag_rows"], 0)
        self.assertEqual(summary["unique_seed_rebalance_dates"], 4)
        self.assertEqual(summary["unique_sleeves"], 4)
        self.assertGreater(summary["pm_review_queue_rows"], 0)
        self.assertEqual(summary["trade_order_allowed_count"], 0)
        self.assertEqual(summary["weight_change_allowed_count"], 0)
        self.assertEqual(
            summary["overheat_engineering_gate"],
            "overheat_no_new_overweight_diagnostic_only_do_not_replace_v5f_champion",
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertFalse(summary["engineering_backtest_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_forward_paper_v5c_state_tags") / "current"
        expected = [
            "v5f_v5c_state_tag_summary.json",
            "v5f_v5c_state_tag_report.md",
            "v5f_v5c_state_tag_input_manifest.csv",
            "v5f_v5c_state_tag_schema.csv",
            "v5f_v5c_state_tag_historical_seed.csv",
            "v5f_v5c_state_tag_forward_observation_template.csv",
            "v5f_v5c_state_tag_watch_summary_by_sleeve.csv",
            "v5f_v5c_state_tag_watch_summary_by_rebalance.csv",
            "v5f_v5c_state_tag_pm_review_queue.csv",
            "v5f_v5c_state_tag_governance_audit.csv",
            "v5f_v5c_state_tag_allowed_blocked_actions.csv",
            "v5f_v5c_state_tag_pm_gate_decision.csv",
            "v5f_v5c_state_tag_next_agent_queue.csv",
            "v5f_v5c_state_tag_blockers.csv",
            "v5f_v5c_state_tag_next_prompt.md",
            "v5f_v5c_state_tag_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_v5c_state_tag_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_v5c_state_tag_historical_seed.csv").open("r", encoding="utf-8-sig", newline="") as f:
            seed = list(csv.DictReader(f))
        self.assertTrue(all(row["allowed_action"] == "record_observe_only_tag" for row in seed))
        self.assertTrue(all(row["trade_order_allowed"] == "False" for row in seed))
        self.assertTrue(all(row["weight_change_allowed"] == "False" for row in seed))

        with (out / "v5f_v5c_state_tag_allowed_blocked_actions.csv").open("r", encoding="utf-8-sig", newline="") as f:
            actions = {row["action"]: row for row in csv.DictReader(f)}
        self.assertEqual(actions["change_v5f_weight_from_v5c_tag"]["allowed"], "False")
        self.assertEqual(actions["sell_stock_from_v5c_overheat_tag"]["allowed"], "False")
        self.assertEqual(actions["attach_v5c_state_tags_to_forward_paper_rows"]["allowed"], "True")


if __name__ == "__main__":
    unittest.main()
