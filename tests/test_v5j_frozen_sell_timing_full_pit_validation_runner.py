from __future__ import annotations
import unittest
from v5.v5j_frozen_sell_timing_full_pit_validation_runner import _median
class V5jFrozenSellTimingFullPitValidationTests(unittest.TestCase):
 def test_median(self):self.assertEqual(_median([1.,3.,2.]),2.)
if __name__=="__main__":unittest.main()
