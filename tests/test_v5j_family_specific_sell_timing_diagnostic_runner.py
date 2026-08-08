from __future__ import annotations

import unittest

from v5.v5j_family_specific_sell_timing_diagnostic_runner import _signals_before_entry


class V5jFamilySpecificSellTimingDiagnosticTests(unittest.TestCase):
    def test_signals_use_only_history_before_entry(self) -> None:
        daily = {'000001.XSHE': [{'date': f'2012-01-{index:02d}', 'close': float(index)} for index in range(1, 29)]}
        factors = {('000001.XSHE', f'2012-01-{index:02d}'): 1.0 for index in range(1, 29)}
        momentum, reversion = _signals_before_entry('000001.XSHE', '2012-02-01', daily, factors)
        self.assertIsNone(momentum)
        self.assertIsNone(reversion)


if __name__ == '__main__':
    unittest.main()
