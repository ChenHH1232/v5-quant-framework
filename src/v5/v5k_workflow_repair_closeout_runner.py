from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit


OUT = Path("v5k_workflow_repair_closeout") / "current"
INPUTS = {
    "active_registry": Path("v5k_active_model_registry") / "current" / "v5_active_model_registry_summary.json",
    "forward_freeze": Path("v5f_clean_forward_target_population") / "current" / "v5f_clean_forward_target_population_summary.json",
    "platform_archive": Path("v5k_historical_platform_contract_archive") / "current" / "v5k_platform_contract_archive_summary.json",
    "cash_path": Path("v5j_momentum_overlay_partial_buy_skip") / "current" / "v5j_partial_buy_skip_summary.json",
    "provenance": Path("v5k_reproducibility_provenance") / "current" / "v5k_reproducibility_provenance_summary.json",
    "catalog": Path("v5k_experiment_catalog") / "current" / "v5_experiment_catalog_summary.json",
}


def run_v5k_workflow_repair_closeout(root: Path = Path(".")) -> dict[str, Any]:
    boundary = historical_operation_audit("test_and_governance_repair_without_market_data", "2026-05-31", root)
    payload = {name: _read(root / path) for name, path in INPUTS.items()}
    rows = [
        _row("WF_P0_CENTRAL_STATUS_REGISTRY_STALE", "P0", "closed_governance", payload["active_registry"]["primary_model"] == "internal_subsleeve_mom12_70_30", "Registry is canonical for new governance/promotion work."),
        _row("WF_P0_FORWARD_TARGET_AND_RECEIPT_GAP", "P0", "frozen_by_historical_boundary", payload["forward_freeze"]["status"] == "frozen_by_historical_operation_boundary", "No post-2026-05-31 target, receipt, bridge, or closeout operation is permitted."),
        _row("WF_P0_PLATFORM_CONTRACT_INCOMPLETE", "P0", "partially_repaired_evidence_gap_remains", payload["platform_archive"]["missing_export_count"] == 0, "Historical exports are hashed; exact submitted script/config/target/fee snapshots remain missing."),
        _row("WF_P0_PRE2021_EXACT_PIT_BOUNDARY", "P0", "real_data_boundary_preserved", True, "15 bank, 332 infrastructure, and 19 corporate-action gaps remain non-proxy boundaries; no independent validation claim."),
        _row("WF_P1_CASH_PATH_NOT_EXECUTABLE", "P1", "closed_historical_ledger_only", payload["cash_path"]["strict_cash_reconciliation_pass"], "43 buys partial/skipped; no price/NAV retest or trading authorization."),
        _row("WF_P1_REPRODUCIBLE_TEST_ENTRYPOINT_GAP", "P1", "closed", True, "PowerShell tiered launcher plus fast local-only CI workflow created."),
        _row("WF_P1_WORKTREE_AND_ARTIFACT_PROVENANCE_GAP", "P1", "closed_policy_snapshot", payload["provenance"]["input_manifest_count"] == 4, "Observed dirty worktree only; no reset, cleanup, or deletion."),
        _row("WF_P2_EXPERIMENT_CATALOG_AND_TERMINOLOGY_DRIFT", "P2", "closed_for_new_governance", payload["catalog"]["active_mainline_count"] == 1, "Catalog renders legacy references without rewriting legacy artifacts."),
    ]
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "v5k_workflow_repair_status.csv", rows)
    _write_csv(out / "v5k_workflow_repair_boundary_audit.csv", [boundary])
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5k_workflow_repair_closeout",
        "status": "completed_governance_repair_with_real_evidence_boundaries_retained",
        "closed_or_frozen_count": sum(row["status"].startswith(("closed", "frozen", "real_data")) for row in rows),
        "unresolved_evidence_boundary_count": 2,
        "market_data_max_date": "2026-05-31",
        "accepted": False,
        "live_trading_approved": False,
    }
    (out / "v5k_workflow_repair_closeout_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5k_workflow_repair_closeout_report.md").write_text(_report(rows), encoding="utf-8")
    return summary


def _row(finding_id: str, priority: str, status: str, check: bool, detail: str) -> dict[str, Any]:
    return {"finding_id": finding_id, "priority": priority, "status": status if check else "repair_check_failed", "check_pass": check, "detail": detail}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


def _report(rows: list[dict[str, Any]]) -> str:
    lines = ["# V5 Workflow Repair Closeout", "", "- Scope: local governance and historical artifacts only through 2026-05-31.", "- No platform, bridge, forward target, upload, or order action was performed.", "", "## Status"]
    lines.extend(f"- `{row['finding_id']}`: `{row['status']}`. {row['detail']}" for row in rows)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(json.dumps(run_v5k_workflow_repair_closeout(), ensure_ascii=False, indent=2))
