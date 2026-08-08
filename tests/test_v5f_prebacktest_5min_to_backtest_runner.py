from __future__ import annotations

import unittest
from pathlib import Path

from src.v5.v5f_prebacktest_5min_to_backtest_runner import run_v5f_prebacktest_5min_to_backtest


class V5fPrebacktest5minToBacktestRunnerTest(unittest.TestCase):
    def test_runner_keeps_governance_flags_false(self) -> None:
        root = Path(__file__).resolve().parents[1]
        summary = run_v5f_prebacktest_5min_to_backtest(root)

        self.assertEqual(summary["status"], "completed_prebacktest_5min_validation_then_formal_backtest")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertGreater(summary["validation_feature_rows"], 0)
        self.assertGreater(summary["backtest_feature_rows"], 0)


if __name__ == "__main__":
    unittest.main()
