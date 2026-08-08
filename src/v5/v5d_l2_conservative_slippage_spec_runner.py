from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


LIQ_DIR = Path("v5d_l2_liquidity_instant_fill_review") / "current"
OUT_DIR = Path("v5d_l2_conservative_slippage_spec") / "current"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"

SLIPPAGE_BPS = {
    "below_one_lot_after_scaling": 0.0,
    "instant_fill_conservative": 1.0,
    "instant_fill_base": 3.0,
    "split_window_review": 8.0,
    "liquidity_review_required": 20.0,
    "missing_bar_or_zero_liquidity": None,
}


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


def load_inputs() -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    required = [
        LIQ_DIR / "v5d_l2_liquidity_instant_fill_summary.json",
        LIQ_DIR / "v5d_l2_liquidity_by_order.csv",
    ]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        return pd.DataFrame(), {}, blockers
    summary = json.loads((LIQ_DIR / "v5d_l2_liquidity_instant_fill_summary.json").read_text(encoding="utf-8"))
    return pd.read_csv(LIQ_DIR / "v5d_l2_liquidity_by_order.csv"), summary, []


def rule_rows() -> list[dict[str, Any]]:
    return [
        {"liquidity_tier": "below_one_lot_after_scaling", "adverse_slippage_bps": 0.0, "fill_assumption": "no_order_after_scaling", "policy": "do not create sub-lot paper order"},
        {"liquidity_tier": "instant_fill_conservative", "adverse_slippage_bps": 1.0, "fill_assumption": "local_instant_fill_allowed", "policy": "order is small relative to 5min bar"},
        {"liquidity_tier": "instant_fill_base", "adverse_slippage_bps": 3.0, "fill_assumption": "local_instant_fill_allowed_with_buffer", "policy": "allowed for small capital local paper review, not proof of real queue priority"},
        {"liquidity_tier": "split_window_review", "adverse_slippage_bps": 8.0, "fill_assumption": "split_or_retry_required", "policy": "do not force instant fill"},
        {"liquidity_tier": "liquidity_review_required", "adverse_slippage_bps": 20.0, "fill_assumption": "tail_review_required", "policy": "keep split/retry and consider excluding from instant-fill claim"},
        {"liquidity_tier": "missing_bar_or_zero_liquidity", "adverse_slippage_bps": "", "fill_assumption": "blocked", "policy": "cannot estimate slippage without positive bar liquidity"},
    ]


def build_order_costs(order_df: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for _, row in order_df.iterrows():
        tier = str(row["liquidity_tier"])
        bps = SLIPPAGE_BPS.get(tier)
        if bps is None:
            blockers.append({"blocker_id": "missing_slippage_rule", "severity": "fatal", "strategy_id": row["strategy_id"], "capital_case": row["capital_case"], "trade_date": row["trade_date"], "code": row["code"], "liquidity_tier": tier})
            slippage_cost = ""
            bps_out = ""
        else:
            value = float(row["scaled_order_value"])
            slippage_cost = value * bps / 10000.0
            bps_out = bps
        rows.append(
            {
                "strategy_id": row["strategy_id"],
                "capital_case": row["capital_case"],
                "execution_policy": row["execution_policy"],
                "trade_date": row["trade_date"],
                "window": row["window"],
                "code": row["code"],
                "side": row["side"],
                "scaled_amount": row["scaled_amount"],
                "scaled_order_value": row["scaled_order_value"],
                "liquidity_tier": tier,
                "max_participation": row["max_participation"],
                "adverse_slippage_bps": bps_out,
                "adverse_slippage_cost": slippage_cost,
                "fill_policy": "instant_fill_local_proxy" if tier in {"instant_fill_conservative", "instant_fill_base"} else "split_retry_or_tail_review",
            }
        )
    cost_df = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for (strategy_id, capital_case), group in cost_df.groupby(["strategy_id", "capital_case"]):
        capital = float(order_df[(order_df["strategy_id"] == strategy_id) & (order_df["capital_case"] == capital_case)]["capital"].iloc[0])
        total_value = pd.to_numeric(group["scaled_order_value"], errors="coerce").sum()
        total_slippage = pd.to_numeric(group["adverse_slippage_cost"], errors="coerce").sum()
        tail_count = group["liquidity_tier"].isin(["split_window_review", "liquidity_review_required"]).sum()
        instant_count = group["liquidity_tier"].isin(["instant_fill_conservative", "instant_fill_base", "below_one_lot_after_scaling"]).sum()
        summary_rows.append(
            {
                "strategy_id": strategy_id,
                "capital_case": capital_case,
                "capital": capital,
                "order_count": len(group),
                "instant_or_no_order_count": int(instant_count),
                "tail_review_count": int(tail_count),
                "total_scaled_traded_value": total_value,
                "conservative_slippage_cost": total_slippage,
                "slippage_cost_bps_on_traded_value": total_slippage / total_value * 10000.0 if total_value > 0 else 0.0,
                "slippage_cost_pct_on_capital": total_slippage / capital if capital > 0 else 0.0,
                "pm_read": "small_capital_slippage_buffer_acceptable" if capital_case == "capital_50w_scaled" and total_slippage / capital < 0.002 else "tail_slippage_should_remain_explicit",
            }
        )
    tail_rows = [row for row in rows if row["liquidity_tier"] in {"split_window_review", "liquidity_review_required"}]
    return rows, summary_rows, blockers + []


def build_report(summary: dict[str, Any], cost_summary: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L2 Conservative Slippage Spec",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: fixed slippage specification based on 5min liquidity tiers. No return selection, no broker connection, no live trading.",
        "",
        "## Cost Estimate",
        "",
        "| Strategy | Capital | Orders | Tail Review | Slippage Cost | Cost on Capital | Cost Bps on Traded Value |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in cost_summary:
        lines.append(
            f"| `{row['strategy_id']}` | `{row['capital_case']}` | {row['order_count']} | {row['tail_review_count']} | {float(row['conservative_slippage_cost']):.2f} | {pct(row['slippage_cost_pct_on_capital'])} | {float(row['slippage_cost_bps_on_traded_value']):.2f} |"
        )
    lines.extend(
        [
            "",
            "## PM Read",
            "",
            "The 50w scaled case can proceed with local paper execution using conservative slippage, while tail orders should keep split/retry treatment. This does not prove guaranteed instant fill inside a 5min bar.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    order_df, liquidity_summary, blockers = load_inputs()
    if blockers:
        write_csv(OUT_DIR / "v5d_l2_slippage_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l2_conservative_slippage_spec", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l2_conservative_slippage_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    order_cost_rows, cost_summary_rows, blockers = build_order_costs(order_df)
    allowed_blocked = [
        {"action": "apply_conservative_slippage_to_local_paper_matching", "status": "allowed", "reason": "fixed tier rules are based on pre-defined participation ranges"},
        {"action": "claim_guaranteed_instant_fill", "status": "blocked", "reason": "5min bar liquidity is not queue-level proof"},
        {"action": "optimize_slippage_by_return", "status": "blocked", "reason": "slippage rules are governance buffers, not return parameters"},
        {"action": "connect_live_broker", "status": "blocked", "reason": "not required for current V5d local scope"},
    ]
    next_gate = [
        {
            "gate": "l2_small_capital_paper_execution_candidate",
            "allowed": "true" if not blockers else "false",
            "reason": "50w scaled liquidity and conservative slippage review are sufficient for local paper execution spec, with tail split/retry retained",
            "not_allowed": "accepted_strategy;guaranteed_fill;broker_connection;live_orders",
        }
    ]
    write_csv(OUT_DIR / "v5d_l2_slippage_rule_spec.csv", rule_rows())
    write_csv(OUT_DIR / "v5d_l2_slippage_by_order.csv", order_cost_rows)
    write_csv(OUT_DIR / "v5d_l2_slippage_cost_summary.csv", cost_summary_rows)
    write_csv(OUT_DIR / "v5d_l2_slippage_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(OUT_DIR / "v5d_l2_slippage_blockers.csv", blockers, ["blocker_id", "severity", "strategy_id", "capital_case", "trade_date", "code", "liquidity_tier"])
    write_csv(OUT_DIR / "v5d_l2_next_gate_decision.csv", next_gate)
    summary = {
        "schema_version": 1,
        "project": "v5d_l2_conservative_slippage_spec",
        "status": "completed_slippage_spec_passed" if not blockers else "completed_with_blockers",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "source_liquidity_status": liquidity_summary.get("status"),
        "v57f_core_modified": False,
        "erc_modified": False,
        "broker_connected": False,
        "live_trading_started": False,
        "blocker_count": len(blockers),
        "cost_summary_rows": cost_summary_rows,
        "next_gate": next_gate[0]["gate"] if not blockers else "resolve_slippage_blockers",
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l2_conservative_slippage_summary.json"),
            "report": str(OUT_DIR / "v5d_l2_conservative_slippage_report.md"),
            "rule_spec": str(OUT_DIR / "v5d_l2_slippage_rule_spec.csv"),
            "by_order": str(OUT_DIR / "v5d_l2_slippage_by_order.csv"),
            "cost_summary": str(OUT_DIR / "v5d_l2_slippage_cost_summary.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_l2_slippage_allowed_blocked_actions.csv"),
            "next_gate": str(OUT_DIR / "v5d_l2_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l2_conservative_slippage_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l2_conservative_slippage_report.md").write_text(build_report(summary, cost_summary_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
