from __future__ import annotations

import unittest

from v5.v5j_local_adjust_factor_corporate_action_runner import _ordinal


class V5jLocalAdjustFactorCorporateActionTests(unittest.TestCase):
    def test_ordinal_keeps_dates_comparable(self) -> None:
        self.assertLess(_ordinal("2017-12-04"), _ordinal("2018-01-02"))


if __name__ == "__main__":
    unittest.main()
