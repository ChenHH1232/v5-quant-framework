from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5k_active_model_registry_runner import run_v5k_active_model_registry


class V5kActiveModelRegistryRunnerTest(unittest.TestCase):
    def test_registry_freezes_post_boundary_operations(self) -> None:
        summary = run_v5k_active_model_registry(Path("."))
        self.assertEqual(summary["primary_model"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["market_data_max_date"], "2026-05-31")
        self.assertFalse(summary["post_boundary_forward_target_generation_allowed"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])


if __name__ == "__main__":
    unittest.main()
