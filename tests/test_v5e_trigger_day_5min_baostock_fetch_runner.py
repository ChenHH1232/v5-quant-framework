from __future__ import annotations

import unittest

from v5.v5e_trigger_day_5min_baostock_fetch_runner import _fetch_blockers, _summary


class V5eTriggerDay5minBaoStockFetchRunnerTest(unittest.TestCase):
    def test_fetch_summary_preserves_v5e_governance_boundaries(self) -> None:
        fetch_rows = [{"status": "pass", "row_count": 48}]
        std_index = [{"row_count": 48}]
        audit_summary = {
            "pm_decision": "coverage_pass_ready_for_execution_proxy_test",
            "coverage_rate_pct": 100.0,
            "missing_window_rows": 0,
            "fetch_queue_count": 0,
        }

        summary = _summary(
            "completed_baostock_fetch_and_rerun_data_gate",
            fetch_rows,
            std_index,
            [],
            audit_summary,
        )

        self.assertTrue(summary["baostock_network_fetch_started"])
        self.assertFalse(summary["full_holding_period_fetch"])
        self.assertFalse(summary["minute_data_used_for_trigger"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertEqual(summary["post_fetch_coverage_rate_pct"], 100.0)

    def test_fetch_blockers_separate_failed_and_empty_responses(self) -> None:
        blockers = _fetch_blockers(
            [
                {"status": "pass"},
                {"status": "empty"},
                {"status": "query_error"},
            ]
        )
        blocker_ids = {row["blocker_id"] for row in blockers}

        self.assertIn("baostock_empty_5min_responses", blocker_ids)
        self.assertIn("baostock_fetch_failures", blocker_ids)


if __name__ == "__main__":
    unittest.main()
