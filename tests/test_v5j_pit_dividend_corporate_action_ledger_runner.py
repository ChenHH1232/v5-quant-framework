from __future__ import annotations
import unittest
from v5.v5j_pit_dividend_corporate_action_ledger_runner import _event
class V5jPitDividendCorporateActionLedgerTests(unittest.TestCase):
    def test_event_uses_announcement_as_visibility_date(self) -> None:
        row = _event("600000.XSHG", 2020, {"dividCashPsBeforeTax":"0.2", "dividPlanAnnounceDate":"2020-03-15"})
        self.assertEqual(row["announcement_visible_date"], "2020-03-15")
        self.assertEqual(row["corporate_action_type"], "cash_dividend")
if __name__ == "__main__": unittest.main()
