from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5e_historical_closeout_governance_runner import (
    run_v5e_historical_closeout_governance,
)


class V5eHistoricalCloseoutGovernanceRunnerTest(unittest.TestCase):
    def test_runner_completes_historical_closeout_without_acceptance(self) -> None:
        summary = run_v5e_historical_closeout_governance(Path("."))

        self.assertEqual(summary["status"], "completed_v5e_historical_closeout_governance_packet")
        self.assertEqual(summary["historical_closeout_status"], "complete")
        self.assertEqual(summary["backtest_scope_start"], "2021-05-01")
        self.assertEqual(summary["backtest_scope_end"], "2026-05-31")
        self.assertEqual(summary["candidate_count"], 2)
        self.assertEqual(summary["diagnostic_count"], 2)
        self.assertEqual(summary["forward_only_blocker_count"], 1)
        self.assertFalse(summary["v5e_accepted"])
        self.assertFalse(summary["v5e_replacement_for_v57f"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["network_fetch_started"])
        self.assertFalse(summary["joinquant_started"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_historical_closeout_governance_packet") / "current"
        expected = [
            "v5e_historical_closeout_summary.json",
            "v5e_historical_closeout_report.md",
            "v5e_component_status_matrix.csv",
            "v5e_candidate_vs_diagnostic_matrix.csv",
            "v5e_backtest_scope_blocker_reclassification.csv",
            "v5e_202607_forward_only_reclassification.csv",
            "v5e_allowed_blocked_actions.csv",
            "v5e_final_governance_decision.csv",
            "v5e_next_stage_queue.csv",
            "v5e_agent_execution_rules.md",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5e_final_governance_decision.csv").open("r", encoding="utf-8-sig", newline="") as f:
            final = list(csv.DictReader(f))[0]
        self.assertEqual(final["historical_closeout_status"], "complete")
        self.assertEqual(final["v5e_accepted"], "False")
        self.assertEqual(final["v5e_replacement_for_v57f"], "False")
        self.assertEqual(final["cash_proxy_511360_accepted"], "False")
        self.assertEqual(final["sleeve_level_release_accepted"], "False")
        self.assertEqual(final["2026_07_restore_blocker_status"], "forward_only_not_backtest_blocker")

        with (out / "v5e_candidate_vs_diagnostic_matrix.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows = {row["component_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(rows["v5e_profit_lock_main_20pct_sell50"]["classification"], "forward_paper_candidate")
        self.assertEqual(rows["v5e_511360_cash_proxy"]["classification"], "forward_review_candidate")
        self.assertEqual(rows["full_intraday_trigger_rolling_nav"]["classification"], "diagnostic_only")
        self.assertEqual(rows["sleeve_level_risk_release"]["classification"], "diagnostic_only")


if __name__ == "__main__":
    unittest.main()
