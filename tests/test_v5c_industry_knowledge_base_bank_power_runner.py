from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_industry_knowledge_base_bank_power_runner import run


class V5cIndustryKnowledgeBaseBankPowerRunnerTest(unittest.TestCase):
    def test_generates_bank_power_observation_knowledge_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary_path = run(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_p0_industry_knowledge_base")
            self.assertEqual(summary["pm_gate_decision"], "admit_bank_power_industry_knowledge_to_v5c_observation_layer_only")
            self.assertFalse(summary["can_change_weights"])
            self.assertFalse(summary["can_trigger_trade"])
            self.assertTrue(summary["dedicated_bank_power_book_gap"])

            out = root / "v5c_industry_knowledge_base_bank_power_p0" / "current"
            tags = _read_csv(out / "v5c_industry_state_tag_mapping.csv")
            self.assertIn("bank", {row["industry"] for row in tags})
            self.assertIn("utilities_electricity", {row["industry"] for row in tags})
            self.assertTrue(all(row["can_trigger_trade"] == "False" for row in tags))
            self.assertTrue(all(row["can_modify_weight"] == "False" for row in tags))

            policy = _read_csv(out / "v5c_industry_evidence_layer_policy.csv")
            book = next(row for row in policy if row["evidence_layer"] == "book_framework")
            self.assertIn("numeric threshold", book["blocked_use"])

            kb = root / "knowledge" / "research_agent" / "v5c_industry_bank_power_p0"
            self.assertTrue((kb / "INDEX.md").exists())
            self.assertTrue((kb / "v5c_industry_knowledge_cards.csv").exists())


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
