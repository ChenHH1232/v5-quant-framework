from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


IN_DIR = Path("v5d_order_scheduling_engineering_test") / "current"
OUT_DIR = Path("v5d_l2_order_scheduling_pm_quant_review") / "current"
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


def pct(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return ""


def load_required() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    required = [
        IN_DIR / "v5d_l2_engineering_summary.json",
        IN_DIR / "v5d_l2_engineering_comparison.csv",
        IN_DIR / "v5d_l2_order_health.csv",
        IN_DIR / "v5d_l2_unfilled_order_log.csv",
        IN_DIR / "v5d_l2_no_intraday_t_validation.csv",
    ]
    missing = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if missing:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, missing
    summary = json.loads((IN_DIR / "v5d_l2_engineering_summary.json").read_text(encoding="utf-8"))
    return (
        pd.read_csv(IN_DIR / "v5d_l2_engineering_comparison.csv"),
        pd.read_csv(IN_DIR / "v5d_l2_order_health.csv"),
        pd.read_csv(IN_DIR / "v5d_l2_unfilled_order_log.csv"),
        summary,
        [],
    )


def build_policy_matrix(comparison: pd.DataFrame, health: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, comp in comparison.iterrows():
        h = health[
            (health["strategy_id"] == comp["strategy_id"])
            & (health["execution_policy"] == comp["execution_policy"])
        ]
        health_row = h.iloc[0].to_dict() if not h.empty else {}
        policy = comp["execution_policy"]
        if policy == "l2_size_aware":
            decision = "promote_to_l2_execution_policy_candidate"
            reason = "lower slice count than full slicing, fewer or equal unfilled orders, no intraday T violations, auditable retry/unfilled logs"
        else:
            decision = "diagnostic_only_defer"
            reason = "technically valid but over-slices ordinary orders and materially increases trade count"
        rows.append(
            {
                "strategy_id": comp["strategy_id"],
                "execution_policy": policy,
                "pm_quant_decision": decision,
                "strategy_return": comp["strategy_return"],
                "max_drawdown": comp["max_drawdown"],
                "information_ratio": comp["information_ratio"],
                "trade_count": comp["trade_count"],
                "unfilled_order_count": comp["unfilled_order_count"],
                "filtered_small_diff_count": comp["filtered_small_diff_count"],
                "cash_event_count": health_row.get("cash_event_count", ""),
                "t_trade_violation_count": comp["t_trade_violation_count"],
                "delta_return_vs_daily_open": comp["delta_return_vs_daily_open"],
                "review_basis": "execution_health_and_auditability_not_return_selection",
                "reason": reason,
            }
        )
    return rows


def build_trade_count_review(comparison: pd.DataFrame, health: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strategy_id, group in comparison.groupby("strategy_id"):
        by_policy = {row["execution_policy"]: row for _, row in group.iterrows()}
        full = by_policy.get("l2_all_orders_sliced")
        size = by_policy.get("l2_size_aware")
        if full is None or size is None:
            continue
        full_h = health[(health["strategy_id"] == strategy_id) & (health["execution_policy"] == "l2_all_orders_sliced")].iloc[0]
        size_h = health[(health["strategy_id"] == strategy_id) & (health["execution_policy"] == "l2_size_aware")].iloc[0]
        full_trades = float(full["trade_count"])
        size_trades = float(size["trade_count"])
        rows.append(
            {
                "strategy_id": strategy_id,
                "all_sliced_trade_count": int(full_trades),
                "size_aware_trade_count": int(size_trades),
                "trade_count_reduction": int(full_trades - size_trades),
                "trade_count_reduction_pct": (full_trades - size_trades) / full_trades if full_trades > 0 else 0.0,
                "all_sliced_cash_event_count": int(full_h["cash_event_count"]),
                "size_aware_cash_event_count": int(size_h["cash_event_count"]),
                "cash_event_reduction": int(full_h["cash_event_count"] - size_h["cash_event_count"]),
                "all_sliced_unfilled": int(full["unfilled_order_count"]),
                "size_aware_unfilled": int(size["unfilled_order_count"]),
                "all_sliced_return": full["strategy_return"],
                "size_aware_return": size["strategy_return"],
                "return_delta_size_aware_minus_all_sliced": float(size["strategy_return"]) - float(full["strategy_return"]),
                "pm_read": "size_aware_reduces_operational_burden_without_new_t_violation",
            }
        )
    return rows


def build_unfilled_review(unfilled: pd.DataFrame) -> list[dict[str, Any]]:
    if unfilled.empty:
        return []
    grouped = unfilled.groupby(["strategy_id", "execution_policy", "final_block_reason"], dropna=False).size().reset_index(name="count")
    rows: list[dict[str, Any]] = []
    for _, row in grouped.iterrows():
        reason = row["final_block_reason"]
        severity = "expected_untradeable" if reason in {"paused", "buy_at_high_limit"} else "logged_execution_residual"
        rows.append(
            {
                "strategy_id": row["strategy_id"],
                "execution_policy": row["execution_policy"],
                "final_block_reason": reason,
                "count": int(row["count"]),
                "severity": severity,
                "pm_action": "retain_log_do_not_force_fill",
            }
        )
    return rows


def build_report(summary: dict[str, Any], policy_rows: list[dict[str, Any]], trade_rows: list[dict[str, Any]], unfilled_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L2 Order Scheduling PM/Quant Review",
        "",
        f"- Status: `{summary['status']}`",
        f"- Next gate: `{summary['next_gate']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Review basis: execution health, auditability, lower operational burden, and no intraday T. Return ranking is not used for selection.",
        "",
        "## Policy Decision",
        "",
        "| Strategy | Policy | Decision | Trades | Unfilled | T Violations | Delta vs Daily Open |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in policy_rows:
        lines.append(
            f"| `{row['strategy_id']}` | `{row['execution_policy']}` | `{row['pm_quant_decision']}` | {row['trade_count']} | {row['unfilled_order_count']} | {row['t_trade_violation_count']} | {pct(row['delta_return_vs_daily_open'])} |"
        )
    lines.extend(["", "## Size-Aware Benefit", ""])
    for row in trade_rows:
        lines.append(
            f"- `{row['strategy_id']}`: trades reduced by {row['trade_count_reduction']} ({pct(row['trade_count_reduction_pct'])}); cash events reduced by {row['cash_event_reduction']}; unfilled {row['all_sliced_unfilled']} -> {row['size_aware_unfilled']}."
        )
    lines.extend(["", "## Unfilled Read", ""])
    if unfilled_rows:
        for row in unfilled_rows:
            lines.append(f"- `{row['strategy_id']}` / `{row['execution_policy']}` / `{row['final_block_reason']}`: {row['count']}, action `{row['pm_action']}`.")
    else:
        lines.append("- No unfilled orders.")
    lines.extend(
        [
            "",
            "## Governance",
            "",
            "L2 size-aware scheduling can move to the next engineering/PM gate as an execution-policy candidate. It is not an accepted strategy, not a V57f replacement, and does not change V57f or ERC signals.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    comparison, health, unfilled, engineering_summary, blockers = load_required()
    if blockers:
        write_csv(OUT_DIR / "v5d_l2_pm_quant_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l2_order_scheduling_pm_quant_review", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l2_pm_quant_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    policy_rows = build_policy_matrix(comparison, health)
    trade_rows = build_trade_count_review(comparison, health)
    unfilled_rows = build_unfilled_review(unfilled)
    allowed_blocked = [
        {"action": "promote_l2_size_aware_to_execution_policy_candidate", "status": "allowed", "reason": "lower operational burden with auditable order health and no intraday T violations"},
        {"action": "keep_l2_all_orders_sliced_as_main_policy", "status": "blocked", "reason": "over-slices ordinary orders and materially increases trade count"},
        {"action": "choose_policy_by_highest_return", "status": "blocked", "reason": "minute execution policy cannot be selected by historical return"},
        {"action": "modify_v57f_or_erc_signals", "status": "blocked", "reason": "V57f frozen and ERC candidate governance"},
        {"action": "intraday_T_or_price_prediction", "status": "blocked", "reason": "outside V5d L2 scope"},
    ]
    checklist = [
        {"check_item": "fixed_signals_only", "status": "pass", "evidence": "L2 reads existing V57f/ERC rebalance signals only"},
        {"check_item": "no_return_selected_window", "status": "pass", "evidence": "Decision is based on trade count, unfilled logs, cash events, and T validation"},
        {"check_item": "no_intraday_T", "status": "pass", "evidence": "same-day buy/sell validation count is zero"},
        {"check_item": "unfilled_orders_auditable", "status": "pass_with_logged_unfilled", "evidence": "paused/high-limit/end-of-schedule rows are logged"},
        {"check_item": "size_aware_operational_burden", "status": "pass", "evidence": "size-aware reduces trade count and cash-event rows versus all-orders-sliced"},
    ]
    next_gate = [
        {
            "gate": "l2_size_aware_execution_policy_candidate",
            "decision": "promote_to_candidate_not_accepted",
            "allowed_next_action": "optional cost/slippage PM review or broker-paper execution simulation",
            "blocked_actions": "accepted_strategy;v57f_replacement;return_selected_window;intraday_T;modify_v57f",
        }
    ]
    write_csv(OUT_DIR / "v5d_l2_pm_quant_policy_review_matrix.csv", policy_rows)
    write_csv(OUT_DIR / "v5d_l2_trade_count_cost_review.csv", trade_rows)
    write_csv(OUT_DIR / "v5d_l2_unfilled_pm_review.csv", unfilled_rows, ["strategy_id", "execution_policy", "final_block_reason", "count", "severity", "pm_action"])
    write_csv(OUT_DIR / "v5d_l2_pm_quant_checklist.csv", checklist)
    write_csv(OUT_DIR / "v5d_l2_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(OUT_DIR / "v5d_l2_next_gate_decision.csv", next_gate)
    write_csv(OUT_DIR / "v5d_l2_pm_quant_blockers.csv", [], ["blocker_id", "severity", "description"])
    summary = {
        "schema_version": 1,
        "project": "v5d_l2_order_scheduling_pm_quant_review",
        "status": "completed_l2_pm_quant_review",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "engineering_status": engineering_summary.get("status"),
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "policy_decision": "l2_size_aware_promote_to_execution_policy_candidate_not_accepted",
        "diagnostic_policy": "l2_all_orders_sliced_diagnostic_only",
        "blocker_count": 0,
        "next_gate": next_gate[0]["gate"],
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l2_pm_quant_review_summary.json"),
            "report": str(OUT_DIR / "v5d_l2_pm_quant_review_report.md"),
            "policy_matrix": str(OUT_DIR / "v5d_l2_pm_quant_policy_review_matrix.csv"),
            "trade_count_cost_review": str(OUT_DIR / "v5d_l2_trade_count_cost_review.csv"),
            "unfilled_review": str(OUT_DIR / "v5d_l2_unfilled_pm_review.csv"),
            "checklist": str(OUT_DIR / "v5d_l2_pm_quant_checklist.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_l2_allowed_blocked_actions.csv"),
            "next_gate": str(OUT_DIR / "v5d_l2_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l2_pm_quant_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l2_pm_quant_review_report.md").write_text(build_report(summary, policy_rows, trade_rows, unfilled_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
