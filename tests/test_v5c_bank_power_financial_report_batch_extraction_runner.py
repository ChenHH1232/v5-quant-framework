from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_bank_power_financial_report_batch_extraction_runner import BatchExtractionConfig, run, _value_candidates


class V5cBankPowerFinancialReportBatchExtractionRunnerTest(unittest.TestCase):
    def test_value_candidate_parser_keeps_nearby_percentages_and_units(self) -> None:
        values = _value_candidates("本行净息差 2.31%，不良贷款率 1.02%，拨备覆盖率 250.00%。", "净息差")
        self.assertIn("2.31%", values)
        self.assertIn("1.02%", values)

    def test_batch_extraction_stays_review_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "v5c_bank_power_financial_report_data_gate" / "current"
            input_dir.mkdir(parents=True)
            bank_text = input_dir / "bank_fixture.txt"
            power_text = input_dir / "power_fixture.txt"
            bank_text.write_text("本行净息差 2.31%，存款成本率 1.95%，不良贷款率 1.02%，资本充足率 13.5%。", encoding="utf-8")
            power_text.write_text("公司燃料成本 100 亿元，上网电价 0.38 元/千瓦时，利用小时 4200 小时，发电量 300 亿千瓦时。", encoding="utf-8")
            _write_csv(
                input_dir / "v5c_bank_power_annual_report_manifest.csv",
                [
                    _manifest_row("bank", "600000.XSHG", "浦发银行", "2025-12-31", bank_text),
                    _manifest_row("utilities_electricity", "600011.XSHG", "华能国际", "2025-12-31", power_text),
                ],
            )

            summary_path = run(root, BatchExtractionConfig(download_missing=False))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_financial_report_batch_extraction")
            self.assertFalse(summary["can_update_model_now"])
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])

            out = root / "v5c_bank_power_financial_report_batch_extraction" / "current"
            bank_candidates = _read_csv(out / "v5c_bank_financial_report_field_candidates.csv")
            power_candidates = _read_csv(out / "v5c_power_financial_report_field_candidates.csv")
            self.assertTrue(any(row["field"] == "net_interest_margin" for row in bank_candidates))
            self.assertTrue(any(row["field"] == "fuel_cost" for row in power_candidates))

            decision = _read_csv(out / "v5c_bank_power_batch_extraction_pm_gate_decision.csv")
            self.assertEqual(decision[0]["can_update_model_now"], "False")


def _manifest_row(industry: str, code: str, name: str, period: str, path: Path) -> dict[str, str]:
    return {
        "industry": industry,
        "code": code,
        "cn_code": code.split(".")[0],
        "sec_name": name,
        "org_id": "fixture",
        "announcement_title": "年度报告",
        "announcement_date": "2026-03-30",
        "report_period": period,
        "adjunct_url": "",
        "pdf_url": "",
        "source": "fixture",
        "pit_visible_date": "2026-03-30",
        "download_status": "queued",
        "local_pdf_path": str(path),
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
