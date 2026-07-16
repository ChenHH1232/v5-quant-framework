from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from v5.scoring import apply_value_trap_guard, merge_eastmoney_quality, score_rows
from v5.spec import SpecError, parse_strategy_spec


class ScoringV2Tests(unittest.TestCase):
    def test_two_layer_score_uses_value_and_quality(self):
        spec = {
            "signals": {
                "factors": [
                    {"name": "low_price_to_book", "direction": "lower_is_better"},
                    {"name": "roe_quality", "direction": "higher_is_better"},
                    {"name": "asset_quality_trend", "direction": "higher_is_better"},
                    {"name": "provision_buffer", "direction": "higher_is_better"},
                    {"name": "capital_resilience", "direction": "higher_is_better"},
                ],
                "scoring": {
                    "method": "two_layer_score",
                    "value_score": {"low_price_to_book": 0.6},
                    "quality_score": {
                        "roe_quality": 0.35,
                        "asset_quality_trend": 0.25,
                        "provision_buffer": 0.2,
                        "capital_resilience": 0.2,
                    },
                },
            }
        }
        rows = [
            {"trade_date": "2025-05-06", "code": "A", "low_price_to_book": "0.5", "roe_quality": "10", "asset_quality_trend": "0.1", "provision_buffer": "300", "capital_resilience": "12"},
            {"trade_date": "2025-05-06", "code": "B", "low_price_to_book": "0.7", "roe_quality": "8", "asset_quality_trend": "-0.1", "provision_buffer": "200", "capital_resilience": "10"},
            {"trade_date": "2025-05-06", "code": "C", "low_price_to_book": "1.0", "roe_quality": "6", "asset_quality_trend": "-0.2", "provision_buffer": "100", "capital_resilience": "8"},
        ]
        scored, used = score_rows(spec, rows)
        self.assertIn("low_price_to_book", used)
        self.assertIn("capital_resilience", used)
        by_code = {row["code"]: row for row in scored}
        self.assertGreater(by_code["A"]["score"], by_code["C"]["score"])

    def test_v2_guard_uses_quality_score(self):
        scored = [
            {"code": "A", "score": 1.0, "quality_score": 1.0, "asset_quality_trend": 0.2},
            {"code": "B", "score": 0.8, "quality_score": 0.5, "asset_quality_trend": 0.1},
            {"code": "C", "score": 0.7, "quality_score": -1.0, "asset_quality_trend": -0.5},
        ]
        guarded = apply_value_trap_guard({"signals": {"scoring": {"method": "two_layer_score"}}}, scored)
        self.assertEqual({row["code"] for row in guarded}, {"A", "B"})

    def test_eastmoney_quality_uses_notice_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["code", "source_year", "asset_quality_trend", "provision_buffer", "capital_resilience", "notice_date", "review_status"])
                writer.writeheader()
                writer.writerow({"code": "A", "source_year": "2024", "asset_quality_trend": "0.1", "provision_buffer": "300", "capital_resilience": "10", "notice_date": "2025-03-31", "review_status": "needs_check"})
            rows = [
                {"trade_date": "2025-03-30", "code": "A"},
                {"trade_date": "2025-04-01", "code": "A"},
            ]
            merged = merge_eastmoney_quality(rows, path)
            self.assertNotIn("asset_quality_trend", merged[0])
            self.assertEqual(merged[1]["asset_quality_trend"], "0.1")

    def test_eastmoney_quality_can_match_joinquant_source_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["code", "source_year", "asset_quality_trend", "provision_buffer", "capital_resilience", "notice_date", "review_status"])
                writer.writeheader()
                writer.writerow({"code": "A", "source_year": "2024", "asset_quality_trend": "0.1", "provision_buffer": "300", "capital_resilience": "10", "notice_date": "2026-03-31", "review_status": "needs_check"})
            rows = [{"trade_date": "2025-07-01", "code": "A"}]
            merged = merge_eastmoney_quality(rows, path, visibility_mode="joinquant_source_year")
            self.assertEqual(merged[0]["asset_quality_trend"], "0.1")

    def test_unknown_scoring_method_is_blocked(self):
        spec = self._minimal_spec()
        spec["signals"]["scoring"]["method"] = "insurance_low_pb_onyl_typo"

        with self.assertRaises(SpecError):
            parse_strategy_spec(spec)

    def test_registered_insurance_low_pb_method_scores_as_weighted_composite(self):
        spec = {
            "signals": {
                "factors": [
                    {"name": "low_price_to_book", "direction": "lower_is_better"},
                ],
                "scoring": {
                    "method": "insurance_low_pb_only_v53c",
                    "weights": {"low_price_to_book": 1.0},
                    "min_factor_count": 1,
                },
            }
        }
        rows = [
            {"trade_date": "2025-05-06", "code": "A", "low_price_to_book": "0.5"},
            {"trade_date": "2025-05-06", "code": "B", "low_price_to_book": "0.8"},
            {"trade_date": "2025-05-06", "code": "C", "low_price_to_book": "1.2"},
        ]

        scored, used = score_rows(spec, rows)

        self.assertEqual(used, ["low_price_to_book"])
        ordered_codes = [row["code"] for row in sorted(scored, key=lambda item: item["score"], reverse=True)]
        self.assertEqual(ordered_codes, ["A", "B", "C"])

    def _minimal_spec(self):
        return {
            "meta": {"strategy_id": "test", "name": "test", "objective": "test"},
            "universe": {"name": "test", "construction": "test", "point_in_time": True},
            "data": {"vendor": "test", "price_frequency": "quarterly", "financial_as_of_policy": "announcement_date"},
            "signals": {
                "factors": [
                    {
                        "name": "low_price_to_book",
                        "source": "test",
                        "direction": "lower_is_better",
                        "definition": "test",
                        "as_of": "trade_date",
                        "disclosure_lag_days": 1,
                        "missing_policy": "drop_security",
                    }
                ],
                "scoring": {
                    "method": "weighted_composite_score",
                    "weights": {"low_price_to_book": 1.0},
                    "min_factor_count": 1,
                },
            },
            "schedule": {"signal_frequency": "quarterly", "rebalance_frequency": "quarterly"},
            "portfolio": {"selection_count": 1, "weighting": "equal", "max_position_weight": 1.0},
            "risk": {"defensive_asset": "cash", "defensive_rule": {"enabled": False}},
            "validation": {"method": "rolling", "train_years": 5, "test_years": 1},
            "execution": {"commission_bps": 0, "slippage_bps": 0, "suspension_policy": "skip", "limit_policy": "skip"},
            "outputs": {"save_holdings": True, "save_rebalance_signals": True, "report": "markdown"},
        }


if __name__ == "__main__":
    unittest.main()
