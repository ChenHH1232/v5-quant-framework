from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5_qmt_model_retest_packet_runner import run_v5_qmt_model_retest_packet


class V5QmtModelRetestPacketRunnerTest(unittest.TestCase):
    def test_runner_exports_no_order_qmt_packet(self) -> None:
        summary = run_v5_qmt_model_retest_packet(Path("."))

        self.assertEqual(summary["status"], "completed_qmt_retest_packet_ready_manual_qmt_run_required")
        self.assertEqual(summary["backtest_start"], "2021-05-01")
        self.assertEqual(summary["effective_first_signal"], "2021-05-06")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["real_order_function_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreaterEqual(summary["ready_model_count"], 5)
        self.assertGreater(summary["target_weight_rows"], 0)

        out = Path("v5_qmt_model_retest_packet") / "current"
        expected = [
            "v5_qmt_retest_summary.json",
            "v5_qmt_retest_report.md",
            "v5_qmt_manual_run_checklist.md",
            "v5_qmt_expected_metric_comparison.csv",
            "v5_qmt_no_order_static_audit.csv",
            "v5_qmt_result_import_template.csv",
            "v5_qmt_retest_blockers.csv",
            "v5_qmt_retest_next_queue.csv",
            "v5_qmt_skill_candidate_spec.md",
            "qmt_inputs/v5_qmt_model_manifest.csv",
            "qmt_inputs/v5_qmt_selected_model_metrics.csv",
            "qmt_inputs/v5_qmt_target_weight_schedule.csv",
            "qmt_inputs/v5_qmt_source_file_manifest.csv",
            "qmt_scripts/v5_qmt_no_order_nav_replay.py",
            "qmt_scripts/v5_qmt_import_smoke_test.py",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5_qmt_no_order_static_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        script = (out / "qmt_scripts" / "v5_qmt_no_order_nav_replay.py").read_text(encoding="utf-8").lower()
        for term in ["passorder", "order_shares", "order_target", "order_value"]:
            self.assertNotIn(term, script)

        with (out / "qmt_inputs" / "v5_qmt_model_manifest.csv").open("r", encoding="utf-8-sig", newline="") as f:
            manifest = {row["model_id"]: row for row in csv.DictReader(f)}
        self.assertIn("v57f_startup_preload_repaired_baseline", manifest)
        self.assertIn("internal_subsleeve_mom12_70_30", manifest)
        self.assertEqual(manifest["internal_subsleeve_mom12_70_30"]["qmt_test_status"], "ready_for_qmt_no_order_replay")


if __name__ == "__main__":
    unittest.main()
