from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v5.experiment_governance import validate_daily_run_contract, validate_experiment_layer
from v5.formal_validation_runner import _common_sample_interaction_tests, _notice_date_leakage_audit, run_formal_validation


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

    def test_bank_quality_notice_date_is_audited_separately(self):
        rows = [
            {
                "trade_date": "2025-03-31",
                "code": "A",
                "factor_visible_date": "2025-03-31",
                "provision_coverage_ratio": "300",
                "bank_quality_notice_date": "2025-04-01",
            }
        ]

        audit = _notice_date_leakage_audit(rows)

        self.assertEqual(audit[0]["status"], "needs_review")
        self.assertEqual(audit[0]["future_notice_violations"], 1)

    def test_common_sample_interactions_use_same_rows(self):
        raw = {
            "signals": {
                "factors": [
                    {"name": "dividend_yield", "direction": "higher_is_better"},
                    {"name": "return_on_equity_ttm", "direction": "higher_is_better"},
                    {"name": "low_price_to_book", "direction": "lower_is_better"},
                    {"name": "provision_coverage_ratio", "direction": "higher_is_better"},
                    {"name": "core_tier_1_capital_adequacy_ratio", "direction": "higher_is_better"},
                ],
                "scoring": {
                    "weights": {
                        "dividend_yield": 0.35,
                        "return_on_equity_ttm": 0.2,
                        "low_price_to_book": 0.2,
                        "provision_coverage_ratio": 0.15,
                        "core_tier_1_capital_adequacy_ratio": 0.1,
                    }
                },
            },
            "portfolio": {"selection_count": 2},
        }
        rows = []
        for trade_date in ["2025-04-01", "2025-07-01", "2025-10-08", "2026-01-05"]:
            for index in range(3):
                rows.append(
                    {
                        "trade_date": trade_date,
                        "code": f"B{index}",
                        "future_return": 0.01 * (index + 1),
                        "dividend_yield": 0.04 + index * 0.01,
                        "return_on_equity_ttm": 8 + index,
                        "low_price_to_book": 1.0 - index * 0.1,
                        "provision_coverage_ratio": 200 + index * 10,
                        "core_tier_1_capital_adequacy_ratio": 9 + index,
                    }
                )

        result = _common_sample_interaction_tests(rows, raw)

        self.assertEqual({row["common_sample_rows"] for row in result}, {12})
        self.assertEqual({row["common_sample_dates"] for row in result}, {4})
        self.assertTrue(all(row["status"] == "completed" for row in result))


if __name__ == "__main__":
    unittest.main()
