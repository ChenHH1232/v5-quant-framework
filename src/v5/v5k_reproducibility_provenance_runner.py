from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit


OUT = Path("v5k_reproducibility_provenance") / "current"
INPUTS = [
    Path("config") / "v5_active_model_registry.json",
    Path("config") / "v5_historical_operation_boundary.json",
    Path("config") / "v5_experiment_catalog.json",
    Path("config") / "v5_test_tiers.json",
]


def run_v5k_reproducibility_provenance(root: Path = Path(".")) -> dict[str, Any]:
    boundary = historical_operation_audit("test_and_governance_repair_without_market_data", "2026-05-31", root)
    manifest = [_hash_row(root / path, "input") for path in INPUTS]
    git = _git_state(root)
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "v5k_governance_input_sha256_manifest.csv", manifest)
    _write_csv(out / "v5k_git_worktree_state.csv", [git])
    _write_csv(out / "v5k_provenance_boundary_audit.csv", [boundary])
    _write_csv(out / "v5k_artifact_root_policy.csv", [
        {"classification": "source", "root": "src/v5; tests; config; scripts; .github/workflows", "rule": "Review and commit in bounded batches."},
        {"classification": "generated_artifact", "root": "v5*/current; data/joinquant_exports", "rule": "Never erase or silently treat as source; record manifests for promoted packets."},
    ])
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5k_reproducibility_provenance",
        "status": "completed_non_destructive_provenance_snapshot",
        "git_head": git["git_head"],
        "modified_path_count": git["modified_path_count"],
        "untracked_path_count": git["untracked_path_count"],
        "input_manifest_count": len(manifest),
        "accepted": False,
        "live_trading_approved": False,
    }
    (out / "v5k_reproducibility_provenance_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _git_state(root: Path) -> dict[str, Any]:
    def command(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"
    lines = command("status", "--porcelain=v1").splitlines()
    return {
        "git_head": command("rev-parse", "HEAD"),
        "modified_path_count": sum(not line.startswith("??") for line in lines),
        "untracked_path_count": sum(line.startswith("??") for line in lines),
        "clean_worktree": len(lines) == 0,
        "action": "observed_only_no_reset_clean_or_revert",
    }


def _hash_row(path: Path, kind: str) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
    return {"kind": kind, "path": str(path), "exists": path.exists(), "sha256": digest}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5k_reproducibility_provenance(), ensure_ascii=False, indent=2))
