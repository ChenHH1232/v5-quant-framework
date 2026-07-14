from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.audit import audit_strategy
from v5.spec import StrategySpec, parse_strategy_spec


class RunBlockedError(RuntimeError):
    """Raised when a strategy has blocking audit issues."""


def load_spec(path: Path) -> StrategySpec:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return parse_strategy_spec(raw)


def validate_spec_file(path: Path) -> dict[str, Any]:
    spec = load_spec(path)
    audit = audit_strategy(spec)
    return {
        "strategy_id": spec.strategy_id,
        "audit": audit.to_dict(),
    }


def run_strategy(path: Path, out_dir: Path, allow_blockers: bool = False) -> Path:
    spec = load_spec(path)
    audit = audit_strategy(spec)

    if audit.blocking_issues and not allow_blockers:
        raise RunBlockedError(
            "strategy run blocked by audit issues: "
            + ", ".join(issue.code for issue in audit.blocking_issues)
        )

    run_id = _make_run_id(spec)
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    _write_json(run_dir / "strategy_spec.json", spec.raw)
    _write_json(run_dir / "audit.json", audit.to_dict())
    _write_json(run_dir / "manifest.json", _manifest(spec, run_id))
    _write_report(run_dir / "report.md", spec, audit)
    return run_dir


def _make_run_id(spec: StrategySpec) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha256(json.dumps(spec.raw, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    return f"{timestamp}_{spec.strategy_id}_{digest}"


def _manifest(spec: StrategySpec, run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "strategy_id": spec.strategy_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_version": _git_commit(),
        "engine_stage": "scaffold",
        "project_context": _project_context(),
        "artifacts": [
            "strategy_spec.json",
            "audit.json",
            "manifest.json",
            "report.md",
        ],
    }


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip()


def _project_context() -> dict[str, Any]:
    context_path = Path(__file__).resolve().parents[2] / "config" / "v5_context.json"
    try:
        with context_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {
            "project": "Bank Quant V5",
            "mission": "Build a reproducible and explainable quantitative research framework.",
        }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_report(path: Path, spec: StrategySpec, audit: Any) -> None:
    context = _project_context()
    lines = [
        f"# Research Run: {spec.raw['meta']['name']}",
        "",
        f"- Strategy ID: `{spec.strategy_id}`",
        f"- Objective: {spec.raw['meta']['objective']}",
        f"- Audit passed: `{audit.passed}`",
        f"- Engine stage: scaffold",
        f"- V5 mission: {context.get('mission', 'Build a reproducible quantitative research framework.')}",
        f"- V5 motto: {context.get('motto', 'A research framework can generate strategies.')}",
        "",
        "## V5 Research Context",
        "",
        context.get(
            "core_thesis",
            "Statistics provides evidence, finance provides explanation, and AI improves research efficiency.",
        ),
        "",
        "## Audit Issues",
        "",
    ]
    if audit.issues:
        for issue in audit.issues:
            lines.append(f"- `{issue.severity}` `{issue.code}`: {issue.message}")
    else:
        lines.append("- No audit issues.")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "This scaffold run validates the strategy contract and records artifacts. Real factor computation, rolling validation, and executable backtests are intentionally not mocked.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
