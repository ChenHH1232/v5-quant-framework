from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from v5.utilities_golden_workflow_runner import _build_steps, run_utilities_golden_workflow_audit


class UtilitiesGoldenWorkflowRunnerTests(unittest.TestCase):
    def test_audit_passes_when_required_artifacts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for step in _build_steps():
                for rel_path in step.get("required", []):
                    path = root / rel_path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("ok\n", encoding="utf-8")

            report = run_utilities_golden_workflow_audit(root / "out", repo_root=root)
            summary = json.loads((root / "out" / "v51f_utilities_golden_workflow_execution_v1.json").read_text(encoding="utf-8"))[
                "summary"
            ]

            self.assertEqual(report.name, "v51f_utilities_golden_workflow_execution_v1.md")
            self.assertEqual(summary["status"], "golden_template_productized_with_pending_forward_and_platform_review")
            self.assertEqual(summary["blocked_steps"], 0)
            self.assertEqual(summary["pending_gates"], ["platform_replication_packet", "forward_review"])


if __name__ == "__main__":
    unittest.main()
