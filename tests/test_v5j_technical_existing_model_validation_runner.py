from pathlib import Path
import unittest

from src.v5.v5j_technical_existing_model_validation_runner import run_v5j_technical_existing_model_validation


class V5jTechnicalExistingModelValidationRunnerTest(unittest.TestCase):
    def test_validates_the_frozen_buy_execution_rule_without_changing_v5f(self) -> None:
        summary = run_v5j_technical_existing_model_validation(Path("."))
        self.assertEqual(summary["status"], "completed_pre2021_fixed_v5h_validation")
        self.assertEqual(summary["frozen_technical_rule"], "pressure_positive_1000_else_1400_buy")
        self.assertGreater(summary["entry_proxy_count"], 0)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["new_buy_signal_used"])
        self.assertFalse(summary["threshold_scan_used"])
        self.assertFalse(summary["joinquant_started"])
        out = Path("v5j_technical_existing_model_validation") / "current"
        self.assertTrue((out / "v5j_pre2021_fixed_v5h_result.csv").exists())
        self.assertTrue((out / "v5j_technical_pm_gate_decision.csv").exists())


if __name__ == "__main__":
    unittest.main()
