from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit


OUT = Path("v5l_qmt_execution_evidence_and_forward_readiness") / "current"
NO_ORDER = Path("v5_qmt_model_retest_packet") / "current" / "v5_qmt_actual_no_order_comparison.csv"
ENGINE = Path("v5_qmt_model_retest_packet") / "current" / "v5_qmt_prior_engine_result_comparison.csv"
LOCAL = Path("v5f_internal_subsleeve_deep_engineering") / "current" / "v5f_internal_subsleeve_deep_metrics.csv"


def run_v5l_qmt_execution_evidence(root: Path = Path(".")) -> dict[str, Any]:
    no_order, engine, local = _csv(root / NO_ORDER), _csv(root / ENGINE), _csv(root / LOCAL)
    primary = next(row for row in local if row["version_id"] == "internal_subsleeve_mom12_70_30")
    baseline = next(row for row in local if row["version_id"] == "v57f_startup_preload_repaired_baseline")
    comparison = [
        {"evidence_type": "local_idealized_nav", "model_id": "internal_subsleeve_mom12_70_30", "return_pct": float(primary["strategy_return"]) * 100, "delta_vs_local_baseline_pct_points": float(primary["delta_return_pct_points_vs_repaired_baseline"]), "interpretation": "historical research result"},
        *[{"evidence_type": "qmt_no_order_daily_close_replay", "model_id": r["model_id"], "return_pct": r["qmt_no_order_return_pct"], "delta_vs_local_baseline_pct_points": r["qmt_delta_return_pct_points_vs_repaired_baseline"], "interpretation": "not_order_or_fill_backtest"} for r in no_order if r["model_id"] in {"internal_subsleeve_mom12_70_30", "v57f_startup_preload_repaired_baseline"}],
        *[{"evidence_type": "existing_engine_export", "model_id": r["model_id"], "return_pct": r["qmt_engine_strategy_return_pct"], "delta_vs_local_baseline_pct_points": r["qmt_engine_delta_return_pct_points_vs_repaired_baseline"], "interpretation": "aggregate_order_fill_style_export_not_exact_submitted_contract"} for r in engine],
    ]
    residuals = [
        {"category": "price_source_and_adjustment", "status": "unresolved", "detail": "No-order replay return differs materially from local idealized NAV."},
        {"category": "timing_fee_and_slippage", "status": "unresolved", "detail": "Exact submitted script/config/fee snapshot is absent."},
        {"category": "limits_pauses_and_unfilled", "status": "partially_explained", "detail": "Existing engine export is aggregate only; per-rebalance source contract is absent."},
        {"category": "round_lot_and_cash_residual", "status": "unresolved", "detail": "No target-to-order-to-fill-to-position-to-cash chain is archived."},
        {"category": "dividend_and_corporate_action", "status": "unresolved", "detail": "No exact submitted platform total-return contract is archived."},
    ]
    missing = [{"evidence": name, "status": "missing", "required_action": "retain or manually export historical submitted artifact; do not reconstruct from memory"} for name in ["submitted_script_snapshot", "submitted_config_and_fee_snapshot", "frozen_target_file_per_rebalance", "target_order_fill_position_cash_chain"]]
    boundary = historical_operation_audit("generate_forward_targets", "2026-10-08", root)
    readiness = [{"field": field, "type": typ, "required": True, "future_value": "", "status": "blank_schema_only"} for field, typ in [("target_snapshot_id", "string"), ("target_sha256", "string"), ("pit_visible_date", "date"), ("order_export_sha256", "string"), ("fill_export_sha256", "string"), ("position_export_sha256", "string"), ("cash_reconciliation_error", "number")]]
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write(out / "v5l_local_qmt_comparison.csv", comparison); _write(out / "v5l_qmt_residual_classification.csv", residuals); _write(out / "v5l_missing_platform_contract_evidence.csv", missing); _write(out / "v5l_rebalance_target_order_fill_position_audit.csv", [{"scope": "historical_engine_export", "target_to_order_to_fill_to_position_to_cash": "unavailable", "reason": "exact_contract_evidence_missing"}]); _write(out / "v5l_forward_paper_schema.csv", readiness); _write(out / "v5l_forward_operation_boundary.csv", [boundary]); _write(out / "v5l_qmt_pm_gate_decision.csv", [{"pm_gate_decision": "candidate_needs_qmt_contract_repair", "accepted": False, "live_trading_approved": False}]); _write(out / "v5l_qmt_blockers.csv", missing)
    (out / "v5l_forward_paper_readiness_checklist.md").write_text("# Forward Paper Readiness Checklist\n\nThis is a blank schema only. No future target, platform, bridge, upload or order was created. Upon explicit future authorization: PIT-visible inputs -> frozen target + hash -> manual order export -> fill export -> position/cash reconciliation -> closeout. V5c tags remain observation metadata only.\n", encoding="utf-8")
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5l_qmt_execution_evidence", "status": "completed_historical_evidence_attribution_contract_incomplete", "local_primary_return_pct": float(primary["strategy_return"]) * 100, "existing_engine_primary_return_pct": 112.02, "existing_engine_edge_pct_points": 7.37, "qmt_contract_complete": False, "pm_gate_decision": "candidate_needs_qmt_contract_repair", "accepted": False, "live_trading_approved": False}
    (out / "v5l_qmt_execution_attribution_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5l_qmt_execution_attribution_report.md").write_text("# V5l QMT Execution Evidence\n\n- QMT no-order replay is explicitly separated from an order/fill engine result.\n- Existing engine aggregate export is positive versus baseline, but cannot establish exact parity without the submitted contract chain.\n- Future paper readiness is schema-only and hard-blocked after 2026-05-31.\n", encoding="utf-8")
    return summary


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5l_qmt_execution_evidence(), ensure_ascii=False, indent=2))
