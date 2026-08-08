from __future__ import annotations
import unittest
from v5.v5j_v5e_profit_lock_sell_timing_proxy_runner import _median
class V5jV5eProfitLockSellTimingProxyTests(unittest.TestCase):
 def test_median(self):self.assertEqual(_median([1.,2.,3.]),2.)
if __name__=='__main__':unittest.main()
