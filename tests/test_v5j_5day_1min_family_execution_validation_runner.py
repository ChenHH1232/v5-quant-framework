from __future__ import annotations

import unittest

from v5.v5j_5day_1min_family_execution_validation_runner import _state


class V5jFiveDayOneMinuteFamilyExecutionValidationTests(unittest.TestCase):
    def test_price_volume_confirmation_requires_both(self) -> None:
        days = [{'pressure': 0.1, 'close': 11.0, 'vwap': 10.0, 'volume': 100.0} for _ in range(4)]
        days.append({'pressure': 0.1, 'close': 11.0, 'vwap': 10.0, 'volume': 120.0})
        self.assertEqual(_state(days)['agreement'], 'up_volume_confirmed')
        days[-1]['volume'] = 80.0
        self.assertEqual(_state(days)['agreement'], 'not_up_volume_confirmed')


if __name__ == '__main__':
    unittest.main()
