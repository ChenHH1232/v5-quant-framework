from __future__ import annotations

import unittest
from pathlib import Path

from v5.v5k_historical_platform_contract_archive_runner import run_v5k_historical_platform_contract_archive


class V5kHistoricalPlatformContractArchiveRunnerTest(unittest.TestCase):
    def test_archives_existing_historical_exports_without_platform_execution(self) -> None:
        summary = run_v5k_historical_platform_contract_archive(Path("."))
        self.assertEqual(summary["manifest_file_count"], 8)
        self.assertEqual(summary["missing_export_count"], 0)
        self.assertFalse(summary["exact_submitted_source_snapshot_archived"])
        self.assertFalse(summary["accepted"])
        self.assertTrue((Path("v5k_historical_platform_contract_archive") / "current" / "v5k_platform_export_sha256_manifest.csv").exists())


if __name__ == "__main__":
    unittest.main()
