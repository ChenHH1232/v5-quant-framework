from __future__ import annotations

import unittest

from v5.v5j_momentum_overlay_cash_neutral_execution_spec_runner import _boundaries, _rules


class V5jMomentumOverlayCashNeutralSpecTests(unittest.TestCase):
    def test_value_base_and_mean_reversion_are_excluded(self) -> None:
        boundaries = {row['component']: row['status'] for row in _boundaries()}
        self.assertEqual(boundaries['V57f repaired value base'], 'immutable')
        self.assertEqual(boundaries['mean reversion overlay'], 'closed')

    def test_cash_neutral_rule_is_required(self) -> None:
        rules = {row['rule_id']: row['required'] for row in _rules()}
        self.assertTrue(rules['cash_neutral'])


if __name__ == '__main__':
    unittest.main()
