from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_json_file


DEFAULT_OUT_DIR = Path("strategy_state_gates")
DEFAULT_REGISTRY = Path("docs/governance/status_registry.json")
VALID_TARGET_STATUSES = {
    "formal_strategy_candidate",
    "platform_replication_passed",
    "paper_trading_started",
    "accepted_strategy",
    "live_trading_approved",
}


@dataclass(frozen=True)
class StrategyStateGateResult:
    summary_path: Path
    report_path: Path
    status: str
    blocker_count: int
    user_decision_required: bool


def run_strategy_state_gate(
    *,
    strategy_id: str,
    target_status: str,
    registry_path: Path = DEFAULT_REGISTRY,
    out_dir: Path = DEFAULT_OUT_DIR,
    proposed_evidence: list[str] | None = None,
) -> StrategyStateGateResult:
    if target_status not in VALID_TARGET_STATUSES:
        raise ValueError(f"unknown target_status: {target_status}")
    registry = _read_json(registry_path)
    strategy = _find_strategy(registry, strategy_id)
    evidence = list(strategy.get("evidence_paths", [])) + list(proposed_evidence or [])
    current_statuses = set(strategy.get("current_status", []))
    checks = _checks(strategy, current_statuses, evidence, target_status)
    blocker_count = sum(1 for check in checks if check["severity"] == "blocker")
    if target_status in current_statuses:
        status = "already_has_status"
    elif blocker_count:
        status = "blocked"
    else:
        status = "ready_for_user_stage_gate"

    summary = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "target_status": target_status,
        "experiment_layer": "pm_decision_gate",
        "status": status,
        "blocker_count": blocker_count,
        "user_decision_required": status == "ready_for_user_stage_gate",
        "user_decision_reason": _user_decision_reason(status, target_status),
        "current_status": sorted(current_statuses),
        "not_status": strategy.get("not_status", []),
        "next_gate": strategy.get("next_gate"),
        "checks": checks,
        "evidence_paths_checked": evidence,
        "blocked_actions": _blocked_actions(status, target_status),
        "pm_rule": "Strategy state gates are read-only. Passing this gate does not change registry status; promotion still requires an explicit PM/user stage-gate decision.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    out = out_dir / strategy_id / target_status
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "strategy_state_gate_summary.json"
    report_path = out / "strategy_state_gate_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return StrategyStateGateResult(summary_path, report_path, status, blocker_count, summary["user_decision_required"])


def _checks(strategy: dict[str, Any], current_statuses: set[str], evidence: list[str], target_status: str) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    blockers = [str(item) for item in strategy.get("blockers", [])]
    not_statuses = set(strategy.get("not_status", []))
    evidence_text = "\n".join(evidence).lower()
    status_text = "\n".join(sorted(current_statuses | not_statuses) + blockers).lower()

    if target_status in current_statuses:
        checks.append(_check("target_status", "pass", f"Strategy already has status {target_status}."))
        return checks

    if target_status in not_statuses:
        checks.append(_check("not_status_marker", "needs_user_stage_gate", f"Registry currently marks {target_status} as not_status."))

    if target_status == "formal_strategy_candidate":
        _require_evidence(checks, evidence_text, ["formal_validation", "pm_decision", "formal_candidate"], "formal research validation or PM decision evidence")
        if "strategy_candidate_failed" in current_statuses or "archived_not_formal_candidate" in current_statuses:
            checks.append(_check("candidate_failure_status", "blocker", "Strategy is currently marked failed or archived."))

    if target_status == "platform_replication_passed":
        _require_current(
            checks,
            current_statuses,
            {"formal_strategy_candidate", "frozen_formal_strategy_candidate", "formal_etf_candidate"},
            "formal strategy or ETF candidate status",
        )
        _require_evidence(checks, evidence_text, ["platform_replication", "platform_attribution"], "platform replication or attribution evidence")
        if (
            "platform_test_deferred_by_user" in status_text
            or "platform_replication_prepared_pending_joinquant_exports" in status_text
            or "pending_joinquant_exports" in status_text
            or "platform exports" in status_text
            or "without exports" in status_text
            or "waiting_for_exports" in status_text
        ):
            checks.append(_check("platform_exports", "blocker", "Platform exports are deferred or missing; cannot mark platform replication passed."))

    if target_status == "paper_trading_started":
        _require_current(checks, current_statuses, {"formal_strategy_candidate", "frozen_formal_strategy_candidate", "platform_replication_passed"}, "formal candidate or platform-replicated status")
        _require_evidence(checks, evidence_text, ["paper_trading", "forward_paper", "paper_signal"], "paper trading log or forward paper gate evidence")

    if target_status == "accepted_strategy":
        _require_current(checks, current_statuses, {"platform_replication_passed", "full_platform_replication_passed"}, "platform replication passed status")
        _require_current(checks, current_statuses, {"paper_trading_started", "paper_trading_process_started", "paper_trading"}, "paper trading status")
        _require_evidence(checks, evidence_text, ["platform"], "platform evidence")
        _require_evidence(checks, evidence_text, ["paper"], "paper trading evidence")
        if blockers:
            checks.append(_check("open_blockers", "blocker", f"Strategy still lists blockers: {len(blockers)}."))

    if target_status == "live_trading_approved":
        _require_current(checks, current_statuses, {"accepted_strategy"}, "accepted strategy status")
        checks.append(_check("live_trading_user_gate", "blocker", "Live trading approval is outside automated PM promotion."))

    if not any(check["severity"] == "blocker" for check in checks):
        checks.append(_check("pm_stage_gate", "needs_user_stage_gate", "Evidence gate passed, but promotion still requires explicit user/PM stage-gate approval."))
    return checks


def _require_current(checks: list[dict[str, str]], current_statuses: set[str], allowed: set[str], label: str) -> None:
    if current_statuses & allowed:
        checks.append(_check(label, "pass", f"Found {label}."))
    else:
        checks.append(_check(label, "blocker", f"Missing required {label}."))


def _require_evidence(checks: list[dict[str, str]], evidence_text: str, tokens: list[str], label: str) -> None:
    if any(token in evidence_text for token in tokens):
        checks.append(_check(label, "pass", f"Found {label}."))
    else:
        checks.append(_check(label, "blocker", f"Missing {label}."))


def _find_strategy(registry: dict[str, Any], strategy_id: str) -> dict[str, Any]:
    for strategy in registry.get("strategies", []):
        if strategy.get("strategy_id") == strategy_id:
            return strategy
    raise ValueError(f"strategy_id not found in registry: {strategy_id}")


def _blocked_actions(status: str, target_status: str) -> list[str]:
    if status == "already_has_status":
        return []
    if status == "ready_for_user_stage_gate":
        return [f"auto_mark_{target_status}_without_user_stage_gate"]
    return [f"mark_{target_status}", "strategy_state_promotion"]


def _user_decision_reason(status: str, target_status: str) -> str:
    if status == "ready_for_user_stage_gate":
        return f"Promotion to {target_status} is a strategy-state change and requires explicit stage-gate approval."
    return ""


def _check(name: str, severity: str, detail: str) -> dict[str, str]:
    return {"check": name, "severity": severity, "detail": detail}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# Strategy State Gate: {summary['strategy_id']}",
        "",
        f"- Target status: `{summary['target_status']}`",
        f"- Gate status: `{summary['status']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        f"- User decision required: `{summary['user_decision_required']}`",
        f"- User decision reason: {summary['user_decision_reason'] or 'n/a'}",
        "",
        "## Checks",
        "",
    ]
    for check in summary["checks"]:
        lines.append(f"- `{check['severity']}` {check['check']}: {check['detail']}")
    lines.extend(["", "## Blocked Actions", ""])
    for item in summary.get("blocked_actions", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## PM Rule", "", summary["pm_rule"]])
    return "\n".join(lines)
