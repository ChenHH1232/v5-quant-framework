from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit


OUT = Path("v5k_historical_platform_contract_archive") / "current"
SOURCE = Path("data") / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution"
SUMMARY = Path("v5f_joinquant_platform_attribution") / "current" / "v5f_joinquant_platform_attribution_summary.json"
EXPECTED = [
    "daily_returns_baseline_result_1_21.csv", "daily_returns_primary_result_1_20.csv",
    "log_baseline_v57f_startup_preload_repaired_baseline.zip", "log_primary_internal_subsleeve_mom12_70_30.zip",
    "position_baseline_v57f_startup_preload_repaired_baseline.zip", "position_primary_internal_subsleeve_mom12_70_30.zip",
    "transaction_baseline_v57f_startup_preload_repaired_baseline.zip", "transaction_primary_internal_subsleeve_mom12_70_30.zip",
]


def run_v5k_historical_platform_contract_archive(root: Path = Path(".")) -> dict[str, Any]:
    boundary = historical_operation_audit("read_local_historical_artifacts_at_or_before_max_date", "2026-05-31", root)
    source = root / SOURCE
    manifest = [_manifest_row(source / name, name) for name in EXPECTED]
    attribution = json.loads((root / SUMMARY).read_text(encoding="utf-8-sig"))
    missing = [row for row in manifest if not row["exists"]]
    record = [{
        "contract_id": "v5f_platform_historical_reproduction_contract",
        "scope": "historical_exports_only_through_2026-05-31",
        "primary_model": "internal_subsleeve_mom12_70_30",
        "baseline": "v57f_startup_preload_repaired_baseline",
        "daily_return_correlation": attribution["daily_return_correlation_vs_local_primary"],
        "source_snapshot_archived": False,
        "source_snapshot_status": "missing_do_not_reconstruct_from_memory",
        "config_snapshot_archived": False,
        "fee_assumptions_archived": False,
        "target_file_hash_archived": False,
        "exports_manifest_count": len(manifest),
        "exports_missing_count": len(missing),
        "accepted": False,
        "live_trading_approved": False,
    }]
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "v5k_platform_export_sha256_manifest.csv", manifest)
    _write_csv(out / "v5k_platform_contract_record.csv", record)
    _write_csv(out / "v5k_platform_contract_boundary_audit.csv", [boundary])
    _write_csv(out / "v5k_platform_contract_blockers.csv", [{"blocker_id": "exact_submitted_source_snapshot", "status": "open", "detail": "Missing; no reconstructed source is treated as a submitted snapshot."}])
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5k_historical_platform_contract_archive",
        "status": "completed_historical_export_archive_contract_incomplete",
        "market_data_max_date": "2026-05-31",
        "manifest_file_count": len(manifest),
        "missing_export_count": len(missing),
        "exact_submitted_source_snapshot_archived": False,
        "accepted": False,
        "live_trading_approved": False,
    }
    (out / "v5k_platform_contract_archive_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5k_platform_contract_archive_report.md").write_text(
        "# V5 Historical Platform Contract Archive\n\n"
        f"- Historical export files hashed: `{len(manifest)}`; missing: `{len(missing)}`.\n"
        "- Exact submitted platform source/config/target snapshots remain absent. They are not reconstructed from memory.\n"
        "- This archive neither runs a platform nor creates any post-boundary target or order.\n",
        encoding="utf-8",
    )
    return summary


def _manifest_row(path: Path, name: str) -> dict[str, Any]:
    exists = path.exists()
    return {"file_name": name, "path": str(path), "exists": exists, "size_bytes": path.stat().st_size if exists else "", "sha256": _sha256(path) if exists else ""}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5k_historical_platform_contract_archive(), ensure_ascii=False, indent=2))
