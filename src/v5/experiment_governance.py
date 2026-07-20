from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_LAYERS = {
    "research_pit_validation",
    "platform_replication",
    "engineering_smoke_test",
    "paper_trading",
}


def validate_experiment_layer(layer: str) -> str:
    if layer not in EXPERIMENT_LAYERS:
        allowed = ", ".join(sorted(EXPERIMENT_LAYERS))
        raise ValueError(f"unsupported experiment_layer: {layer}; allowed: {allowed}")
    return layer


def validate_daily_run_contract(
    *,
    experiment_layer: str,
    eastmoney_visibility_mode: str,
    execution_price_csv: Path | None,
    benchmark_csv: Path,
    dividend_cash_csv: Path | None,
) -> list[str]:
    layer = validate_experiment_layer(experiment_layer)
    warnings: list[str] = []
    if layer == "research_pit_validation":
        if eastmoney_visibility_mode != "notice_date":
            raise ValueError("research_pit_validation requires eastmoney_visibility_mode=notice_date")
        if execution_price_csv is not None:
            warnings.append("research PIT validation is using execution-price data; use this only for implementation checks, not factor acceptance.")
    elif layer == "platform_replication":
        if eastmoney_visibility_mode != "joinquant_source_year":
            raise ValueError("platform_replication requires eastmoney_visibility_mode=joinquant_source_year for the current JoinQuant V2 script")
        if execution_price_csv is None:
            raise ValueError("platform_replication requires execution_price_csv")
        if dividend_cash_csv is None:
            warnings.append("platform replication has no dividend_cash_csv; dividend cash reconciliation will be incomplete.")
    elif layer == "paper_trading":
        if eastmoney_visibility_mode != "notice_date":
            raise ValueError("paper_trading requires notice_date visibility")
    elif layer == "engineering_smoke_test":
        warnings.append("engineering_smoke_test can verify plumbing only; do not interpret performance as research evidence.")
    if not benchmark_csv.exists():
        raise ValueError(f"benchmark_csv does not exist: {benchmark_csv}")
    return warnings


def build_run_manifest(
    *,
    strategy_id: str,
    experiment_layer: str,
    command_profile: dict[str, Any],
    outputs: dict[str, str],
    warnings: list[str] | None = None,
    pre_run_git: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pre_run = pre_run_git or capture_git_state()
    manifest_created = capture_git_state()
    return {
        "strategy_id": strategy_id,
        "experiment_layer": validate_experiment_layer(experiment_layer),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "git": {
            "commit": pre_run.get("commit"),
            "dirty": bool(pre_run.get("dirty")),
            "dirty_scope": "pre_run",
            "pre_run": pre_run,
            "manifest_created": manifest_created,
        },
        "command_profile": command_profile,
        "outputs": outputs,
        "warnings": warnings or [],
        "governance_rule": "Project Manager Agent must not mix research validation, platform replication, engineering smoke tests, and paper trading evidence.",
    }


def write_run_manifest(path: Path, manifest: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def freeze_snapshot(source_dir: Path, snapshot_root: Path, manifest: dict[str, Any]) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = snapshot_root / f"{timestamp}_{manifest['strategy_id']}_{manifest['experiment_layer']}"
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    for path in source_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, snapshot_dir / path.name)
    write_run_manifest(snapshot_dir / "RUN_MANIFEST.json", manifest)
    return snapshot_dir


def capture_git_state() -> dict[str, Any]:
    status_short = _git(["status", "--short"])
    status_lines = status_short.splitlines() if status_short else []
    return {
        "commit": _git(["rev-parse", "HEAD"]),
        "dirty": bool(status_lines),
        "status_short": status_lines,
        "captured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _git(args: list[str]) -> str | None:
    try:
        result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    except Exception:
        return None
    return result.stdout.strip()
