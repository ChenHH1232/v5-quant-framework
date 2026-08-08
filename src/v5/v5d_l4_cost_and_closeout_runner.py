from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


L4_DIR = Path("v5d_l4_rebalance_neighborhood_order_completion") / "current"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"
BROKER_COMMISSION_RATE = 0.000095
MIN_COMMISSION = 5.0


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


def broker_commission(value: float) -> float:
    return max(value * BROKER_COMMISSION_RATE, MIN_COMMISSION) if value > 0 else 0.0


def pct(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return ""


def load_required() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    required = [
        L4_DIR / "v5d_l4_order_completion_summary.json",
        L4_DIR / "v5d_l4_pm_quant_review_summary.json",
        L4_DIR / "v5d_l4_engineering_comparison.csv",
        L4_DIR / "v5d_l4_unfilled_reason_summary.csv",
    ]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        return pd.DataFrame(), pd.DataFrame(), {}, blockers
    comparison = pd.read_csv(L4_DIR / "v5d_l4_engineering_comparison.csv")
    unfilled = pd.read_csv(L4_DIR / "v5d_l4_unfilled_reason_summary.csv")
    pm_summary = json.loads((L4_DIR / "v5d_l4_pm_quant_review_summary.json").read_text(encoding="utf-8"))
    return comparison, unfilled, pm_summary, []


def load_trades(strategy_id: str, version_id: str) -> pd.DataFrame:
    path = L4_DIR / "runs" / strategy_id / version_id / "trades.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def build_cost_rows(comparison: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strategy_id in sorted(comparison["strategy_id"].unique()):
        for version_id in ["baseline_l2_size_aware", "l4_exception_governed_completion"]:
            comp = comparison[(comparison["strategy_id"] == strategy_id) & (comparison["version_id"] == version_id)].iloc[0]
            trades = load_trades(strategy_id, version_id)
            values = pd.to_numeric(trades.get("value", pd.Series(dtype=float)), errors="coerce").fillna(0)
            embedded_commission = pd.to_numeric(trades.get("commission", pd.Series(dtype=float)), errors="coerce").fillna(0)
            broker_commissions = [broker_commission(float(v)) for v in values if float(v) > 0]
            total_value = float(values.sum())
            broker_total = float(sum(broker_commissions))
            min_fee_count = int(sum(1 for c in broker_commissions if abs(c - MIN_COMMISSION) < 1e-9))
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "version_id": version_id,
                    "trade_count": int(comp["trade_count"]),
                    "total_traded_value": total_value,
                    "embedded_engineering_commission": float(embedded_commission.sum()),
                    "broker_review_commission_rate": BROKER_COMMISSION_RATE,
                    "broker_review_commission": broker_total,
                    "minimum_commission_order_count": min_fee_count,
                    "minimum_commission_order_pct": min_fee_count / len(broker_commissions) if broker_commissions else 0.0,
                    "broker_commission_bps_on_traded_value": broker_total / total_value * 10000.0 if total_value > 0 else 0.0,
                    "strategy_return": comp["strategy_return"],
                    "max_drawdown": comp["max_drawdown"],
                    "unfilled_order_count": int(comp["unfilled_order_count"]),
                    "t_violation_count": int(comp["t_violation_count"]),
                }
            )
    return rows


def build_delta_rows(cost_rows: list[dict[str, Any]], comparison: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_key = {(r["strategy_id"], r["version_id"]): r for r in cost_rows}
    for strategy_id in sorted(comparison["strategy_id"].unique()):
        base = by_key[(strategy_id, "baseline_l2_size_aware")]
        cand = by_key[(strategy_id, "l4_exception_governed_completion")]
        rows.append(
            {
                "strategy_id": strategy_id,
                "candidate": "l4_exception_governed_completion",
                "delta_trade_count": cand["trade_count"] - base["trade_count"],
                "delta_traded_value": cand["total_traded_value"] - base["total_traded_value"],
                "delta_broker_commission": cand["broker_review_commission"] - base["broker_review_commission"],
                "baseline_unfilled": base["unfilled_order_count"],
                "candidate_unfilled": cand["unfilled_order_count"],
                "unfilled_reduction": base["unfilled_order_count"] - cand["unfilled_order_count"],
                "baseline_return": base["strategy_return"],
                "candidate_return": cand["strategy_return"],
                "delta_return": float(cand["strategy_return"]) - float(base["strategy_return"]),
                "baseline_max_drawdown": base["max_drawdown"],
                "candidate_max_drawdown": cand["max_drawdown"],
                "t_violation_count": cand["t_violation_count"],
                "pm_read": "candidate_cost_acceptable_for_closeout" if cand["t_violation_count"] == 0 and cand["unfilled_order_count"] < base["unfilled_order_count"] else "needs_review",
            }
        )
    return rows


def build_unfilled_closeout(unfilled: pd.DataFrame) -> list[dict[str, Any]]:
    if unfilled.empty:
        return []
    rows: list[dict[str, Any]] = []
    cand = unfilled[unfilled["version_id"] == "l4_exception_governed_completion"]
    for _, row in cand.iterrows():
        reason = str(row["unfilled_reason"])
        if reason == "paused":
            action = "archive_as_true_untradeable_execution_residual"
        elif reason == "end_of_l3_schedule":
            action = "archive_as_finite_D2_residual_no_infinite_chase"
        else:
            action = "archive_with_reason_review"
        rows.append(
            {
                "strategy_id": row["strategy_id"],
                "version_id": row["version_id"],
                "unfilled_reason": reason,
                "count": row["count"],
                "amount_sum": row["amount_sum"],
                "closeout_action": action,
            }
        )
    return rows


def build_report(summary: dict[str, Any], delta_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L4 Execution Policy Candidate Cost and Closeout",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: cost and governance closeout only; no V57f/ERC modification, no T, no return selection.",
        "",
        "| Strategy | Unfilled Reduction | Delta Return | Delta Broker Commission | T Violations | Read |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in delta_rows:
        lines.append(
            f"| `{row['strategy_id']}` | {row['unfilled_reduction']} | {pct(row['delta_return'])} | {float(row['delta_broker_commission']):.2f} | {row['t_violation_count']} | `{row['pm_read']}` |"
        )
    lines.extend(
        [
            "",
            "## PM Read",
            "",
            "L4 exception-governed completion is kept as an execution policy candidate because it reduces finite residual unfilled orders with zero T violations. The small return drag is accepted as execution realism, not treated as strategy underperformance requiring tuning.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    comparison, unfilled, pm_summary, blockers = load_required()
    if blockers:
        write_csv(L4_DIR / "v5d_l4_cost_closeout_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l4_cost_and_closeout", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (L4_DIR / "v5d_l4_cost_closeout_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    cost_rows = build_cost_rows(comparison)
    delta_rows = build_delta_rows(cost_rows, comparison)
    residual_rows = build_unfilled_closeout(unfilled)
    allowed_blocked = [
        {"action": "retain_l4_exception_governed_completion_as_candidate", "status": "allowed", "reason": "unfilled improves and no T violations"},
        {"action": "tune_D1_D2_by_return", "status": "blocked", "reason": "D+ windows cannot be selected by historical return"},
        {"action": "infinite_order_chase", "status": "blocked", "reason": "D+2 is finite cleanup boundary"},
        {"action": "accepted_or_v57f_replacement", "status": "blocked", "reason": "execution candidate only"},
        {"action": "modify_v57f_or_erc", "status": "blocked", "reason": "frozen/candidate governance"},
    ]
    next_gate = [
        {
            "gate": "v5d_execution_research_closeout",
            "decision": "ready",
            "reason": "L2/L3/L4 execution candidates have local engineering and governance outputs",
            "not_allowed": "accepted_strategy;live_trading;v57f_replacement",
        }
    ]
    write_csv(L4_DIR / "v5d_l4_cost_comparison.csv", cost_rows)
    write_csv(L4_DIR / "v5d_l4_candidate_cost_delta.csv", delta_rows)
    write_csv(L4_DIR / "v5d_l4_residual_unfilled_closeout.csv", residual_rows)
    write_csv(L4_DIR / "v5d_l4_cost_closeout_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(L4_DIR / "v5d_l4_cost_closeout_next_gate.csv", next_gate)
    write_csv(L4_DIR / "v5d_l4_cost_closeout_blockers.csv", [], ["blocker_id", "severity", "description"])
    summary = {
        "schema_version": 1,
        "project": "v5d_l4_cost_and_closeout",
        "status": "completed_l4_cost_closeout",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "source_pm_status": pm_summary.get("status"),
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "return_selection_used": False,
        "candidate_status": "l4_exception_governed_completion_execution_policy_candidate_not_accepted",
        "delta_rows": delta_rows,
        "blocker_count": 0,
        "next_gate": next_gate[0]["gate"],
        "outputs": {
            "summary": str(L4_DIR / "v5d_l4_cost_closeout_summary.json"),
            "report": str(L4_DIR / "v5d_l4_cost_closeout_report.md"),
            "cost_comparison": str(L4_DIR / "v5d_l4_cost_comparison.csv"),
            "candidate_cost_delta": str(L4_DIR / "v5d_l4_candidate_cost_delta.csv"),
            "residual_unfilled_closeout": str(L4_DIR / "v5d_l4_residual_unfilled_closeout.csv"),
            "next_gate": str(L4_DIR / "v5d_l4_cost_closeout_next_gate.csv"),
        },
    }
    (L4_DIR / "v5d_l4_cost_closeout_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (L4_DIR / "v5d_l4_cost_closeout_report.md").write_text(build_report(summary, delta_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
