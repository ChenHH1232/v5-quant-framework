from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5m_qmt_historical_contract_recovery") / "current"
FILES = {
    "qmt_no_order_script": Path("v5_qmt_model_retest_packet/current/qmt_scripts/v5_qmt_no_order_nav_replay.py"),
    "qmt_no_order_target_schedule": Path("v5_qmt_model_retest_packet/current/qmt_inputs/v5_qmt_target_weight_schedule.csv"),
    "qmt_no_order_daily_result": Path("v5_qmt_model_retest_packet/current/qmt_results/v5_qmt_nav_replay_daily.csv"),
    "qmt_no_order_metrics": Path("v5_qmt_model_retest_packet/current/qmt_results/v5_qmt_nav_replay_metrics.csv"),
    "aggregate_engine_comparison": Path("v5_qmt_model_retest_packet/current/v5_qmt_prior_engine_result_comparison.csv"),
    "submitted_engine_script": Path("v5m_missing_no_file"),
    "submitted_engine_config_fee": Path("v5m_missing_no_file"),
    "engine_target_snapshot_per_rebalance": Path("v5m_missing_no_file"),
    "engine_order_export": Path("v5m_missing_no_file"),
    "engine_fill_export": Path("v5m_missing_no_file"),
    "engine_position_cash_export": Path("v5m_missing_no_file"),
}


def run_v5m_qmt_historical_contract_recovery(root: Path = Path(".")) -> dict[str, Any]:
    manifest = [_row(root / path, name) for name, path in FILES.items()]
    missing = [row for row in manifest if not row["exists"]]
    audit = [
        {"stage": "local_idealized_nav", "available": True, "detail": "Local historical research result."},
        {"stage": "qmt_no_order_daily_close_replay", "available": True, "detail": "Explicitly not an order/fill backtest."},
        {"stage": "qmt_engine_aggregate_export", "available": True, "detail": "Summary comparison exists, but not a complete contract chain."},
        {"stage": "target_to_order_to_fill_to_position_to_cash", "available": False, "detail": "Missing submitted target/order/fill/position/cash artifacts."},
    ]
    residuals = [{"category": name, "status": status, "detail": detail} for name, status, detail in [
        ("price_and_adjustment", "unresolved", "No exact submitted price/adjustment contract."),
        ("timing", "unresolved", "No submitted engine script/config snapshot."),
        ("fees_and_slippage", "unresolved", "No submitted fee/slippage configuration."),
        ("limits_pauses_unfilled", "unresolved", "No per-order/fill export."),
        ("lot_and_cash_residual", "unresolved", "No position/cash rollforward."),
        ("dividend_corporate_action", "unresolved", "No engine total-return ledger."),
        ("target_position_deviation", "unresolved", "No per-rebalance target-position chain."),
        ("unexplained_residual", "present", "Exact parity cannot be claimed."),
    ]]
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write(out / "v5m_qmt_contract_file_hash_manifest.csv", manifest); _write(out / "v5m_qmt_local_engine_evidence_matrix.csv", audit); _write(out / "v5m_target_order_fill_position_cash_audit.csv", audit[-1:]); _write(out / "v5m_qmt_residual_attribution.csv", residuals); _write(out / "v5m_qmt_missing_user_artifacts.csv", [{"artifact": row["artifact"], "required_for": "exact_historical_qmt_contract", "requested": False, "reason": "No user prompt required to record a missing local artifact."} for row in missing]); _write(out / "v5m_qmt_pm_gate_decision.csv", [{"pm_gate_decision": "candidate_needs_qmt_historical_contract_recovery", "accepted": False, "live_trading_approved": False}]); _write(out / "v5m_qmt_blockers.csv", missing)
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5m_qmt_historical_contract_recovery", "status": "historical_qmt_contract_incomplete", "available_file_count": len(manifest) - len(missing), "missing_contract_artifact_count": len(missing), "exact_qmt_contract_recovered": False, "accepted": False}
    (out / "v5m_qmt_contract_recovery_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5m_qmt_contract_recovery_report.md").write_text("# V5m QMT Historical Contract Recovery\n\nExisting QMT no-order inputs/results are hashed and retained as no-order evidence only. Aggregate engine comparison exists, but the historical submitted script/config/target/order/fill/position/cash contract is absent. No contract is reconstructed from memory.\n", encoding="utf-8")
    return summary


def _row(path: Path, artifact: str) -> dict[str, Any]:
    return {"artifact": artifact, "path": str(path), "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else "", "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "", "classification": "no_order_replay_input_or_output" if artifact.startswith("qmt_no_order") else "engine_contract_requirement"}
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8-sig", newline="") as h: w = csv.DictWriter(h, fieldnames=keys); w.writeheader(); w.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5m_qmt_historical_contract_recovery(), ensure_ascii=False, indent=2))
