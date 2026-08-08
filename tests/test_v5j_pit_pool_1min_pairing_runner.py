from __future__ import annotations

import unittest

from v5.v5j_pit_pool_1min_pairing_runner import _paired, _years_inclusive


class V5jPitPoolOneMinutePairingRunnerTests(unittest.TestCase):
    def test_years_include_a_cross_year_holding_period(self) -> None:
        self.assertEqual(_years_inclusive("2020-10-09", "2021-01-04"), [2020, 2021])

    def test_years_keep_a_same_year_holding_period_compact(self) -> None:
        self.assertEqual(_years_inclusive("2019-04-01", "2019-07-01"), [2019])

    def test_terminal_company_action_is_an_explicit_source_resolution(self) -> None:
        self.assertTrue(_paired({"minute_pairing_status": "pass_terminal_corporate_action_no_postexit_bars_expected"}))


if __name__ == "__main__":
    unittest.main()
