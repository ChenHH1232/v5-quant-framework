from __future__ import annotations

import unittest

from v5.v5j_v4_bank_indicator_pit_reuse_gate_runner import _select_visible_records


class V5jV4BankIndicatorPitReuseGateRunnerTest(unittest.TestCase):
    def test_future_bank_record_is_excluded(self) -> None:
        pool = [{"rebalance_date": "2020-04-01", "code": "600000.XSHG"}]
        records = [
            {
                "code": "600000.XSHG",
                "pub_date": "2020-03-30",
                "stat_date": "2019-12-31",
                "Nonperforming_loan_rate": "1.0",
                "non_performing_loan_provision_coverage": "200",
                "core_level_capital_adequacy_ratio": "9.0",
                "source_type": "source",
            },
            {
                "code": "600000.XSHG",
                "pub_date": "2020-04-02",
                "stat_date": "2019-12-31",
                "Nonperforming_loan_rate": "99.0",
                "non_performing_loan_provision_coverage": "99",
                "core_level_capital_adequacy_ratio": "99",
                "source_type": "future",
            },
        ]
        selected = _select_visible_records(pool, records)
        self.assertEqual(selected[0]["statement_pub_date"], "2020-03-30")
        self.assertEqual(selected[0]["Nonperforming_loan_rate"], "1.0")
        self.assertEqual(selected[0]["pit_status"], "pass")


if __name__ == "__main__":
    unittest.main()
