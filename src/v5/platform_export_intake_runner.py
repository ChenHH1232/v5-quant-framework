from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_json_file


DEFAULT_OUT_DIR = Path("platform_export_intake_checks")


@dataclass(frozen=True)
class PlatformExportIntakeCheckResult:
    summary_path: Path
    report_path: Path
    status: str
    ready_count: int
    missing_count: int
    empty_count: int


def check_platform_export_intake(
    manifest_path: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    user_deferred: bool = False,
) -> PlatformExportIntakeCheckResult:
    manifest = _read_json(manifest_path)
    strategy_id = str(manifest.get("strategy_id") or "platform_export_intake")
    checks = [_check_expected_export(item) for item in manifest.get("required_exports", [])]
    missing_count = sum(1 for item in checks if item["status"] == "missing")
    empty_count = sum(1 for item in checks if item["status"] == "empty")
    ready_count = sum(1 for item in checks if item["status"] == "ready")
    status = _status(user_deferred, missing_count, empty_count, checks)

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "experiment_layer": "platform_replication",
        "status": status,
        "user_deferred": user_deferred,
        "manifest_path": str(manifest_path),
        "intake_dir": manifest.get("intake_dir"),
        "ready_count": ready_count,
        "missing_count": missing_count,
        "empty_count": empty_count,
        "checks": checks,
        "allowed_next_action": _allowed_next_action(status),
        "blocked_actions": [
            "platform_replication_passed",
            "accepted_strategy",
            "live_trading_approved",
            "return_tuning_from_platform_result",
        ],
        "pm_rule": "Platform replication may only proceed after all required exports are present and non-empty; summary return alone is not enough.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    summary_path = out / "platform_export_intake_summary.json"
    report_path = out / "platform_export_intake_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return PlatformExportIntakeCheckResult(summary_path, report_path, status, ready_count, missing_count, empty_count)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _check_expected_export(item: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(item.get("target_path") or ""))
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    status = "ready" if exists and size > 0 else ("empty" if exists else "missing")
    return {
        "name": item.get("name"),
        "target_path": str(path),
        "required_for": item.get("required_for"),
        "source_hint": item.get("source_hint"),
        "exists": exists,
        "size_bytes": size,
        "status": status,
    }


def _status(user_deferred: bool, missing_count: int, empty_count: int, checks: list[dict[str, Any]]) -> str:
    if user_deferred:
        return "platform_test_deferred_by_user_waiting_for_exports"
    if not checks:
        return "manifest_has_no_required_exports"
    if missing_count or empty_count:
        return "waiting_for_joinquant_exports"
    return "ready_for_platform_attribution"


def _allowed_next_action(status: str) -> str:
    if status == "ready_for_platform_attribution":
        return "run_platform_replication_packet_without_tuning"
    if status == "platform_test_deferred_by_user_waiting_for_exports":
        return "continue_local_paper_preflight_and_do_not_run_platform_attribution"
    return "wait_for_required_exports"


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# Platform Export Intake Check: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- User deferred: `{summary['user_deferred']}`",
        f"- Ready exports: `{summary['ready_count']}`",
        f"- Missing exports: `{summary['missing_count']}`",
        f"- Empty exports: `{summary['empty_count']}`",
        f"- Allowed next action: `{summary['allowed_next_action']}`",
        "",
        "## Export Checks",
        "",
        "| Export | Status | Size | Target |",
        "| --- | --- | ---: | --- |",
    ]
    for item in summary["checks"]:
        lines.append(f"| {item['name']} | `{item['status']}` | {item['size_bytes']} | `{item['target_path']}` |")
    lines.extend(
        [
            "",
            "## PM Rule",
            "",
            summary["pm_rule"],
        ]
    )
    return "\n".join(lines)

