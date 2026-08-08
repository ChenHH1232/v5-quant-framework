from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5e_sleeve_level_risk_release_quant_spec_runner import (
    run_v5e_sleeve_level_risk_release_quant_spec,
)


class V5eSleeveLevelRiskReleaseQuantSpecRunnerTest(unittest.TestCase):
    def test_quant_spec_admits_limited_engineering_without_scan(self) -> None:
        summary = run_v5e_sleeve_level_risk_release_quant_spec(Path("."))

        self.assertEqual(summary["status"], "completed_sleeve_level_risk_release_quant_spec")
        self.assertEqual(
            summary["pm_gate_decision"],
            "admit_sleeve_level_risk_release_to_limited_engineering_test_not_accepted",
        )
        self.assertEqual(summary["rule_count"], 2)
        self.assertTrue(summary["engineering_test_allowed"])
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["new_unapproved_threshold_added"])
        self.assertEqual(summary["fatal_blocker_count"], 0)

        out = Path("v5e_sleeve_level_risk_release_quant_spec") / "current"
        self.assertTrue((out / "v5e_sleeve_level_rule_spec.csv").exists())
        self.assertTrue((out / "v5e_sleeve_level_pre_registered_threshold_policy.csv").exists())
        self.assertTrue((out / "v5e_sleeve_level_next_prompt.md").exists())


if __name__ == "__main__":
    unittest.main()
