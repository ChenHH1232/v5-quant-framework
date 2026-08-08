from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit


ACTIVE_REGISTRY = Path("config") / "v5_active_model_registry.json"
PRIMARY_MODEL = "internal_subsleeve_mom12_70_30"
REPAIRED_BASELINE = "v57f_startup_preload_repaired_baseline"


OUT = Path("v5j_momentum_overlay_partial_buy_skip") / "current"
INPUT = Path("v5j_momentum_cash_neutral_engineering") / "current" / "v5j_momentum_cash_neutral_ledger.csv"
MAX_DATE = "2026-05-31"


def run_v5j_momentum_overlay_partial_buy_skip(root: Path = Path(".")) -> dict[str, Any]:
    registry = json.loads((root / ACTIVE_REGISTRY).read_text(encoding="utf-8-sig"))
    active = registry["active_models"][0]
    if active["model_id"] != PRIMARY_MODEL or active["baseline_id"] != REPAIRED_BASELINE:
        raise RuntimeError("Active-model registry conflicts with the frozen cash-path ledger contract.")
    boundary = historical_operation_audit("historical_reconciliation", MAX_DATE, root)
    if not boundary["allowed"]:
        raise RuntimeError("Historical cash-path replay is blocked by the operation boundary.")
    legs = _read_csv(root / INPUT)
    historical = [row for row in legs if str(row["trade_date"]) <= MAX_DATE]
    excluded = len(legs) - len(historical)
    executions, reconciliations = _replay(historical)
    audit = _audit(executions, reconciliations, excluded)
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "v5j_partial_buy_skip_execution_ledger.csv", executions)
    _write_csv(out / "v5j_partial_buy_skip_reconciliation.csv", reconciliations)
    _write_csv(out / "v5j_partial_buy_skip_audit.csv", [audit])
    _write_csv(out / "v5j_partial_buy_skip_rule_spec.csv", _rules())
    _write_csv(out / "v5j_partial_buy_skip_historical_boundary_audit.csv", [boundary])
    _write_csv(out / "v5j_partial_buy_skip_pm_gate.csv", [_decision(audit)])
    (out / "v5j_partial_buy_skip_report.md").write_text(_report(audit), encoding="utf-8")
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5j_momentum_overlay_partial_buy_skip",
        "primary_candidate": PRIMARY_MODEL,
        "baseline_id": REPAIRED_BASELINE,
        "status": "completed_historical_cash_path_limited_engineering",
        "market_data_max_date": MAX_DATE,
        "input_leg_count": len(historical),
        "post_boundary_leg_count_excluded": excluded,
        "strict_cash_reconciliation_pass": audit["strict_cash_reconciliation_pass"],
        "partial_or_skipped_buy_count": audit["partial_or_skipped_buy_count"],
        "value_base_change_count": audit["value_base_change_count"],
        "cross_sleeve_transfer_count": audit["cross_sleeve_transfer_count"],
        "accepted": False,
        "live_trading_approved": False,
        "pm_gate_decision": _decision(audit)["pm_gate_decision"],
    }
    (out / "v5j_partial_buy_skip_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _replay(legs: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for leg in legs:
        groups[(leg["trade_date"], leg["sleeve_id"])].append(leg)
    execution_rows: list[dict[str, Any]] = []
    reconciliation_rows: list[dict[str, Any]] = []
    for (trade_date, sleeve_id), group in sorted(groups.items()):
        confirmed_sells = [row for row in group if row["side"] == "sell" and _bool(row.get("bar_available"))]
        buys = sorted((row for row in group if row["side"] == "buy"), key=lambda row: str(row["code"]))
        available_cash = sum(_number(row.get("cash_amount")) for row in confirmed_sells)
        sell_cash = available_cash
        for row in confirmed_sells:
            execution_rows.append(_execution_row(row, row["cash_amount"], 1.0, "confirmed_sell", available_cash))
        for row in group:
            if row["side"] == "sell" and not _bool(row.get("bar_available")):
                execution_rows.append(_execution_row(row, 0.0, 0.0, "unfilled_sell_no_cash", available_cash))
        requested_buy = 0.0
        released_buy = 0.0
        partial_count = 0
        for row in buys:
            requested = _number(row.get("cash_amount"))
            requested_buy += requested
            executable = min(requested, max(available_cash, 0.0)) if _bool(row.get("bar_available")) else 0.0
            fill_fraction = executable / requested if requested else 0.0
            available_cash -= executable
            released_buy += executable
            if fill_fraction < 1.0:
                partial_count += 1
            status = "full_buy" if fill_fraction == 1.0 else "partial_buy" if executable > 0 else "skipped_buy"
            execution_rows.append(_execution_row(row, executable, fill_fraction, status, available_cash))
        reconciliation_rows.append({
            "trade_date": trade_date,
            "sleeve_id": sleeve_id,
            "confirmed_sell_cash": sell_cash,
            "requested_buy_cash": requested_buy,
            "released_buy_cash": released_buy,
            "residual_cash": available_cash,
            "partial_or_skipped_buy_count": partial_count,
            "cash_neutral_pass": available_cash >= -1e-12,
            "cross_sleeve_transfer": False,
            "value_base_changed": False,
        })
    return execution_rows, reconciliation_rows


def _execution_row(row: dict[str, str], executed_cash: float | str, fill_fraction: float, status: str, available_cash_after: float) -> dict[str, Any]:
    requested = _number(row.get("cash_amount"))
    return {
        "trade_date": row["trade_date"], "sleeve_id": row["sleeve_id"], "code": row["code"], "side": row["side"],
        "execution_time": row.get("execution_time", ""), "requested_cash": requested, "executed_cash": _number(executed_cash),
        "unfilled_cash": max(requested - _number(executed_cash), 0.0), "fill_fraction": fill_fraction,
        "execution_status": status, "available_sleeve_cash_after": available_cash_after,
        "value_base_unchanged": _bool(row.get("value_base_unchanged")), "cross_sleeve_transfer": False,
    }


def _audit(executions: list[dict[str, Any]], reconciliations: list[dict[str, Any]], excluded: int) -> dict[str, Any]:
    return {
        "audit_id": "same_sleeve_partial_buy_skip_cash_neutrality",
        "strict_cash_reconciliation_pass": all(bool(row["cash_neutral_pass"]) for row in reconciliations),
        "reconciliation_count": len(reconciliations),
        "partial_or_skipped_buy_count": sum(row["execution_status"] in {"partial_buy", "skipped_buy"} for row in executions),
        "total_unfilled_buy_cash": sum(row["unfilled_cash"] for row in executions if row["side"] == "buy"),
        "value_base_change_count": sum(not row["value_base_unchanged"] for row in executions),
        "cross_sleeve_transfer_count": sum(bool(row["cross_sleeve_transfer"]) for row in executions),
        "post_boundary_leg_count_excluded": excluded,
        "accepted": False,
    }


def _decision(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "pm_gate_decision": "partial_buy_skip_cash_path_pass_price_edge_not_retested_not_accepted" if audit["strict_cash_reconciliation_pass"] else "partial_buy_skip_cash_path_failed",
        "cash_path_engineering_pass": audit["strict_cash_reconciliation_pass"],
        "price_or_nav_improvement_claimed": False,
        "accepted": False,
        "live_trading_approved": False,
        "reason": "The policy closes a historical ledger only. It does not validate the resulting NAV or authorize orders.",
    }


def _rules() -> list[dict[str, str]]:
    return [
        {"rule_id": "historical_end", "rule": "Read legs dated no later than 2026-05-31 only."},
        {"rule_id": "confirmed_sell_cash_only", "rule": "Only filled same-sleeve sells create available cash."},
        {"rule_id": "partial_buy_skip", "rule": "Release a buy only up to confirmed available sleeve cash; otherwise partially fill or skip it."},
        {"rule_id": "no_borrowing", "rule": "No margin, cross-sleeve transfer, cash proxy, or fabricated fill."},
        {"rule_id": "value_base_immutable", "rule": "V57f value-base weights and orders remain unchanged."},
    ]


def _report(audit: dict[str, Any]) -> str:
    return "\n".join([
        "# V5j Partial Buy / Skip Cash Path", "",
        "- Scope is a historical ledger replay through 2026-05-31 only.",
        f"- Strict cash reconciliation pass: `{audit['strict_cash_reconciliation_pass']}`.",
        f"- Partial or skipped overlay buys: `{audit['partial_or_skipped_buy_count']}`.",
        f"- Unfilled overlay buy cash: `{audit['total_unfilled_buy_cash']:.8f}` weight units.",
        "- This proves ledger feasibility only; it does not claim a NAV improvement or approve trading.", "",
    ])


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


if __name__ == "__main__":
    print(json.dumps(run_v5j_momentum_overlay_partial_buy_skip(), ensure_ascii=False, indent=2))
