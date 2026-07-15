from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from v5.scoring import apply_value_trap_guard, merge_eastmoney_quality, score_rows


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


if __name__ == "__main__":
    unittest.main()
