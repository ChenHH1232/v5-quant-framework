from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5m_forward_paper_cycle_readiness") / "current"


def run_v5m_forward_paper_cycle_readiness(root: Path = Path(".")) -> dict[str, Any]:
    boundary = json.loads((root / "config/v5_historical_operation_boundary.json").read_text(encoding="utf-8-sig"))
    target_schema = _schema([("snapshot_id", "string"), ("candidate_id", "string"), ("baseline_id", "string"), ("pit_visible_date", "date"), ("input_manifest_sha256", "string"), ("target_sha256", "string"), ("target_frozen_at", "timestamp"), ("state_tag_metadata", "string")])
    reconciliation = _schema([("target_sha256", "string"), ("order_export_sha256", "string"), ("fill_export_sha256", "string"), ("position_export_sha256", "string"), ("cash_export_sha256", "string"), ("cash_reconciliation_error", "number"), ("closeout_status", "string")])
    freshness = [{"gate": gate, "status": "required_before_future_authorized_cycle", "allowed_now": False} for gate in ["data_freshness_verified", "pit_visible_date_verified", "repaired_baseline_target_source_verified", "target_frozen_and_hashed", "manual_export_received_after_explicit_authorization"]]
    trigger = [{"trigger": "explicit_user_authorization_after_historical_boundary", "required": True, "current_status": "not_authorized"}, {"trigger": "official_repaired_v57f_signal_available", "required": True, "current_status": "not_checked"}, {"trigger": "no_platform_or_order_before_all_gates", "required": True, "current_status": "enforced"}]
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write(out / "v5m_target_snapshot_schema.csv", target_schema); _write(out / "v5m_target_fill_position_cash_reconciliation_schema.csv", reconciliation); _write(out / "v5m_forward_data_freshness_gate.csv", freshness); _write(out / "v5m_forward_authorization_boundary.csv", [{"market_data_max_date": boundary["market_data_max_date"], "future_target_generation": "blocked", "platform_start": "blocked", "upload_receive_position": "blocked", "order_creation": "blocked"}]); _write(out / "v5m_forward_trigger_conditions.csv", trigger); _write(out / "v5m_forward_blockers.csv", [{"blocker_id": "historical_boundary", "detail": "Preparation is schema-only; no forward evidence exists."}])
    (out / "v5m_forward_paper_cycle_checklist.md").write_text("# Future Paper Cycle Checklist\n\n1. Obtain explicit authorization.\n2. Verify fresh PIT-visible inputs.\n3. Freeze and hash the official repaired target.\n4. Export order/fill/position/cash records manually.\n5. Reconcile target to cash and close the cycle.\n\nV5c remains observation metadata; V5d/V5h remain execution observations. This document creates no target, no platform session and no order.\n", encoding="utf-8")
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5m_forward_paper_cycle_readiness", "status": "schema_only_future_cycle_readiness", "future_target_generated": False, "platform_started": False, "forward_evidence_exists": False, "accepted": False}
    (out / "v5m_forward_readiness_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _schema(items: list[tuple[str, str]]) -> list[dict[str, Any]]: return [{"field": name, "type": typ, "future_value": "", "schema_only": True} for name, typ in items]
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8-sig", newline="") as h: w = csv.DictWriter(h, fieldnames=keys); w.writeheader(); w.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5m_forward_paper_cycle_readiness(), ensure_ascii=False, indent=2))
