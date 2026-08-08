from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_improvement_queue_execution_runner import run_v5f_improvement_queue_execution


class V5fImprovementQueueExecutionRunnerTest(unittest.TestCase):
    def test_runner_preserves_governance_and_records_real_blockers(self) -> None:
        summary = run_v5f_improvement_queue_execution(Path("."))
        self.assertEqual(summary["status"], "completed_four_item_improvement_queue_execution")
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertEqual(summary["formal_backtest_end"], "2026-05-31")

        out = Path("v5f_improvement_queue_execution") / "current"
        for name in [
            "v5f_execution_parity_reconciliation.csv",
            "v5f_momentum_sell_cash_path_audit.csv",
            "v5f_momentum_sell_cash_path_spec.csv",
            "v5f_monthly_momentum_trusted_subset_gate.csv",
            "v5f_spike_satellite_trusted_subset_gate.csv",
            "v5f_improvement_queue_summary.json",
            "v5f_improvement_queue_report.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_momentum_sell_cash_path_audit.csv").open(encoding="utf-8-sig", newline="") as handle:
            cash = next(csv.DictReader(handle))
        self.assertEqual(cash["status"], "blocked_cash_reconciliation_failed")

        with (out / "v5f_monthly_momentum_trusted_subset_gate.csv").open(encoding="utf-8-sig", newline="") as handle:
            monthly = next(csv.DictReader(handle))
        self.assertEqual(monthly["status"], "blocked_no_certified_trusted_equivalent_target_subset")


if __name__ == "__main__":
    unittest.main()
