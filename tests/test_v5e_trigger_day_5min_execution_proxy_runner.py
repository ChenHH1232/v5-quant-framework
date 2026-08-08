from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_trigger_day_5min_execution_proxy_runner import (
    MAIN_CANDIDATE,
    run_v5e_trigger_day_5min_execution_proxy,
)


class V5eTriggerDay5minExecutionProxyRunnerTest(unittest.TestCase):
    def test_runner_uses_minute_data_only_for_execution_proxy(self) -> None:
        root = Path(".")
        summary = run_v5e_trigger_day_5min_execution_proxy(root)

        self.assertEqual(summary["status"], "completed_5min_execution_proxy_test")
        self.assertEqual(summary["pm_decision"], "switch_primary_to_profit_lock_main_execution_robust_review_candidate")
        self.assertFalse(summary["minute_data_used_for_trigger"])
        self.assertFalse(summary["full_holding_period_checked"])
        self.assertFalse(summary["full_rebacktest"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertGreater(summary["secondary_candidate_vwap_delta_vs_v57f_baseline"], 0)

        out = root / "v5e_trigger_day_5min_execution_proxy_test" / "current"
        with (out / "v5e_5min_execution_proxy_candidate_impact.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        main_vwap = next(row for row in rows if row["version_id"] == MAIN_CANDIDATE and row["proxy_id"] == "day_5min_vwap")
        self.assertEqual(main_vwap["estimate_scope"], "execution_price_delta_only_not_full_rebacktest")
        self.assertEqual(main_vwap["threshold_status"], "pre_registered_not_optimized")


if __name__ == "__main__":
    unittest.main()
