from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5f_spike_mr_sleeve_threshold_effectiveness_runner import (
    run_v5f_spike_mr_sleeve_threshold_effectiveness,
)


class V5fSpikeMrSleeveThresholdEffectivenessRunnerTest(unittest.TestCase):
    def test_runner_audits_sleeve_specific_thresholds_without_promoting_rule(self) -> None:
        summary = run_v5f_spike_mr_sleeve_threshold_effectiveness(Path("."))

        self.assertEqual(summary["status"], "completed_v5f_spike_mr_sleeve_threshold_effectiveness_audit")
        self.assertEqual(
            summary["pm_gate_decision"],
            "sleeve_thresholds_valid_but_forward_mixed_keep_observation_only",
        )
        self.assertEqual(summary["primary_candidate"], "internal_subsleeve_mom12_70_30")
        self.assertEqual(summary["observation_id"], "spike_funded_mr_borrowing_observe_only")
        self.assertEqual(summary["backtest_end"], "2026-05-31")
        self.assertTrue(summary["sleeve_specific_thresholds_used"])
        self.assertFalse(summary["candidate_promoted"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_trading_approved"])
        self.assertFalse(summary["deployment_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["full_market_selection_used"])
        self.assertGreaterEqual(summary["historical_supported_sleeve_count"], 2)
        self.assertEqual(summary["forward_sample_status"], "initial_forward_negative_or_too_small")
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5f_spike_mr_sleeve_threshold_effectiveness_audit") / "current"
        for name in [
            "v5f_spike_mr_threshold_effectiveness_summary.json",
            "v5f_spike_mr_threshold_effectiveness_report.md",
            "v5f_spike_mr_threshold_sensitivity_by_sleeve.csv",
            "v5f_spike_mr_threshold_yearly_stability.csv",
            "v5f_spike_mr_historical_event_rate_by_sleeve_year.csv",
            "v5f_spike_mr_forward_event_rate_by_sleeve.csv",
            "v5f_spike_mr_historical_effectiveness_by_sleeve.csv",
            "v5f_spike_mr_forward_effectiveness_by_sleeve.csv",
            "v5f_spike_mr_common_vs_sleeve_threshold_comparison.csv",
            "v5f_spike_mr_sleeve_effectiveness_classification.csv",
            "v5f_spike_mr_threshold_governance_audit.csv",
            "v5f_spike_mr_threshold_pm_gate_decision.csv",
            "v5f_spike_mr_threshold_next_agent_queue.csv",
            "v5f_spike_mr_threshold_blockers.csv",
            "v5f_spike_mr_threshold_agent_execution_rules.md",
        ]:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5f_spike_mr_threshold_sensitivity_by_sleeve.csv").open("r", encoding="utf-8-sig", newline="") as f:
            thresholds = [
                row for row in csv.DictReader(f)
                if row["scheme"] == "anchored_prior_years" and row["test_year"] == "2026"
            ]
        self.assertEqual(len(thresholds), 4)
        by_sleeve = {row["sleeve"]: row for row in thresholds}
        self.assertLess(float(by_sleeve["bank"]["drop_abs_pct"]), float(by_sleeve["utilities_electricity"]["drop_abs_pct"]))
        self.assertLess(float(by_sleeve["bank"]["spike_abs_pct"]), float(by_sleeve["utilities_electricity"]["spike_abs_pct"]))
        self.assertTrue(all(row["uses_future_test_year_data"] == "False" for row in thresholds))

        with (out / "v5f_spike_mr_sleeve_effectiveness_classification.csv").open("r", encoding="utf-8-sig", newline="") as f:
            classification = {row["sleeve"]: row for row in csv.DictReader(f)}
        self.assertEqual(classification["utilities_electricity"]["historical_read"], "supported")
        self.assertIn(classification["port_rail_infrastructure"]["historical_read"], {"supported", "mixed_or_cost_sensitive"})
        self.assertEqual(classification["port_rail_infrastructure"]["forward_read"], "mixed_or_negative")

        with (out / "v5f_spike_mr_threshold_governance_audit.csv").open("r", encoding="utf-8-sig", newline="") as f:
            governance = {row["audit_id"]: row for row in csv.DictReader(f)}
        for audit_id in [
            "sleeve_specific_thresholds_used",
            "pit_threshold_training",
            "backtest_scope_not_oos",
            "primary_line_retained",
            "forward_observation_not_candidate",
            "historical_event_rates_available",
            "forward_event_rates_available",
            "no_threshold_scan_used",
            "accepted_false",
            "v57f_core_modified_false",
        ]:
            self.assertEqual(governance[audit_id]["status"], "pass", audit_id)


if __name__ == "__main__":
    unittest.main()
