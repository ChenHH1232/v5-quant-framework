from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_bank_power_dedicated_book_card_collection_runner import run


class V5cBankPowerDedicatedBookCardCollectionRunnerTest(unittest.TestCase):
    def test_generates_observation_only_bank_power_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p0 = root / "v5c_industry_knowledge_base_bank_power_p0" / "current"
            p0.mkdir(parents=True)
            (p0 / "v5c_industry_knowledge_summary.json").write_text(
                json.dumps({"status": "completed_p0_industry_knowledge_base"}),
                encoding="utf-8",
            )

            summary_path = run(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_dedicated_book_report_card_collection")
            self.assertEqual(
                summary["pm_gate_decision"],
                "admit_dedicated_bank_power_book_cards_to_v5c_observation_knowledge_base",
            )
            self.assertFalse(summary["can_change_weights"])
            self.assertFalse(summary["can_trigger_trade"])
            self.assertFalse(summary["can_set_threshold"])
            self.assertFalse(summary["accepted"])

            out = root / "v5c_bank_power_dedicated_book_card_collection" / "current"
            bank_cards = _read_csv(out / "v5c_bank_industry_book_cards.csv")
            power_cards = _read_csv(out / "v5c_power_industry_book_cards.csv")
            report_cards = _read_csv(out / "v5c_bank_power_report_article_cards.csv")

            self.assertGreaterEqual(len(bank_cards), 5)
            self.assertGreaterEqual(len(power_cards), 5)
            self.assertGreaterEqual(len(report_cards), 6)
            self.assertTrue(all(row["can_trigger_trade"] == "False" for row in bank_cards + power_cards))
            self.assertTrue(all(row["can_change_weight"] == "False" for row in bank_cards + power_cards))
            self.assertIn("numeric threshold", bank_cards[0]["blocked_use"])

            source_register = _read_csv(out / "v5c_bank_power_dedicated_source_register.csv")
            self.assertIn("bank", {row["industry"] for row in source_register})
            self.assertIn("utilities_electricity", {row["industry"] for row in source_register})

            kb = root / "knowledge" / "research_agent" / "v5c_industry_bank_power_dedicated_cards"
            self.assertTrue((kb / "INDEX.md").exists())
            self.assertTrue((kb / "v5c_bank_power_pit_data_gate_queue.csv").exists())


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
