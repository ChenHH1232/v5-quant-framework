from pathlib import Path
import unittest

from src.v5.v5i_sell_execution_evaluation_runner import run_v5i_sell_execution_evaluation
from src.v5.v5i_sell_execution_closeout_runner import run_v5i_sell_execution_closeout


class V5iSellExecutionCloseoutRunnerTest(unittest.TestCase):
    def test_negative_fixed_family_is_not_admitted_to_joinquant(self) -> None:
        run_v5i_sell_execution_evaluation(Path("."))
        result = run_v5i_sell_execution_closeout(Path("."))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["pm_gate_decision"], "v5i_technical_sell_execution_closeout_diagnostic_only")
        self.assertFalse(result["joinquant_historical_backtest_admitted"])
        self.assertFalse(result["accepted"])
        self.assertFalse(result["live_trading_approved"])
        out = Path("v5i_sell_execution_closeout") / "current"
        self.assertTrue((out / "v5i_sell_execution_closeout_report.md").exists())
        self.assertTrue((out / "v5i_sell_execution_closeout_pm_gate.csv").exists())


if __name__ == "__main__":
    unittest.main()
