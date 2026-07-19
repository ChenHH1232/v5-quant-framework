from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.insurance_special_fields_runner import REQUIRED_COLUMNS, audit_insurance_special_fields


class InsuranceSpecialFieldsRunnerTests(unittest.TestCase):
    def test_template_rows_are_blocked_until_reviewed_and_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "manual.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                writer.writerow(
                    {
                        "sector": "insurance",
                        "code": "601318.XSHG",
                        "company_name": "Ping An",
                        "report_period": "2025-12-31",
                        "field": "embedded_value",
                        "value": "",
                        "unit": "CNY",
                        "source_type": "annual_report",
                        "source_title": "",
                        "source_url": "",
                        "publish_date": "",
                        "visible_date": "",
                        "pit_status": "needs_original_announcement_check",
                        "missing_reason": "manual_review_pending",
                        "original_announcement_checked": "false",
                        "review_status": "unreviewed",
                        "notes": "",
                    }
                )

            audit_insurance_special_fields(source, root / "out", min_core_code_count=1)
            summary = json.loads((root / "out" / "insurance_low_pb_only_v53c" / "insurance_special_fields_audit_summary.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "insurance_special_fields_source_repair_blocked")
            self.assertIn("embedded_value", summary["missing_core_fields"])

    def test_reviewed_core_fields_can_pass_source_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "manual.csv"
            fields = [
                "embedded_value",
                "new_business_value",
                "core_solvency_ratio",
                "comprehensive_solvency_ratio",
                "net_investment_yield",
                "total_investment_yield",
            ]
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                for field in fields:
                    writer.writerow(
                        {
                            "sector": "insurance",
                            "code": "601318.XSHG",
                            "company_name": "Ping An",
                            "report_period": "2025-12-31",
                            "field": field,
                            "value": "1.23",
                            "unit": "CNY",
                            "source_type": "annual_report",
                            "source_title": "2025 Annual Report",
                            "source_url": "https://example.com/report.pdf",
                            "publish_date": "2026-03-20",
                            "visible_date": "2026-03-20",
                            "pit_status": "pit_usable",
                            "missing_reason": "not_missing",
                            "original_announcement_checked": "true",
                            "review_status": "reviewed",
                            "notes": "",
                        }
                    )

            audit_insurance_special_fields(source, root / "out", min_core_code_count=1)
            summary = json.loads((root / "out" / "insurance_low_pb_only_v53c" / "insurance_special_fields_audit_summary.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "insurance_special_fields_source_repair_passed")
            self.assertEqual(summary["missing_core_fields"], [])

    def test_single_code_seed_is_blocked_when_min_core_code_count_is_five(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "manual.csv"
            fields = [
                "embedded_value",
                "new_business_value",
                "core_solvency_ratio",
                "comprehensive_solvency_ratio",
                "net_investment_yield",
                "total_investment_yield",
            ]
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                for field in fields:
                    writer.writerow(
                        {
                            "sector": "insurance",
                            "code": "601318.XSHG",
                            "company_name": "Ping An",
                            "report_period": "2025-12-31",
                            "field": field,
                            "value": "1.23",
                            "unit": "CNY",
                            "source_type": "annual_report",
                            "source_title": "2025 Annual Report",
                            "source_url": "https://example.com/report.pdf",
                            "publish_date": "2026-03-20",
                            "visible_date": "2026-03-20",
                            "pit_status": "pit_usable",
                            "missing_reason": "not_missing",
                            "original_announcement_checked": "true",
                            "review_status": "reviewed",
                            "notes": "",
                        }
                    )

            audit_insurance_special_fields(source, root / "out")
            summary = json.loads((root / "out" / "insurance_low_pb_only_v53c" / "insurance_special_fields_audit_summary.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "insurance_special_fields_source_repair_blocked")
            self.assertIn("embedded_value", summary["coverage_blocked_core_fields"])

    def test_database_backfill_without_original_announcement_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "manual.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                writer.writerow(
                    {
                        "sector": "insurance",
                        "code": "601318.XSHG",
                        "company_name": "Ping An",
                        "report_period": "2025-12-31",
                        "field": "embedded_value",
                        "value": "1.23",
                        "unit": "CNY",
                        "source_type": "eastmoney_f10_backfilled",
                        "source_title": "Eastmoney historical data",
                        "source_url": "https://example.com",
                        "publish_date": "2026-03-20",
                        "visible_date": "2026-03-20",
                        "pit_status": "needs_original_announcement_check",
                        "missing_reason": "database_backfilled_without_original_date",
                        "original_announcement_checked": "false",
                        "review_status": "reviewed",
                        "notes": "",
                    }
                )

            audit_insurance_special_fields(source, root / "out")
            with (root / "out" / "insurance_low_pb_only_v53c" / "insurance_special_fields_audit_rows.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["pit_usable"], "false")
            self.assertIn("pit_status_needs_original_announcement_check", rows[0]["issues"])
            self.assertIn("original_announcement_not_checked", rows[0]["issues"])

    def test_custom_core_fields_support_ev_nbv_specific_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "manual.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                for code in ["601318.XSHG", "601628.XSHG"]:
                    for field in ["embedded_value", "new_business_value"]:
                        writer.writerow(
                            {
                                "sector": "insurance",
                                "code": code,
                                "company_name": "Insurance",
                                "report_period": "2025-12-31",
                                "field": field,
                                "value": "123",
                                "unit": "CNY million",
                                "source_type": "annual_report",
                                "source_title": "Annual Report",
                                "source_url": "https://example.com/report.pdf",
                                "publish_date": "2026-03-20",
                                "visible_date": "2026-03-20",
                                "pit_status": "pit_usable",
                                "missing_reason": "not_missing",
                                "original_announcement_checked": "true",
                                "review_status": "reviewed",
                                "notes": "",
                            }
                        )

            audit_insurance_special_fields(
                source,
                root / "out",
                min_core_code_count=2,
                core_fields={"embedded_value", "new_business_value"},
            )
            summary = json.loads((root / "out" / "insurance_low_pb_only_v53c" / "insurance_special_fields_audit_summary.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "insurance_special_fields_source_repair_passed")
            self.assertEqual(summary["active_core_fields"], ["embedded_value", "new_business_value"])
            self.assertEqual(summary["missing_core_fields"], [])


if __name__ == "__main__":
    unittest.main()
