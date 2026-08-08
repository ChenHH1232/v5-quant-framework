from pathlib import Path
import unittest

from src.v5.v5i_sell_intent_provenance_runner import run_v5i_sell_intent_provenance


class V5iSellIntentProvenanceRunnerTest(unittest.TestCase):
    def test_primary_v5e_intents_are_pit_clean_and_v57f_same_day_sells_are_excluded(self) -> None:
        summary = run_v5i_sell_intent_provenance(Path("."))
        self.assertEqual(summary["status"], "completed_p0_intent_provenance")
        self.assertGreater(summary["primary_eligible_intent_count"], 0)
        self.assertEqual(summary["v57f_same_day_sell_primary_eligibility"], "excluded_pending_timestamped_preintraday_intent_provenance")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        out = Path("v5i_sell_execution_provenance") / "current"
        self.assertTrue((out / "v5i_immutable_sell_intent_ledger.csv").exists())
        self.assertTrue((out / "v5i_sell_intent_provenance_audit.csv").exists())


if __name__ == "__main__":
    unittest.main()
