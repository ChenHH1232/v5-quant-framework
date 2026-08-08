from __future__ import annotations

import unittest
import hashlib
import tempfile
from pathlib import Path

from v5.v5k_workflow_activation_runner import run_v5k_workflow_activation


class V5kWorkflowActivationRunnerTest(unittest.TestCase):
    def test_test_mode_cannot_mutate_formal_current_outputs(self) -> None:
        root = Path(".")
        formal = root / "v5k_workflow_activation_repair" / "current"
        before = _hashes(formal)
        summary = run_v5k_workflow_activation(root, execute_tests=False)
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["baseline_id"], "v57f_startup_preload_repaired_baseline")
        self.assertEqual(summary["market_data_scope_end"], "2026-05-31")
        self.assertFalse(summary["accepted"])
        self.assertEqual(before, _hashes(formal))

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "activation_test_output"
            isolated = run_v5k_workflow_activation(root, execute_tests=False, output_dir=output)
            self.assertEqual(isolated["status"], "workflow_activation_blocked")
            self.assertTrue((output / "v5k_workflow_activation_summary.json").exists())
        self.assertEqual(before, _hashes(formal))


def _hashes(folder: Path) -> dict[str, str]:
    return {
        str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.rglob("*") if path.is_file()
    }


if __name__ == "__main__":
    unittest.main()
