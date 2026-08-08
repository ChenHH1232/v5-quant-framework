from __future__ import annotations

import unittest
from pathlib import Path

from src.v5.v5f_needed_model_full_comparison_runner import run_v5f_needed_model_full_comparison


class V5fNeededModelFullComparisonRunnerTest(unittest.TestCase):
    def test_runner_completes_without_acceptance(self) -> None:
        root = Path(__file__).resolve().parents[1]
        summary = run_v5f_needed_model_full_comparison(root)

        self.assertEqual(summary["status"], "completed_needed_model_full_comparison")
        self.assertEqual(summary["primary_model"], "internal_subsleeve_mom12_70_30")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertGreater(summary["model_count"], 5)


if __name__ == "__main__":
    unittest.main()
