from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v5.experiment_governance import validate_daily_run_contract, validate_experiment_layer
from v5.formal_validation_runner import (
    _baseline_tests,
    _common_sample_interaction_tests,
    _notice_date_leakage_audit,
    run_formal_validation,
)


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

    def test_configured_utilities_common_sample_interactions_are_not_bank_specific(self):
        raw = {
            "signals": {
                "factors": [
                    {"name": "low_price_to_book", "direction": "lower_is_better"},
                    {"name": "dividend_yield", "direction": "higher_is_better"},
                    {"name": "interest_coverage", "direction": "higher_is_better"},
                ],
                "scoring": {
                    "weights": {
                        "low_price_to_book": 0.4,
                        "dividend_yield": 0.3,
                        "interest_coverage": 0.3,
                    }
                },
            },
            "portfolio": {"selection_count": 2},
            "validation": {
                "common_sample_fields": ["low_price_to_book", "dividend_yield", "interest_coverage"],
                "common_sample_interactions": [
                    {"name": "common_utilities_value_dividend", "factors": ["low_price_to_book", "dividend_yield"]},
                    {"name": "common_utilities_all_support", "factors": ["low_price_to_book", "dividend_yield", "interest_coverage"]},
                ],
            },
        }
        rows = []
        for trade_date in ["2024-04-01", "2024-07-01", "2024-10-08", "2025-01-02"]:
            for index in range(3):
                rows.append(
                    {
                        "trade_date": trade_date,
                        "code": f"U{index}",
                        "future_return": 0.01 * (index + 1),
                        "low_price_to_book": 1.0 - index * 0.1,
                        "dividend_yield": 0.03 + index * 0.01,
                        "interest_coverage": 3 + index,
                    }
                )

        result = _common_sample_interaction_tests(rows, raw)

        self.assertEqual([row["case"] for row in result], ["common_utilities_value_dividend", "common_utilities_all_support"])
        self.assertEqual({row["required_common_fields"] for row in result}, {"low_price_to_book;dividend_yield;interest_coverage"})
        self.assertTrue(all(row["status"] == "completed" for row in result))

    def test_configured_high_dividend_baseline_selects_high_values(self):
        raw = {
            "signals": {
                "factors": [{"name": "dividend_yield", "direction": "higher_is_better"}],
                "scoring": {"weights": {"dividend_yield": 1.0}},
            },
            "portfolio": {"selection_count": 1},
            "validation": {
                "baselines": [
                    {
                        "name": "high_dividend_utilities_top1",
                        "mode": "single_factor",
                        "factor": "dividend_yield",
                        "selection_count": 1,
                    }
                ]
            },
        }
        rows = [
            {"trade_date": "2025-04-01", "code": "LOW", "future_return": -0.05, "dividend_yield": 0.01},
            {"trade_date": "2025-04-01", "code": "HIGH", "future_return": 0.07, "dividend_yield": 0.08},
        ]

        result = _baseline_tests(rows, raw)

        self.assertEqual(result[0]["case"], "high_dividend_utilities_top1")
        self.assertEqual(result[0]["mean_return"], 0.07)

    def test_configured_baseline_direction_can_cover_raw_factor_not_in_spec(self):
        raw = {
            "signals": {
                "factors": [{"name": "cashflow_yield_subindustry_score", "direction": "higher_is_better"}],
                "scoring": {"weights": {"cashflow_yield_subindustry_score": 1.0}},
            },
            "portfolio": {"selection_count": 1},
            "validation": {
                "baselines": [
                    {
                        "name": "raw_low_pb_top1",
                        "mode": "single_factor",
                        "factor": "low_price_to_book",
                        "direction": "lower_is_better",
                        "selection_count": 1,
                    }
                ]
            },
        }
        rows = [
            {"trade_date": "2025-04-01", "code": "LOW_PB", "future_return": 0.06, "low_price_to_book": 0.5},
            {"trade_date": "2025-04-01", "code": "HIGH_PB", "future_return": -0.04, "low_price_to_book": 2.0},
        ]

        result = _baseline_tests(rows, raw)

        self.assertEqual(result[0]["case"], "raw_low_pb_top1")
        self.assertEqual(result[0]["mean_return"], 0.06)


if __name__ == "__main__":
    unittest.main()
