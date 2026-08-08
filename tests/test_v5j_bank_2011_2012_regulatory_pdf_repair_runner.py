from __future__ import annotations

import unittest

from v5.v5j_bank_2011_2012_regulatory_pdf_repair_runner import _coverage


class BankHistoricalRegulatoryPdfRepairTests(unittest.TestCase):
    def test_future_report_is_not_selected(self) -> None:
        pool = [{"rebalance_date": "2013-01-04", "code": "600000.XSHG"}]
        manifest = [{"code": "600000.XSHG", "report_year": "2012", "pit_visible_date": "2013-03-14"}]
        rows = _coverage(pool, manifest, [])
        self.assertEqual(rows[0]["selected_report_year"], "")
        self.assertFalse(rows[0]["future_report_used"])


if __name__ == "__main__":
    unittest.main()
