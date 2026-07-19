from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.insurance_ev_nbv_panel_runner import build_insurance_ev_nbv_panel
from v5.insurance_special_fields_runner import REQUIRED_COLUMNS


class InsuranceEvNbvPanelRunnerTests(unittest.TestCase):
    def test_visible_date_blocks_future_ev_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel = root / "panel.csv"
            evidence = root / "ev_nbv.csv"
            with panel.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["trade_date", "code", "market_cap", "future_return"])
                writer.writeheader()
                writer.writerow({"trade_date": "2025-01-02", "code": "601318.XSHG", "market_cap": "6000", "future_return": "0.1"})
                writer.writerow({"trade_date": "2025-04-01", "code": "601318.XSHG", "market_cap": "6000", "future_return": "0.1"})
            with evidence.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                for field, value in [("embedded_value", "835093"), ("new_business_value", "28534")]:
                    writer.writerow(
                        {
                            "sector": "insurance",
                            "code": "601318.XSHG",
                            "company_name": "Ping An",
                            "report_period": "2024-12-31",
                            "field": field,
                            "value": value,
                            "unit": "CNY million",
                            "source_type": "annual_report",
                            "source_title": "Ping An 2024 Annual Report",
                            "source_url": "https://www.fxbaogao.com/view?id=4738198",
                            "publish_date": "2025-03-20",
                            "visible_date": "2025-03-20",
                            "pit_status": "pit_usable",
                            "missing_reason": "not_missing",
                            "original_announcement_checked": "true",
                            "review_status": "reviewed",
                            "notes": "",
                        }
                    )

            build_insurance_ev_nbv_panel(panel, evidence, root / "out", min_coverage_ratio=0.8, min_validation_years=1)
            with (root / "out" / "insurance_pev_nbv_v53f" / "panel_with_ev_nbv.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["embedded_value"], "")
            self.assertEqual(rows[0]["price_to_embedded_value"], "")
            self.assertEqual(rows[1]["embedded_value"], "835093")
            self.assertAlmostEqual(float(rows[1]["price_to_embedded_value"]), 6000 * 100 / 835093)

    def test_insufficient_years_blocks_formal_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel = root / "panel.csv"
            evidence = root / "ev_nbv.csv"
            with panel.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["trade_date", "code", "market_cap", "future_return"])
                writer.writeheader()
                writer.writerow({"trade_date": "2025-04-01", "code": "601318.XSHG", "market_cap": "6000", "future_return": "0.1"})
            with evidence.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                for field, value in [("embedded_value", "835093"), ("new_business_value", "28534")]:
                    writer.writerow(
                        {
                            "sector": "insurance",
                            "code": "601318.XSHG",
                            "company_name": "Ping An",
                            "report_period": "2024-12-31",
                            "field": field,
                            "value": value,
                            "unit": "CNY million",
                            "source_type": "annual_report",
                            "source_title": "Ping An 2024 Annual Report",
                            "source_url": "https://www.fxbaogao.com/view?id=4738198",
                            "publish_date": "2025-03-20",
                            "visible_date": "2025-03-20",
                            "pit_status": "pit_usable",
                            "missing_reason": "not_missing",
                            "original_announcement_checked": "true",
                            "review_status": "reviewed",
                            "notes": "",
                        }
                    )

            build_insurance_ev_nbv_panel(panel, evidence, root / "out", min_coverage_ratio=0.8, min_validation_years=4)
            summary = json.loads((root / "out" / "insurance_pev_nbv_v53f" / "ev_nbv_panel_summary.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "ev_nbv_pev_panel_insufficient_history")
            self.assertFalse(summary["formal_validation_allowed"])


if __name__ == "__main__":
    unittest.main()
