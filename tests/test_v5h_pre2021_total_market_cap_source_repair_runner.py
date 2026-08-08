from __future__ import annotations

import csv
import unittest
from pathlib import Path

from src.v5.v5h_pre2021_total_market_cap_source_repair_runner import (
    run_v5h_pre2021_total_market_cap_source_repair,
)


class V5hPre2021TotalMarketCapSourceRepairRunnerTest(unittest.TestCase):
    def test_runner_repairs_pre2021_total_market_cap_without_rule_change(self) -> None:
        summary = run_v5h_pre2021_total_market_cap_source_repair(Path("."))

        self.assertEqual(summary["status"], "completed_pre2021_total_market_cap_source_repair")
        self.assertIn(summary["repair_decision"], {"baostock_total_share_repair_success", "baostock_total_share_repair_partial"})
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["trading_frequency_increased"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["joinquant_started"])
        self.assertGreater(summary["repaired_rows"], 0)

        out = Path("v5h_pre2021_total_market_cap_source_repair") / "current"
        for name in [
            "v5h_pre2021_total_market_cap_source_repair_summary.json",
            "v5h_pre2021_total_market_cap_source_repair_report.md",
            "v5h_pre2021_total_market_cap_missing_rows_before.csv",
            "v5h_pre2021_total_market_cap_baostock_fetch_audit.csv",
            "v5h_pre2021_total_market_cap_repaired_rows.csv",
            "v5h_pre2021_total_market_cap_repair_decision.csv",
            "v5h_pre2021_total_market_cap_repair_blockers.csv",
            "v5h_pre2021_total_market_cap_repair_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5h_pre2021_total_market_cap_repaired_rows.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            repaired = list(csv.DictReader(handle))
        self.assertTrue(all(row["market_cap_pit_status"] == "pass" for row in repaired))


if __name__ == "__main__":
    unittest.main()
