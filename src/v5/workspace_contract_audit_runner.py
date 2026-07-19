from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.config_validation_runner import validate_config_file
from v5.io_utils import write_json_file


DEFAULT_OUT_DIR = Path("workspace_contract_audits")
DEFAULT_REGISTRY = Path("docs/governance/status_registry.json")


@dataclass(frozen=True)
class WorkspaceContractAuditResult:
    summary_path: Path
    report_path: Path
    status: str
    blocker_count: int
    warning_count: int


def run_workspace_contract_audit(
    *,
    root: Path = Path("."),
    out_dir: Path = DEFAULT_OUT_DIR,
    registry_path: Path = DEFAULT_REGISTRY,
    include_configs: bool = True,
    include_examples: bool = True,
) -> WorkspaceContractAuditResult:
    root = root.resolve()
    config_results = _validate_json_dir(root / "config") if include_configs else []
    example_results = _validate_json_dir(root / "examples") if include_examples else []
    registry_result = _audit_registry(root, root / registry_path)
    checks = [
        _check_validation_group("config_validation", config_results),
        _check_validation_group("example_validation", example_results),
        registry_result,
    ]
    blocker_count = sum(1 for check in checks if check["severity"] == "blocker")
    warning_count = sum(1 for check in checks if check["severity"] == "warning")
    status = "passed" if blocker_count == 0 else "blocked"

    out = out_dir / "latest"
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "experiment_layer": "pm_decision_gate",
        "status": status,
        "root": str(root),
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "checks": checks,
        "config_validation": _validation_summary(config_results),
        "example_validation": _validation_summary(example_results),
        "registry_audit": registry_result,
        "blocked_actions": _blocked_actions(status),
        "pm_rule": "Workspace contract audit is a read-only governance check; it does not run backtests, refresh data, tune models, or call JoinQuant.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    summary_path = out / "workspace_contract_audit_summary.json"
    report_path = out / "workspace_contract_audit_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return WorkspaceContractAuditResult(summary_path, report_path, status, blocker_count, warning_count)


def _validate_json_dir(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    results = []
    for path in sorted(directory.glob("*.json")):
        try:
            result = validate_config_file(path)
            audit = result.get("audit", {})
            results.append(
                {
                    "path": _rel(path),
                    "config_type": result.get("config_type"),
                    "identifier": result.get("identifier") or result.get("strategy_id"),
                    "passed": bool(audit.get("passed")),
                    "issue_count": len(audit.get("issues", [])),
                    "issues": audit.get("issues", []),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "path": _rel(path),
                    "config_type": "validation_exception",
                    "identifier": path.stem,
                    "passed": False,
                    "issue_count": 1,
                    "issues": [{"code": "VALIDATION_EXCEPTION", "severity": "blocker", "message": str(exc)}],
                }
            )
    return results


def _audit_registry(root: Path, registry_path: Path) -> dict[str, Any]:
    if not registry_path.exists():
        return _check("status_registry", "blocker", f"Registry file is missing: {_rel(registry_path)}")
    registry = _read_json(registry_path)
    missing_paths = []
    missing_fields = []
    accepted_violations = []
    required = {"strategy_id", "sector", "current_status", "not_status", "experiment_layer", "evidence_paths", "blockers", "next_gate"}
    for strategy in registry.get("strategies", []):
        strategy_id = str(strategy.get("strategy_id") or "<unknown>")
        absent = sorted(required - set(strategy))
        if absent:
            missing_fields.append({"strategy_id": strategy_id, "missing_fields": absent})
        for path_text in strategy.get("evidence_paths", []):
            if not (root / str(path_text)).exists():
                missing_paths.append({"strategy_id": strategy_id, "path": str(path_text)})
        statuses = set(strategy.get("current_status", []))
        evidence = "\n".join(strategy.get("evidence_paths", []))
        has_platform = "platform" in evidence or "platform_replication_passed" in statuses
        has_paper = "paper" in evidence or "paper_trading" in statuses or "paper_trading_started" in statuses
        if "accepted_strategy" in statuses and not (has_platform and has_paper):
            accepted_violations.append(strategy_id)
    severity = "pass" if not missing_paths and not missing_fields and not accepted_violations else "blocker"
    detail = (
        f"missing_paths={len(missing_paths)}, missing_fields={len(missing_fields)}, "
        f"accepted_violations={len(accepted_violations)}"
    )
    check = _check("status_registry", severity, detail)
    check["missing_paths"] = missing_paths
    check["missing_fields"] = missing_fields
    check["accepted_violations"] = accepted_violations
    check["strategy_count"] = len(registry.get("strategies", []))
    return check


def _check_validation_group(name: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [item for item in results if not item["passed"]]
    warnings = [
        item
        for item in results
        if item["passed"] and any(issue.get("severity") == "warning" for issue in item.get("issues", []))
    ]
    if failed:
        severity = "blocker"
    elif warnings:
        severity = "warning"
    else:
        severity = "pass"
    check = _check(name, severity, f"passed={len(results) - len(failed)}, failed={len(failed)}, warnings={len(warnings)}")
    check["file_count"] = len(results)
    check["failed"] = failed
    check["warnings"] = warnings
    return check


def _validation_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    failed = []
    for item in results:
        config_type = str(item.get("config_type") or "unknown")
        by_type[config_type] = by_type.get(config_type, 0) + 1
        if not item["passed"]:
            failed.append(item)
    return {
        "file_count": len(results),
        "passed_count": len(results) - len(failed),
        "failed_count": len(failed),
        "counts_by_config_type": by_type,
        "failed": failed,
    }


def _blocked_actions(status: str) -> list[str]:
    if status == "passed":
        return []
    return [
        "strategy_state_promotion",
        "platform_replication_passed_marking",
        "paper_trading_signal_generation",
        "new_sector_formal_candidate_freeze",
    ]


def _check(name: str, severity: str, detail: str) -> dict[str, Any]:
    return {"check": name, "severity": severity, "detail": detail}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# Workspace Contract Audit",
        "",
        f"- Status: `{summary['status']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        f"- Warnings: `{summary['warning_count']}`",
        f"- Root: `{summary['root']}`",
        "",
        "## Checks",
        "",
    ]
    for check in summary["checks"]:
        lines.append(f"- `{check['severity']}` {check['check']}: {check['detail']}")
    lines.extend(["", "## Config Validation", ""])
    for key, value in summary["config_validation"]["counts_by_config_type"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Example Validation", ""])
    for key, value in summary["example_validation"]["counts_by_config_type"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## PM Rule", "", summary["pm_rule"]])
    return "\n".join(lines)
