from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_p1_financial_quality_pit_panel_runner import run_v5c_p1_financial_quality_pit_panel


class V5cP1FinancialQualityPitPanelRunnerTest(unittest.TestCase):
    def test_runner_builds_financial_quality_pit_panel_from_repaired_baseline(self) -> None:
        summary = run_v5c_p1_financial_quality_pit_panel(Path("."))

        self.assertEqual(summary["status"], "completed_p1_financial_quality_pit_panel")
        self.assertEqual(
            summary["pm_gate_decision"],
            "p1_financial_quality_pit_panel_pass_with_payout_proxy_review_ready_for_p2",
        )
        self.assertTrue(summary["p0_dependency_pass"])
        self.assertGreater(summary["financial_panel_rows"], 0)
        self.assertGreater(summary["cash_dividend_event_rows"], 0)
        self.assertGreater(summary["universe_code_count"], 0)
        self.assertFalse(summary["exact_payout_ratio_available"])
        self.assertTrue(summary["payout_proxy_used"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["new_strategy_rule_added"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5c_p1_financial_quality_pit_panel") / "current"
        expected = [
            "v5c_p1_financial_quality_summary.json",
            "v5c_p1_financial_quality_report.md",
            "v5c_p1_source_manifest.csv",
            "v5c_p1_financial_universe.csv",
            "v5c_p1_financial_quality_pit_panel.csv",
            "v5c_p1_cash_dividend_events.csv",
            "v5c_p1_dividend_policy_audit.csv",
            "v5c_p1_field_coverage_audit.csv",
            "v5c_p1_visible_date_audit.csv",
            "v5c_p1_payout_ratio_proxy_audit.csv",
            "v5c_p1_financial_quality_by_sleeve.csv",
            "v5c_p1_pm_gate_decision.csv",
            "v5c_p1_next_data_gate_queue.csv",
            "v5c_p1_blockers.csv",
            "v5c_p1_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_p1_financial_quality_pit_panel.csv").open("r", encoding="utf-8-sig", newline="") as f:
            panel = list(csv.DictReader(f))
        self.assertEqual(len(panel), summary["financial_panel_rows"])
        self.assertTrue(all(row["panel_join_status"] == "matched" for row in panel))
        self.assertTrue(all(row["visible_date_status"] == "pass" for row in panel))
        self.assertTrue(all(row["cash_dividend_event_available"] for row in panel))

        with (out / "v5c_p1_visible_date_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            visible_audit = list(csv.DictReader(f))
        self.assertTrue(visible_audit)
        self.assertTrue(all(row["audit_status"] == "pass" for row in visible_audit))

        with (out / "v5c_p1_payout_ratio_proxy_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            payout_audit = list(csv.DictReader(f))
        self.assertTrue(payout_audit)
        self.assertTrue(any(row["payout_gate_status"] == "review_proxy_only" for row in payout_audit))
        self.assertTrue(all(row["payout_ratio_exact_count"] == "0" for row in payout_audit))

        with (out / "v5c_p1_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["p1_pass"], "True")
        self.assertEqual(decision["exact_payout_ratio_available"], "False")
        self.assertEqual(decision["payout_proxy_used"], "True")


if __name__ == "__main__":
    unittest.main()
