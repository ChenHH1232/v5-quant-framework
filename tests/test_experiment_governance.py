from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v5.experiment_governance import validate_daily_run_contract, validate_experiment_layer
from v5.formal_validation_runner import run_formal_validation


class ExperimentGovernanceTests(unittest.TestCase):
    def test_unknown_experiment_layer_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_experiment_layer("backtest")

    def test_research_pit_requires_notice_date_visibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            benchmark = Path(tmp) / "benchmark.csv"
            benchmark.write_text("date,code,close\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_daily_run_contract(
                    experiment_layer="research_pit_validation",
                    eastmoney_visibility_mode="joinquant_source_year",
                    execution_price_csv=None,
                    benchmark_csv=benchmark,
                    dividend_cash_csv=None,
                )

    def test_platform_replication_requires_execution_prices(self):
        with tempfile.TemporaryDirectory() as tmp:
            benchmark = Path(tmp) / "benchmark.csv"
            benchmark.write_text("date,code,close\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_daily_run_contract(
                    experiment_layer="platform_replication",
                    eastmoney_visibility_mode="joinquant_source_year",
                    execution_price_csv=None,
                    benchmark_csv=benchmark,
                    dividend_cash_csv=None,
                )

    def test_formal_validation_rejects_non_research_layer(self):
        with self.assertRaises(ValueError):
            run_formal_validation(
                Path("examples/bank_value_15y_strategy.json"),
                Path("data/processed/bank_value_15y/panel.csv"),
                Path("validation_formal"),
                experiment_layer="platform_replication",
            )


if __name__ == "__main__":
    unittest.main()
