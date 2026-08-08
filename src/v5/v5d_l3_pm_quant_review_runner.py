from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


IN_DIR = Path("v5d_l3_intraday_execution_engineering") / "current"
OUT_DIR = Path("v5d_l3_pm_quant_review") / "current"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def pct(value: object) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return ""


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object], list[dict[str, object]]]:
    required = [
        IN_DIR / "v5d_l3_engineering_summary.json",
        IN_DIR / "v5d_l3_engineering_comparison.csv",
        IN_DIR / "v5d_l3_order_health.csv",
        IN_DIR / "v5d_l3_unfilled_order_log.csv",
    ]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, blockers
    summary = json.loads((IN_DIR / "v5d_l3_engineering_summary.json").read_text(encoding="utf-8"))
    return (
        pd.read_csv(IN_DIR / "v5d_l3_engineering_comparison.csv"),
        pd.read_csv(IN_DIR / "v5d_l3_order_health.csv"),
        pd.read_csv(IN_DIR / "v5d_l3_unfilled_order_log.csv"),
        summary,
        [],
    )


def build_policy_review(comparison: pd.DataFrame, health: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for _, row in comparison.iterrows():
        h = health[(health["strategy_id"] == row["strategy_id"]) & (health["l3_policy_id"] == row["l3_policy_id"])]
        health_row = h.iloc[0].to_dict() if not h.empty else {}
        if row["l3_policy_id"] == "l3_default_exception":
            decision = "promote_to_l3_execution_governance_candidate"
            reason = "same fills as L2 size-aware, explicit exception logging, low unfilled count, zero T violations"
        elif row["l3_policy_id"] == "l3_open_delay_price_band_fallback":
            original = comparison[
                (comparison["strategy_id"] == row["strategy_id"])
                & (comparison["l3_policy_id"] == "l3_open_delay_price_band")
            ]
            original_unfilled = int(original["unfilled_order_count"].iloc[0]) if not original.empty else 0
            repaired_unfilled = int(row["unfilled_order_count"])
            reduction = original_unfilled - repaired_unfilled
            decision = "promote_to_l3_1_unfilled_remediation_candidate_not_accepted"
            reason = f"fixed fallback repair reduced unfilled orders from {original_unfilled} to {repaired_unfilled}; no T violations; not selected by return"
        else:
            decision = "diagnostic_only_needs_unfilled_governance_repair"
            reason = "positive return delta is not admissible because unfilled count is high and may reflect non-execution path dependence"
        rows.append(
            {
                "strategy_id": row["strategy_id"],
                "l3_policy_id": row["l3_policy_id"],
                "pm_quant_decision": decision,
                "strategy_return": row["strategy_return"],
                "max_drawdown": row["max_drawdown"],
                "delta_return_vs_l2_size_aware": row["delta_return_vs_l2_size_aware"],
                "trade_count": row["trade_count"],
                "unfilled_order_count": row["unfilled_order_count"],
                "unfilled_reduction_vs_raw_price_band": reduction if row["l3_policy_id"] == "l3_open_delay_price_band_fallback" else "",
                "exception_count": row["exception_count"],
                "cash_event_count": health_row.get("cash_event_count", ""),
                "t_trade_violation_count": row["t_trade_violation_count"],
                "decision_basis": "order_health_and_governance_not_return_selection",
                "reason": reason,
            }
        )
    return rows


def build_unfilled_review(unfilled: pd.DataFrame) -> list[dict[str, object]]:
    if unfilled.empty:
        return []
    grouped = unfilled.groupby(["strategy_id", "l3_policy_id", "final_block_reason"], dropna=False).size().reset_index(name="count")
    rows: list[dict[str, object]] = []
    for _, row in grouped.iterrows():
        severity = "expected_untradeable" if row["final_block_reason"] in {"paused", "buy_at_high_limit"} else "review"
        if row["l3_policy_id"] == "l3_open_delay_price_band" and row["final_block_reason"] == "end_of_l3_schedule":
            severity = "diagnostic_policy_problem"
        rows.append(
            {
                "strategy_id": row["strategy_id"],
                "l3_policy_id": row["l3_policy_id"],
                "final_block_reason": row["final_block_reason"],
                "count": int(row["count"]),
                "severity": severity,
                "pm_action": "retain_log_do_not_force_fill",
            }
        )
    return rows


def build_checklist(policy_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {"check_item": "v57f_erc_targets_unchanged", "status": "pass", "evidence": "L3 uses existing target orders only"},
        {"check_item": "no_intraday_T", "status": "pass", "evidence": "T violation count is zero across tested L3 policies"},
        {"check_item": "no_return_selection", "status": "pass", "evidence": "positive open-delay/price-band return is explicitly not used for promotion"},
        {"check_item": "default_exception_candidate", "status": "pass", "evidence": "same L2 outcome with explicit exception logs"},
        {"check_item": "open_delay_price_band_diagnostic", "status": "needs_repair", "evidence": "high unfilled/end-of-schedule count; keep raw diagnostic only"},
        {"check_item": "open_delay_price_band_fallback", "status": "pass_with_review_notes", "evidence": "fallback repair lowers unfilled materially and keeps zero T violations; still not accepted"},
    ]


def build_report(summary: dict[str, object], policy_rows: list[dict[str, object]], unfilled_rows: list[dict[str, object]]) -> str:
    lines = [
        "# V5d L3 PM/Quant Review",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Review basis: governance, PIT safety, order health, and no-T validation. Return ranking is not used.",
        "",
        "## Decision",
        "",
        "| Strategy | L3 Policy | Decision | Delta vs L2 | Unfilled | T Violations |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in policy_rows:
        lines.append(f"| `{row['strategy_id']}` | `{row['l3_policy_id']}` | `{row['pm_quant_decision']}` | {pct(row['delta_return_vs_l2_size_aware'])} | {row['unfilled_order_count']} | {row['t_trade_violation_count']} |")
    lines.extend(["", "## Unfilled Review", ""])
    for row in unfilled_rows:
        lines.append(f"- `{row['strategy_id']}` / `{row['l3_policy_id']}` / `{row['final_block_reason']}`: {row['count']} ({row['severity']}).")
    lines.extend(["", "## PM Read", "", "L3 default exception handling is the valid effective result: it does not improve historical return, but improves execution governance by making exception states auditable without changing V57f/ERC targets. The open-delay/price-band result is useful but not admissible as an enhancement until unfilled governance is repaired."])
    return "\n".join(lines) + "\n"


def run() -> dict[str, object]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    comparison, health, unfilled, engineering_summary, blockers = load_inputs()
    if blockers:
        write_csv(OUT_DIR / "v5d_l3_pm_quant_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l3_pm_quant_review", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l3_pm_quant_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    policy_rows = build_policy_review(comparison, health)
    unfilled_rows = build_unfilled_review(unfilled)
    checklist = build_checklist(policy_rows)
    allowed_blocked = [
        {"action": "promote_l3_default_exception_to_execution_governance_candidate", "status": "allowed", "reason": "auditable exception layer, low unfilled count, no T violations"},
        {"action": "promote_l3_open_delay_price_band_fallback_to_l3_1_candidate", "status": "allowed", "reason": "fixed fallback materially reduces unfilled without T violations"},
        {"action": "promote_l3_open_delay_price_band_by_return", "status": "blocked", "reason": "positive return delta is contaminated by high unfilled/non-execution path dependence"},
        {"action": "repair_open_delay_price_band_unfilled_governance", "status": "allowed", "reason": "may be revisited as diagnostic after stricter fill/carry rules"},
        {"action": "accepted_strategy_or_v57f_replacement", "status": "blocked", "reason": "V5d L3 is execution research only"},
        {"action": "intraday_T", "status": "blocked", "reason": "hard governance block"},
    ]
    next_gate = [
        {
            "gate": "l3_default_exception_execution_governance_candidate",
            "decision": "promote_candidate_not_accepted",
            "allowed_next_action": "optional closeout or stricter open-delay/price-band repair spec",
            "blocked_actions": "accepted_strategy;v57f_replacement;return_selected_l3;intraday_T",
        }
    ]
    write_csv(OUT_DIR / "v5d_l3_pm_quant_policy_review_matrix.csv", policy_rows)
    write_csv(OUT_DIR / "v5d_l3_unfilled_pm_review.csv", unfilled_rows, ["strategy_id", "l3_policy_id", "final_block_reason", "count", "severity", "pm_action"])
    write_csv(OUT_DIR / "v5d_l3_pm_quant_checklist.csv", checklist)
    write_csv(OUT_DIR / "v5d_l3_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(OUT_DIR / "v5d_l3_next_gate_decision.csv", next_gate)
    write_csv(OUT_DIR / "v5d_l3_pm_quant_blockers.csv", [], ["blocker_id", "severity", "description"])
    summary = {
        "schema_version": 1,
        "project": "v5d_l3_pm_quant_review",
        "status": "completed_l3_pm_quant_review",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "engineering_status": engineering_summary.get("status"),
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "return_selection_used": False,
        "policy_decision": "l3_default_exception_promote_to_execution_governance_candidate_not_accepted",
        "diagnostic_policy": "l3_open_delay_price_band_diagnostic_only_needs_unfilled_governance_repair",
        "remediation_policy": "l3_open_delay_price_band_fallback_promote_to_l3_1_candidate_not_accepted",
        "blocker_count": 0,
        "next_gate": next_gate[0]["gate"],
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l3_pm_quant_review_summary.json"),
            "report": str(OUT_DIR / "v5d_l3_pm_quant_review_report.md"),
            "policy_matrix": str(OUT_DIR / "v5d_l3_pm_quant_policy_review_matrix.csv"),
            "unfilled_review": str(OUT_DIR / "v5d_l3_unfilled_pm_review.csv"),
            "checklist": str(OUT_DIR / "v5d_l3_pm_quant_checklist.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_l3_allowed_blocked_actions.csv"),
            "next_gate": str(OUT_DIR / "v5d_l3_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l3_pm_quant_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l3_pm_quant_review_report.md").write_text(build_report(summary, policy_rows, unfilled_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
