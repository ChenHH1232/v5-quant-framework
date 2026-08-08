from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_p2_valuation_and_crowding_state_panel_runner import (
    run_v5c_p2_valuation_and_crowding_state_panel,
)


class V5cP2ValuationAndCrowdingStatePanelRunnerTest(unittest.TestCase):
    def test_runner_builds_pit_valuation_and_crowding_state_panel(self) -> None:
        summary = run_v5c_p2_valuation_and_crowding_state_panel(Path("."))

        self.assertEqual(summary["status"], "completed_p2_valuation_and_crowding_state_panel")
        self.assertEqual(
            summary["pm_gate_decision"],
            "p2_valuation_crowding_state_panel_pass_ready_for_v5c_p3_state_governance_spec",
        )
        self.assertTrue(summary["p0_dependency_pass"])
        self.assertTrue(summary["p1_dependency_pass"])
        self.assertGreater(summary["valuation_rows"], 0)
        self.assertGreater(summary["crowding_rows"], 0)
        self.assertGreater(summary["sleeve_overheat_rows"], 0)
        self.assertGreater(summary["broad_trend_rows"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_strategy_rule_added"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
        expected = [
            "v5c_p2_valuation_crowding_summary.json",
            "v5c_p2_valuation_crowding_report.md",
            "v5c_p2_source_manifest.csv",
            "v5c_p2_valuation_state_panel.csv",
            "v5c_p2_crowding_state_panel.csv",
            "v5c_p2_sleeve_overheat_state_panel.csv",
            "v5c_p2_broad_index_trend_state_panel.csv",
            "v5c_p2_field_coverage_audit.csv",
            "v5c_p2_pit_leakage_audit.csv",
            "v5c_p2_pm_gate_decision.csv",
            "v5c_p2_next_agent_queue.csv",
            "v5c_p2_blockers.csv",
            "v5c_p2_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_p2_valuation_state_panel.csv").open("r", encoding="utf-8-sig", newline="") as f:
            valuation = list(csv.DictReader(f))
        self.assertEqual(len(valuation), summary["valuation_rows"])
        self.assertTrue(all(row["panel_join_status"] == "matched" for row in valuation))
        self.assertTrue(all(row["pit_status"] == "pass" for row in valuation))
        self.assertTrue(any(row["valuation_state"] == "valuation_overheat_watch" for row in valuation))

        with (out / "v5c_p2_crowding_state_panel.csv").open("r", encoding="utf-8-sig", newline="") as f:
            crowding = list(csv.DictReader(f))
        self.assertEqual(len(crowding), summary["crowding_rows"])
        self.assertTrue(all(row["price_join_status"] == "matched" for row in crowding))
        self.assertTrue(all(row["pit_status"] == "pass" for row in crowding))
        self.assertTrue(all(row["state_asof_date"] < row["trade_date"] for row in crowding))

        with (out / "v5c_p2_pit_leakage_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            pit = list(csv.DictReader(f))
        self.assertTrue(pit)
        self.assertTrue(all(row["audit_status"] == "pass" for row in pit))

        with (out / "v5c_p2_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["p2_pass"], "True")
        self.assertEqual(decision["new_strategy_rule_added"], "False")
        self.assertEqual(decision["network_fetch_started"], "False")
        self.assertEqual(decision["joinquant_started"], "False")


if __name__ == "__main__":
    unittest.main()
