from __future__ import annotations
import unittest
from v5.v5j_frozen_buy_timing_full_pit_validation_runner import _pressure
class V5jFrozenBuyTimingFullPitValidationTests(unittest.TestCase):
    def test_pressure_is_positive_for_rising_amount_weighted_prices(self):
        self.assertGreater(_pressure([{"close":"1","amount":"1"},{"close":"2","amount":"2"}]),0)
if __name__=="__main__":unittest.main()
