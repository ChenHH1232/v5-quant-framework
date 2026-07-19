from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.annual_report_extraction_runner import build_annual_report_sample, extract_annual_report_candidates


class AnnualReportExtractionRunnerTests(unittest.TestCase):
    def test_sample_manifest_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "report.txt"
            report.write_text("内含价值 100 一年新业务价值 10", encoding="utf-8")
            manifest = root / "manifest.csv"
            self._write_manifest(
                manifest,
                [
                    self._row("601318.XSHG", "2023-12-31", report),
                    self._row("601601.XSHG", "2023-12-31", report),
                    self._row("601628.XSHG", "2023-12-31", report),
                ],
            )

            report_path = build_annual_report_sample(manifest, root / "out", sample_size=2, seed=3)

            self.assertTrue(report_path.exists())
            summary = json.loads((root / "out" / "annual_report_sample_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "annual_report_sample_ready")
            self.assertEqual(summary["sample_size"], 2)

    def test_extracted_candidates_require_manual_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "report.txt"
            report.write_text("寿险业务内含价值 398,191 扣除要求资本成本后的一年新业务价值 9,205", encoding="utf-8")
            manifest = root / "manifest.csv"
            self._write_manifest(manifest, [self._row("601601.XSHG", "2022-12-31", report)])

            report_path = extract_annual_report_candidates(manifest, root / "out")

            self.assertTrue(report_path.exists())
            rows = self._read_csv(root / "out" / "annual_report_field_candidates.csv")
            self.assertGreaterEqual(len(rows), 2)
            self.assertTrue(all(row["pit_status"] == "needs_original_announcement_check" for row in rows))
            self.assertTrue(all(row["review_status"] == "unreviewed" for row in rows))
            self.assertIn("398191", {row["candidate_value"] for row in rows})

    def _write_manifest(self, path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = list(rows[0].keys())
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _row(self, code: str, report_period: str, report: Path) -> dict[str, str]:
        return {
            "sector": "insurance",
            "code": code,
            "company_name": code,
            "report_period": report_period,
            "publish_date": "2024-03-27",
            "visible_date": "2024-03-27",
            "source_title": "annual report",
            "source_url": "https://example.com/report.pdf",
            "local_path": str(report),
        }


if __name__ == "__main__":
    unittest.main()
