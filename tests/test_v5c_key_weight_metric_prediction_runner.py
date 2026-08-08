from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_key_weight_metric_prediction_runner import OUT_DIR, run_v5c_key_weight_metric_prediction


class V5cKeyWeightMetricPredictionRunnerTest(unittest.TestCase):
    def test_runner_predicts_key_metric_buckets_without_weight_use(self) -> None:
        summary = run_v5c_key_weight_metric_prediction(Path("."))

        self.assertEqual(summary["status"], "completed_key_weight_metric_prediction")
        self.assertEqual(summary["pm_gate_decision"], "key_metric_bucket_forward_tracking_ready_not_weight_use")
        self.assertGreater(summary["formal_rows"], 0)
        self.assertGreater(summary["pre2021_rows"], 0)
        self.assertGreater(summary["recommended_metric_count"], 0)
        self.assertFalse(summary["overall_financial_state_prediction_used"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_primary_modified"])
        self.assertFalse(summary["trade_rule_added"])
        self.assertFalse(summary["weight_change_added"])
        self.assertEqual(summary["fatal_blocker_count"], 0)
        self.assertEqual(summary["v5f_weight_confidence_spec_status"], "still_blocked")

        out = Path(".") / OUT_DIR
        expected = [
            "v5c_key_weight_metric_prediction_summary.json",
            "v5c_key_weight_metric_prediction_report.md",
            "v5c_key_weight_metric_schema.csv",
            "v5c_key_weight_metric_accuracy.csv",
            "v5c_key_weight_metric_recommended_tracking.csv",
            "v5c_key_weight_metric_forward_tracking_ledger.csv",
            "v5c_key_weight_metric_pm_gate_decision.csv",
            "v5c_key_weight_metric_v5f_freeze_decision.csv",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        with (out / "v5c_key_weight_metric_forward_tracking_ledger.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            ledger = list(csv.DictReader(handle))
        self.assertTrue(ledger)
        self.assertTrue(all(row["trade_impact"] == "none" for row in ledger))
        self.assertTrue(all(row["weight_impact"] == "none" for row in ledger))

        with (out / "v5c_key_weight_metric_recommended_tracking.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            recommended = list(csv.DictReader(handle))
        self.assertGreater(sum(1 for row in recommended if row["recommend_forward_tracking"] == "True"), 0)
        self.assertTrue(all(row["recommend_weight_use"] == "False" for row in recommended))


if __name__ == "__main__":
    unittest.main()
