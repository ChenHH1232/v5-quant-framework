from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5k_experiment_catalog_runner import run_v5k_experiment_catalog


class V5kExperimentCatalogRunnerTest(unittest.TestCase):
    def test_has_one_non_accepted_active_mainline(self) -> None:
        summary = run_v5k_experiment_catalog(Path("."))
        self.assertEqual(summary["active_mainline"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["active_mainline_count"], 1)
        self.assertEqual(summary["market_data_scope_end"], "2026-05-31")
        self.assertFalse(summary["accepted"])


if __name__ == "__main__":
    unittest.main()
