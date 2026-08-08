from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_511360_forward_paper_tracking_runner import (
    run_v5e_511360_forward_paper_tracking,
)


class V5e511360ForwardPaperTrackingRunnerTest(unittest.TestCase):
    def test_runner_closes_proxy_side_and_blocks_official_restore(self) -> None:
        summary = run_v5e_511360_forward_paper_tracking(Path("."))

        self.assertEqual(summary["status"], "completed_511360_forward_paper_tracking")
        self.assertEqual(
            summary["pm_gate_decision"],
            "proxy_side_forward_closeout_done_blocked_until_official_v57f_restore",
        )
        self.assertGreater(summary["price_update_rows"], 0)
        self.assertGreater(summary["nav_update_rows"], 0)
        self.assertEqual(summary["restore_closeout_count"], 3)
        self.assertGreater(summary["proxy_side_closeout_realized_pnl"], 0)
        self.assertFalse(summary["official_v57f_restore_available"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5e_threshold_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertTrue(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_511360_forward_paper_tracking") / "current"
        for name in [
            "v5e_511360_forward_tracking_summary.json",
            "v5e_511360_forward_tracking_report.md",
            "v5e_511360_forward_price_update.csv",
            "v5e_511360_forward_nav_update.csv",
            "v5e_511360_open_forward_restore_closeout.csv",
            "v5e_511360_forward_tracking_next_prompt.md",
        ]:
            self.assertTrue((out / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
