from __future__ import annotations

import unittest

from v5.v5j_overlay_only_sell_validation_runner import _overlay_sell_intents


class V5jOverlayOnlySellValidationTests(unittest.TestCase):
    def test_uses_overlay_reduction_not_base_weight(self) -> None:
        weights = [
            {'strategy_family': 'm', 'rebalance_date': '2020-01-01', 'code': 'a', 'sleeve_id': 's', 'overlay_weight': 0.1},
            {'strategy_family': 'm', 'rebalance_date': '2020-04-01', 'code': 'a', 'sleeve_id': 's', 'overlay_weight': -0.1},
        ]
        intents = _overlay_sell_intents(weights)
        self.assertEqual(len(intents), 1)
        self.assertAlmostEqual(intents[0]['sell_weight'], 0.2)


if __name__ == '__main__':
    unittest.main()
