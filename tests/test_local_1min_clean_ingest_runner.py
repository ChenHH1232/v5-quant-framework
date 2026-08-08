from __future__ import annotations

import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.v5.local_1min_clean_ingest_runner import run_local_1min_clean_ingest


class Local1minCleanIngestRunnerTest(unittest.TestCase):
    def test_runner_cleans_rows_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "数据库"
            price_dir = db / "processed" / "startup_preload_repaired_prices_v5"
            (db / "raw").mkdir(parents=True)
            (db / "manifests").mkdir(parents=True)
            price_dir.mkdir(parents=True)
            _write_csv(
                price_dir / "bank_v3_startup_repaired_daily_prices.csv",
                [{"date": "2013-01-04", "code": "000001.XSHE", "close": "10"}],
            )
            source = root / "minute_source"
            source.mkdir()
            with zipfile.ZipFile(source / "2013.zip", "w") as zf:
                zf.writestr(
                    "2013/000001.SZ.csv",
                    "\n".join(
                        [
                            "trade_time,open,high,low,close,vol,amount",
                            "2013-01-04 09:30:00,10,10,10,10,1,10",
                            "2013-01-04 09:31:00,10,10.1,9.9,10,1,10",
                            "2013-01-04 09:31:00,10,10.1,9.9,10,1,10",
                            "2013-01-04 09:32:00,10,9.9,10,10,1,10",
                            "2013-01-04 09:33:00,10,10,10,10,-1,10",
                        ]
                    ),
                )

            summary = run_local_1min_clean_ingest(root, years=[2013], source_minute_dir=source)

            self.assertEqual(summary["dataset_id"], "local_1min_clean_2013_2026")
            self.assertEqual(summary["total_1min_rows"], 1)
            self.assertEqual(summary["dropped_counts"]["dropped_out_of_session_rows"], 1)
            self.assertEqual(summary["dropped_counts"]["dropped_bad_ohlc_rows"], 1)
            self.assertEqual(summary["dropped_counts"]["dropped_bad_vol_amount_rows"], 1)
            self.assertEqual(summary["dropped_counts"]["duplicate_datetime_rows"], 1)
            self.assertTrue((db / "processed" / "local_1min_clean_2013_2026" / "by_year" / "2013" / "000001_XSHE_1min.csv").exists())


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
