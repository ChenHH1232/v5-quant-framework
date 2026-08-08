from pathlib import Path
import unittest

from src.v5.v5i_sell_execution_evaluation_runner import run_v5i_sell_execution_evaluation
from src.v5.v5i_sell_intent_provenance_runner import run_v5i_sell_intent_provenance


class V5iSellExecutionEvaluationRunnerTest(unittest.TestCase):
    def test_evaluates_only_immutable_v5e_sell_intents(self) -> None:
        run_v5i_sell_intent_provenance(Path("."))
        summary = run_v5i_sell_execution_evaluation(Path("."))
        self.assertEqual(summary["status"], "completed_fixed_candidate_evaluation")
        self.assertEqual(summary["intent_count"], 87)
        self.assertFalse(summary["accepted"])
        self.assertFalse(summary["v57f_core_modified"])
        self.assertFalse(summary["v5f_mainline_modified"])
        self.assertFalse(summary["v5e_exit_rule_modified"])
        self.assertFalse(summary["new_sell_signal_used"])
        self.assertFalse(summary["threshold_scan_used"])
        out = Path("v5i_sell_execution_evaluation") / "current"
        self.assertTrue((out / "v5i_sell_execution_event_evaluation.csv").exists())
        self.assertTrue((out / "v5i_sell_execution_candidate_results.csv").exists())
        self.assertTrue((out / "v5i_sell_execution_pm_gate_decision.csv").exists())


if __name__ == "__main__":
    unittest.main()
