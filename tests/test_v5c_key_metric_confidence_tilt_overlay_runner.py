from __future__ import annotations

import csv
import unittest
from pathlib import Path

from v5.v5c_key_metric_confidence_tilt_overlay_runner import (
    OUT_DIR,
    PRIMARY,
    VARIANTS,
    run_v5c_key_metric_confidence_tilt_overlay,
)


class V5cKeyMetricConfidenceTiltOverlayRunnerTest(unittest.TestCase):
    def test_runner_tests_fixed_confidence_tilts_without_acceptance(self) -> None:
        summary = run_v5c_key_metric_confidence_tilt_overlay(Path("."))

        self.assertEqual(summary["status"], "completed_key_metric_confidence_tilt_overlay")
        self.assertIn(
            summary["pm_gate_decision"],
            {
                "key_metric_confidence_tilt_positive_forward_observation_not_accepted",
                "key_metric_confidence_tilt_no_incremental_value_diagnostic",
            },
        )
        self.assertEqual(summary["tested_variant_count"], len(VARIANTS))
        self.assertGreater(summary["support_score_rows"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["live_approved"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_primary_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_stock_selected"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path(".") / OUT_DIR
        expected = [
            "v5c_key_metric_confidence_tilt_summary.json",
            "v5c_key_metric_confidence_tilt_report.md",
            "v5c_key_metric_confidence_tilt_rule_spec.csv",
            "v5c_key_metric_confidence_support_score_panel.csv",
            "v5c_key_metric_confidence_tilt_weights.csv",
            "v5c_key_metric_confidence_tilt_metrics.csv",
            "v5c_key_metric_confidence_tilt_comparison.csv",
            "v5c_key_metric_confidence_tilt_governance_audit.csv",
            "v5c_key_metric_confidence_tilt_pm_gate_decision.csv",
        ]
        for name in expected:
            self.assertTrue((out / name).exists(), name)

        comparison = _read_csv(out / "v5c_key_metric_confidence_tilt_comparison.csv")
        versions = {row["version_id"] for row in comparison}
        self.assertIn(PRIMARY, versions)
        for variant in VARIANTS:
            self.assertIn(variant["version_id"], versions)
        self.assertTrue(all(row["accepted"] == "False" for row in comparison))

        governance = _read_csv(out / "v5c_key_metric_confidence_tilt_governance_audit.csv")
        self.assertTrue(all(row["status"] == "pass" for row in governance))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
