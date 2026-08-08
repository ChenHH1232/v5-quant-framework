from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_momentum_weight_tilt_forward_tracking_runner import run_v5f_momentum_weight_tilt_forward_tracking


class V5fMomentumWeightTiltForwardTrackingRunnerTest(unittest.TestCase):
    def test_runner_creates_forward_tracking_packet_without_live_status(self) -> None:
        summary = run_v5f_momentum_weight_tilt_forward_tracking(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_momentum_weight_tilt_forward_paper_tracking_packet")
        self.assertEqual(
            summary["pm_gate_decision"],
            "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal",
        )
        self.assertEqual(summary["candidate_id"], "mom_12_1_sleeve_tilt_10pct")
        self.assertGreater(summary["primary_delta_return_pct_points_vs_baseline_proxy"], 0.0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_momentum_weight_tilt_forward_paper_tracking") / "current"
        expected = [
            "v5f_momentum_weight_tilt_forward_summary.json",
            "v5f_momentum_weight_tilt_forward_candidate_status.csv",
            "v5f_momentum_weight_tilt_forward_tracking_schema.csv",
            "v5f_momentum_weight_tilt_rebalance_day_checklist.csv",
            "v5f_momentum_weight_tilt_paper_signal_template.csv",
            "v5f_momentum_weight_tilt_forward_governance_audit.csv",
            "v5f_momentum_weight_tilt_forward_next_queue.csv",
            "v5f_momentum_weight_tilt_forward_blockers.csv",
            "v5f_momentum_weight_tilt_forward_report.md",
            "v5f_momentum_weight_tilt_forward_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_momentum_weight_tilt_forward_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertTrue(all(row["status"] == "pass" for row in audit))

        with (out / "v5f_momentum_weight_tilt_forward_candidate_status.csv").open("r", encoding="utf-8-sig", newline="") as f:
            status = list(csv.DictReader(f))[0]
        self.assertEqual(status["accepted"], "False")
        self.assertEqual(status["live_trading_approved"], "False")


if __name__ == "__main__":
    unittest.main()
