from __future__ import annotations

import unittest

from v5.v5j_family_sell_execution_formal_backtest_runner import _sell_intents


class V5jFamilySellExecutionFormalBacktestTests(unittest.TestCase):
    def test_sells_include_removed_and_reduced_names(self) -> None:
        snapshots = {'2021-01-01': {'a': 0.5, 'b': 0.5}, '2021-04-01': {'a': 0.2, 'c': 0.8}}
        intents = _sell_intents('test', snapshots)
        weights = {row['code']: row['sell_weight'] for row in intents}
        self.assertAlmostEqual(weights['a'], 0.3)
        self.assertAlmostEqual(weights['b'], 0.5)


if __name__ == '__main__':
    unittest.main()
