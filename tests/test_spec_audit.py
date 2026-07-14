from __future__ import annotations

import copy
import json
import unittest
import tempfile
from pathlib import Path

from v5.engine import run_strategy
from v5.audit import audit_strategy
from v5.spec import SpecError, parse_strategy_spec


EXAMPLE = Path("examples/v4_bank_candidate1.json")


def load_example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class SpecAuditTest(unittest.TestCase):
    def test_v4_example_parses_and_passes_without_blockers(self) -> None:
        spec = parse_strategy_spec(load_example())
        audit = audit_strategy(spec)

        self.assertEqual(spec.strategy_id, "v4_bank_candidate1")
        self.assertTrue(audit.passed)
        self.assertEqual({issue.code for issue in audit.warnings}, {"NO_FINANCIAL_DISCLOSURE_LAG"})

    def test_full_sample_normalization_blocks_run(self) -> None:
        raw = load_example()
        raw["signals"]["scoring"]["normalization_scope"] = "full_sample"

        audit = audit_strategy(parse_strategy_spec(raw))

        self.assertFalse(audit.passed)
        self.assertIn("FULL_SAMPLE_NORMALIZATION", {issue.code for issue in audit.blocking_issues})

    def test_missing_top_level_field_is_rejected(self) -> None:
        raw = copy.deepcopy(load_example())
        del raw["execution"]

        with self.assertRaisesRegex(SpecError, "execution"):
            parse_strategy_spec(raw)

    def test_run_manifest_includes_v5_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = run_strategy(EXAMPLE, Path(temp_dir))
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            report = (run_dir / "report.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["project_context"]["project"], "Bank Quant V5")
        self.assertIn("A research framework can generate strategies", report)


if __name__ == "__main__":
    unittest.main()
