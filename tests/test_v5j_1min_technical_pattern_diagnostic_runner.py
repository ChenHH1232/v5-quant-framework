from __future__ import annotations

import unittest

from v5.v5j_1min_technical_pattern_diagnostic_runner import _decision, _ema, _rsi


class V5jOneMinuteTechnicalPatternDiagnosticTests(unittest.TestCase):
    def test_ema_uses_visible_series_only(self) -> None:
        self.assertGreater(_ema([1.0, 2.0, 3.0], 2), 2.0)

    def test_rsi_handles_rising_series(self) -> None:
        self.assertEqual(_rsi([float(value) for value in range(20)], 14), 100.0)

    def test_large_but_unstable_spread_does_not_promote(self) -> None:
        results = [
            {'feature_id': 'rsi_14', 'state': 'oversold', 'event_count': 300, 'mean_next_day_forward_return_bps': -10.0},
            {'feature_id': 'rsi_14', 'state': 'overbought', 'event_count': 300, 'mean_next_day_forward_return_bps': 40.0},
        ]
        cells = [
            {'feature_id': 'rsi_14', 'year': '2013', 'sleeve_id': str(index), 'state': 'oversold', 'mean_next_day_forward_return_bps': 0.0}
            for index in range(10)
        ] + [
            {'feature_id': 'rsi_14', 'year': '2013', 'sleeve_id': str(index), 'state': 'overbought', 'mean_next_day_forward_return_bps': 1.0}
            for index in range(10)
        ]
        decision = _decision(results, cells, [{'audit_id': 'minute_and_next_close_coverage', 'status': 'pass'}])
        self.assertEqual(decision['pm_gate_decision'], 'diagnostic_only_no_stable_technical_edge')


if __name__ == '__main__':
    unittest.main()
