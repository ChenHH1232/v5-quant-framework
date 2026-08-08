from __future__ import annotations

import unittest
from pathlib import Path

from src.v5.v5f_pre2021_5min_blocker_completion_runner import (
    run_v5f_pre2021_5min_blocker_completion,
)


class V5fPre20215minBlockerCompletionRunnerTest(unittest.TestCase):
    def test_runner_completes_without_accepting_strategy(self) -> None:
        root = Path(__file__).resolve().parents[1]
        summary = run_v5f_pre2021_5min_blocker_completion(root)

        self.assertEqual(summary["status"], "completed_pre2021_5min_blocker_completion")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertGreater(summary["candidate_feature_rows"], 0)
        self.assertGreater(summary["resolved_data_blocker_count"], 0)


if __name__ == "__main__":
    unittest.main()
