from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5k_reproducibility_provenance_runner import run_v5k_reproducibility_provenance


class V5kReproducibilityProvenanceRunnerTest(unittest.TestCase):
    def test_records_non_destructive_provenance_snapshot(self) -> None:
        summary = run_v5k_reproducibility_provenance(Path("."))
        self.assertEqual(summary["input_manifest_count"], 4)
        self.assertFalse(summary["accepted"])
        self.assertTrue((Path("v5k_reproducibility_provenance") / "current" / "v5k_git_worktree_state.csv").exists())


if __name__ == "__main__":
    unittest.main()
