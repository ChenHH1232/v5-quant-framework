from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5j_momentum_overlay_partial_buy_skip_runner import run_v5j_momentum_overlay_partial_buy_skip


class V5jMomentumOverlayPartialBuySkipRunnerTest(unittest.TestCase):
    def test_partial_buy_skip_closes_historical_same_sleeve_cash_ledger(self) -> None:
        summary = run_v5j_momentum_overlay_partial_buy_skip(Path("."))
        self.assertEqual(summary["market_data_max_date"], "2026-05-31")
        self.assertTrue(summary["strict_cash_reconciliation_pass"])
        self.assertGreater(summary["partial_or_skipped_buy_count"], 0)
        self.assertEqual(summary["value_base_change_count"], 0)
        self.assertEqual(summary["cross_sleeve_transfer_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])


if __name__ == "__main__":
    unittest.main()
