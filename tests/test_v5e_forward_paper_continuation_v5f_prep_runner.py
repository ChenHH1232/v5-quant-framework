from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_forward_paper_continuation_v5f_prep_runner import (
    run_v5e_forward_paper_continuation_v5f_prep,
)


class V5eForwardPaperContinuationV5fPrepRunnerTest(unittest.TestCase):
    def test_runner_prepares_v5f_without_acceptance_or_restore(self) -> None:
        summary = run_v5e_forward_paper_continuation_v5f_prep(Path("."))

        self.assertEqual(summary["status"], "completed_v5e_forward_paper_continuation_v5f_prep")
        self.assertEqual(
            summary["continuation_decision"],
            "continue_v5e_forward_paper_tracking_and_prepare_v5f_governance",
        )
        self.assertEqual(summary["forward_tracking_item_count"], 3)
        self.assertEqual(summary["v5f_prep_item_count"], 5)
        self.assertFalse(summary["official_202607_restore_available"])
        self.assertFalse(summary["v5e_accepted"])
        self.assertFalse(summary["v5e_replacement_for_v57f"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_forward_paper_continuation_v5f_prep") / "current"
        expected = [
            "v5e_continuation_summary.json",
            "v5e_continuation_report.md",
            "v5e_forward_tracking_registry.csv",
            "v5e_511360_official_restore_status.csv",
            "v5f_deployment_governance_prep_matrix.csv",
            "v5f_paper_trading_workflow_preparation.csv",
            "v5e_continuation_allowed_blocked_actions.csv",
            "v5e_continuation_final_decision.csv",
            "v5e_continuation_next_queue.csv",
            "v5e_continuation_next_prompt.md",
            "v5e_continuation_agent_execution_rules.md",
            "v5e_continuation_blockers.csv",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_511360_official_restore_status.csv").open("r", encoding="utf-8-sig", newline="") as f:
            restore = list(csv.DictReader(f))[0]
        self.assertEqual(restore["restore_status"], "forward_only_pending")
        self.assertEqual(restore["historical_backtest_blocker"], "False")
        self.assertEqual(restore["accepted"], "False")

        with (out / "v5e_continuation_next_queue.csv").open("r", encoding="utf-8-sig", newline="") as f:
            queue = {row["next_task"]: row for row in csv.DictReader(f)}
        self.assertEqual(queue["V5f deployment governance / paper trading workflow packet"]["allowed"], "True")
        self.assertEqual(queue["V5e 511360 official restore closeout"]["allowed"], "False")
        self.assertEqual(queue["V5e threshold scan"]["allowed"], "False")


if __name__ == "__main__":
    unittest.main()
