from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit, load_boundary


OUT = Path("v5k_active_model_registry") / "current"
REGISTRY = Path("config") / "v5_active_model_registry.json"
CENTRAL_STATUS = Path("docs") / "governance" / "status_registry.json"
PRIMARY = Path("v5f_internal_subsleeve_pm_quant_review") / "current" / "v5f_internal_subsleeve_review_summary.json"


def run_v5k_active_model_registry(root: Path = Path(".")) -> dict[str, Any]:
    registry = _read_json(root / REGISTRY)
    primary = _read_json(root / PRIMARY)
    central = _read_json(root / CENTRAL_STATUS)
    boundary = load_boundary(root)
    active = registry["active_models"]
    row = active[0]
    checks = [
        _check("primary_model_matches_review", row["model_id"] == primary["primary_candidate"], primary["primary_candidate"]),
        _check("baseline_is_repaired", row["baseline_id"] == "v57f_startup_preload_repaired_baseline", row["baseline_id"]),
        _check("formal_end_matches_boundary", registry["formal_backtest_window"]["end"] == boundary["market_data_max_date"], boundary["market_data_max_date"]),
        _check("accepted_false", not row["accepted"], row["accepted"]),
        _check("live_approved_false", not row["live_trading_approved"], row["live_trading_approved"]),
        _check("central_status_points_to_authoritative_registry", central["v5_active_model_registry"]["authoritative_path"] == str(REGISTRY).replace("\\", "/"), central["v5_active_model_registry"]["authoritative_path"]),
    ]
    forward_block = historical_operation_audit("generate_forward_targets", "2026-10-08", root)
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "v5_active_model_registry.csv", _flatten(registry))
    _write_csv(out / "v5_active_model_registry_audit.csv", checks)
    _write_csv(out / "v5_historical_operation_boundary_audit.csv", [forward_block])
    (out / "v5_active_model_registry_report.md").write_text(_report(registry, checks, forward_block), encoding="utf-8")
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5k_active_model_registry",
        "status": "completed_active_model_registry_and_historical_boundary_enforced",
        "primary_model": row["model_id"],
        "baseline": row["baseline_id"],
        "market_data_max_date": boundary["market_data_max_date"],
        "post_boundary_forward_target_generation_allowed": forward_block["allowed"],
        "accepted": False,
        "live_trading_approved": False,
    }
    (out / "v5_active_model_registry_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _flatten(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in registry["active_models"] + registry["research_lines"]:
        rows.append({"model_id": item["model_id"], "role": item["role"], "baseline_id": item["baseline_id"], "reason_or_action": item.get("reason", item.get("allowed_next_action", "")), "accepted": item.get("accepted", False), "live_trading_approved": item.get("live_trading_approved", False)})
    return rows


def _check(check_id: str, passed: bool, observed: Any) -> dict[str, Any]:
    return {"check_id": check_id, "status": "pass" if passed else "fail", "observed": observed}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def _report(registry: dict[str, Any], checks: list[dict[str, Any]], forward_block: dict[str, Any]) -> str:
    return "\n".join([
        "# V5 Active Model Registry", "",
        f"- Primary: `{registry['active_models'][0]['model_id']}`.",
        f"- Baseline: `{registry['baseline']['model_id']}`.",
        f"- Historical market-data boundary: `{registry['as_of_market_data_date']}`.",
        f"- Forward target generation for 2026-10-08 allowed: `{forward_block['allowed']}`.",
        "- Legacy runners are not retroactively rewritten; new governance and promotion work must reference this registry.",
        "",
        "## Audit", *[f"- {row['check_id']}: `{row['status']}`" for row in checks], "",
    ])


if __name__ == "__main__":
    print(json.dumps(run_v5k_active_model_registry(), ensure_ascii=False, indent=2))
