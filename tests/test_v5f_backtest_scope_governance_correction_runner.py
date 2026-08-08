from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_backtest_scope_governance_correction_runner import (
    run_v5f_backtest_scope_governance_correction,
)


class V5fBacktestScopeGovernanceCorrectionRunnerTest(unittest.TestCase):
    def test_runner_reclassifies_2021_2026_as_backtest_not_oos(self) -> None:
        summary = run_v5f_backtest_scope_governance_correction(Path("."))

        self.assertEqual(summary["status"], "completed_backtest_scope_governance_correction")
        self.assertEqual(
            summary["global_rule"],
            "2021-05-01_to_2026-05-31_is_historical_backtest_not_oos_validation",
        )
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])

        out = Path("v5f_backtest_scope_governance_correction") / "current"
        for name in [
            "v5f_backtest_scope_correction_summary.json",
            "v5f_backtest_scope_governance_correction_report.md",
            "v5f_evidence_scope_rulebook.csv",
            "v5f_component_scope_reclassification.csv",
            "v4_component_scope_reclassification.csv",
            "v4_v5_scope_violation_audit.csv",
            "v5f_corrected_pm_gate_decision.csv",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_evidence_scope_rulebook.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rules = {row["scope_id"]: row for row in csv.DictReader(f)}
        self.assertEqual(
            rules["v57f_repaired_historical_backtest"]["forbidden_label"],
            "out_of_sample_or_formal_rolling_validation",
        )


if __name__ == "__main__":
    unittest.main()
