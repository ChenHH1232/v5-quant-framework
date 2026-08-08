from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_joinquant_export_checklist_runner import run_v5f_joinquant_export_checklist


class V5fJoinQuantExportChecklistRunnerTest(unittest.TestCase):
    def test_runner_prepares_export_checklist_without_starting_joinquant(self) -> None:
        summary = run_v5f_joinquant_export_checklist(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_joinquant_export_checklist")
        self.assertEqual(
            summary["pm_gate_decision"],
            "joinquant_export_checklist_ready_wait_for_user_exports_not_started",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertEqual(summary["local_5min_bar_source_policy"], "baostock_only")
        self.assertTrue(summary["joinquant_platform_minute_backtest_allowed"])
        self.assertFalse(summary["jqdata_sdk_minute_bar_source_allowed"])
        self.assertEqual(summary["platform_backtest_frequency"], "minute")
        self.assertEqual(summary["required_export_count"], 7)
        self.assertEqual(summary["historical_export_count"], 5)
        self.assertEqual(summary["forward_export_count"], 2)
        self.assertEqual(summary["target_population_status"], "not_populated_waiting_next_clean_official_repaired_v57f_targets")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_joinquant_export_checklist") / "current"
        expected = [
            "v5f_joinquant_export_checklist_summary.json",
            "v5f_joinquant_export_checklist_report.md",
            "v5f_joinquant_input_manifest.csv",
            "v5f_joinquant_required_exports.csv",
            "v5f_joinquant_export_field_schema.csv",
            "v5f_joinquant_export_dropzone_manifest.csv",
            "v5f_joinquant_platform_attribution_plan.csv",
            "v5f_joinquant_clean_target_preflight.csv",
            "v5f_joinquant_export_quality_gates.csv",
            "v5f_joinquant_allowed_blocked_actions.csv",
            "v5f_joinquant_user_action_checklist.md",
            "v5f_joinquant_pm_gate_decision.csv",
            "v5f_joinquant_next_agent_queue.csv",
            "v5f_joinquant_blockers.csv",
            "v5f_joinquant_agent_execution_rules.md",
            "v5f_joinquant_next_prompt.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_joinquant_required_exports.csv").open("r", encoding="utf-8-sig", newline="") as f:
            exports = list(csv.DictReader(f))
        self.assertEqual({row["scope"] for row in exports}, {"historical_platform_attribution", "forward_clean_target_population"})
        self.assertTrue(all("2026-05-31" in row["date_range"] for row in exports if row["scope"] == "historical_platform_attribution"))
        transactions = next(row for row in exports if row["file_name"] == "transactions.csv")
        self.assertIn("Minute-backtest", transactions["content"])

        with (out / "v5f_joinquant_clean_target_preflight.csv").open("r", encoding="utf-8-sig", newline="") as f:
            preflight = {row["source_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(preflight["late_shadow_signal_20260701"]["audit_status"], "reference_only_not_clean_forward")
        self.assertEqual(preflight["late_shadow_signal_20260701"]["use_for_paper_population_now"], "False")
        self.assertEqual(preflight["current_population_state"]["current_action"], "wait_for_clean_official_repaired_v57f_targets")

        with (out / "v5f_joinquant_export_quality_gates.csv").open("r", encoding="utf-8-sig", newline="") as f:
            gates = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in gates))

        with (out / "v5f_joinquant_pm_gate_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            decision = list(csv.DictReader(f))[0]
        self.assertEqual(decision["joinquant_started"], "False")
        self.assertEqual(decision["accepted"], "False")
        self.assertEqual(decision["clean_forward_target_ready_now"], "False")

        with (out / "v5f_joinquant_next_agent_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_task"]: row for row in csv.DictReader(f)}
        self.assertIn("user_runs_joinquant_platform_minute_backtest_and_supplies_exports", queue)

        self.assertTrue((Path("data") / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution").exists())
        self.assertTrue((Path("data") / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "forward_clean_targets").exists())


if __name__ == "__main__":
    unittest.main()
