from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_forward_paper_daily_packet_runner import run_v5e_forward_paper_daily_packet


class V5eForwardPaperDailyPacketRunnerTest(unittest.TestCase):
    def test_runner_records_forward_packet_without_restore_or_acceptance(self) -> None:
        summary = run_v5e_forward_paper_daily_packet(Path("."))

        self.assertEqual(summary["status"], "completed_v5e_forward_paper_daily_packet")
        self.assertEqual(summary["paper_daily_decision"], "forward_tracking_recorded_official_restore_pending")
        self.assertEqual(summary["paper_date"], "2026-07-29")
        self.assertEqual(summary["latest_rebalance_signal_date"], "2026-04-01")
        self.assertFalse(summary["official_202607_restore_available"])
        self.assertFalse(summary["v5e_accepted"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_forward_paper_daily_packet") / "current"
        expected = [
            "v5e_forward_daily_summary.json",
            "v5e_forward_daily_report.md",
            "v5e_forward_daily_signal_log.csv",
            "v5e_forward_daily_v57f_snapshot.csv",
            "v5e_forward_daily_profit_lock_observation.csv",
            "v5e_forward_daily_511360_proxy_observation.csv",
            "v5e_forward_daily_governance_audit.csv",
            "v5e_forward_daily_511360_restore_status.csv",
            "v5e_forward_daily_next_queue.csv",
            "v5e_forward_daily_blockers.csv",
            "v5e_forward_daily_next_prompt.md",
            "v5e_forward_daily_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_forward_daily_511360_restore_status.csv").open("r", encoding="utf-8-sig", newline="") as f:
            restore = list(csv.DictReader(f))[0]
        self.assertEqual(restore["latest_local_v57f_rebalance_signal"], "2026-04-01")
        self.assertEqual(restore["official_restore_available"], "False")
        self.assertEqual(restore["allowed_to_run_closeout"], "False")
        self.assertEqual(restore["historical_backtest_blocker"], "False")
        self.assertEqual(restore["forward_only_status"], "pending")

        with (out / "v5e_forward_daily_next_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_task"]: row for row in csv.DictReader(f)}
        self.assertEqual(queue["Continue V5e forward/paper tracking"]["allowed"], "True")
        self.assertEqual(queue["511360 official restore closeout"]["allowed"], "False")
        self.assertEqual(queue["V5e threshold scan"]["allowed"], "False")


if __name__ == "__main__":
    unittest.main()
