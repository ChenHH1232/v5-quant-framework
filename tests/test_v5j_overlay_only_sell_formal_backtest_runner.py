from __future__ import annotations

import unittest

from v5.v5j_overlay_only_sell_formal_backtest_runner import _overlay_snapshots


class V5jOverlayOnlySellFormalBacktestTests(unittest.TestCase):
    def test_value_base_is_removed_from_overlay(self) -> None:
        base = {'2021-01-01': {'a': 0.4}}
        target = {'2021-01-01': {'a': 0.5, 'b': 0.1}}
        overlay = _overlay_snapshots(base, target)['2021-01-01']
        self.assertAlmostEqual(overlay['a'], 0.1)
        self.assertAlmostEqual(overlay['b'], 0.1)


if __name__ == '__main__':
    unittest.main()
