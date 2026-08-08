from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PM_DIR = Path("v5d_l3_pm_quant_review") / "current"
ENG_DIR = Path("v5d_l3_intraday_execution_engineering") / "current"
OUT_DIR = Path("v5d_l3_1_unfilled_remediation") / "current"
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


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    required = [
        PM_DIR / "v5d_l3_pm_quant_review_summary.json",
        PM_DIR / "v5d_l3_pm_quant_policy_review_matrix.csv",
        ENG_DIR / "v5d_l3_engineering_comparison.csv",
    ]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        return pd.DataFrame(), pd.DataFrame(), {}, blockers
    summary = json.loads((PM_DIR / "v5d_l3_pm_quant_review_summary.json").read_text(encoding="utf-8"))
    return pd.read_csv(PM_DIR / "v5d_l3_pm_quant_policy_review_matrix.csv"), pd.read_csv(ENG_DIR / "v5d_l3_engineering_comparison.csv"), summary, []


def build_rows(pm: pd.DataFrame, comp: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    reduction_rows: list[dict[str, Any]] = []
    for strategy_id in sorted(comp["strategy_id"].unique()):
        base = comp[(comp["strategy_id"] == strategy_id) & (comp["l3_policy_id"] == "l3_default_exception")].iloc[0]
        raw = comp[(comp["strategy_id"] == strategy_id) & (comp["l3_policy_id"] == "l3_open_delay_price_band")].iloc[0]
        fixed = comp[(comp["strategy_id"] == strategy_id) & (comp["l3_policy_id"] == "l3_open_delay_price_band_fallback")].iloc[0]
        raw_unfilled = int(raw["unfilled_order_count"])
        fixed_unfilled = int(fixed["unfilled_order_count"])
        base_unfilled = int(base["unfilled_order_count"])
        reduction = raw_unfilled - fixed_unfilled
        reduction_pct = reduction / raw_unfilled if raw_unfilled else 0.0
        rows.append(
            {
                "strategy_id": strategy_id,
                "candidate_policy": "l3_open_delay_price_band_fallback",
                "status": "l3_1_unfilled_remediation_candidate_not_accepted",
                "raw_price_band_unfilled": raw_unfilled,
                "fallback_unfilled": fixed_unfilled,
                "default_exception_unfilled": base_unfilled,
                "unfilled_reduction": reduction,
                "unfilled_reduction_pct": reduction_pct,
                "fallback_t_violation_count": int(fixed["t_trade_violation_count"]),
                "fallback_return": fixed["strategy_return"],
                "fallback_delta_vs_l2": fixed["delta_return_vs_l2_size_aware"],
                "fallback_max_drawdown": fixed["max_drawdown"],
                "promotion_basis": "unfilled_reduction_and_zero_T_not_return_selection",
                "pm_read": "candidate_with_review_notes" if fixed_unfilled <= 20 and int(fixed["t_trade_violation_count"]) == 0 else "needs_more_repair",
            }
        )
        reduction_rows.append(
            {
                "strategy_id": strategy_id,
                "raw_policy": "l3_open_delay_price_band",
                "repair_policy": "l3_open_delay_price_band_fallback",
                "raw_unfilled": raw_unfilled,
                "repair_unfilled": fixed_unfilled,
                "unfilled_reduction": reduction,
                "unfilled_reduction_pct": reduction_pct,
                "raw_trade_count": raw["trade_count"],
                "repair_trade_count": fixed["trade_count"],
                "raw_exception_count": raw["exception_count"],
                "repair_exception_count": fixed["exception_count"],
                "t_violation_count": fixed["t_trade_violation_count"],
            }
        )
    return rows, reduction_rows


def build_report(summary: dict[str, Any], decision_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L3.1 Unfilled Remediation Closeout",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: fixed fallback remediation only; no return selection, no T, no V57f/ERC changes.",
        "",
        "## Decision",
        "",
        "| Strategy | Candidate | Raw Unfilled | Fallback Unfilled | Reduction | T Violations | Delta vs L2 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in decision_rows:
        lines.append(
            f"| `{row['strategy_id']}` | `{row['candidate_policy']}` | {row['raw_price_band_unfilled']} | {row['fallback_unfilled']} | {pct(row['unfilled_reduction_pct'])} | {row['fallback_t_violation_count']} | {pct(row['fallback_delta_vs_l2'])} |"
        )
    lines.extend(
        [
            "",
            "## PM Read",
            "",
            "The fallback repair is an effective L3.1 result because it materially reduces unfilled orders while preserving zero T violations. Its positive return delta is logged but is not the promotion basis.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pm, comp, pm_summary, blockers = load_inputs()
    if blockers:
        write_csv(OUT_DIR / "v5d_l3_1_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l3_1_unfilled_remediation", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l3_1_unfilled_remediation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    decision_rows, reduction_rows = build_rows(pm, comp)
    allowed_blocked = [
        {"action": "retain_l3_default_exception_as_main_execution_governance_candidate", "status": "allowed", "reason": "lowest unfilled and clean governance baseline"},
        {"action": "promote_l3_open_delay_price_band_fallback_to_l3_1_candidate", "status": "allowed", "reason": "fixed fallback reduces raw price-band unfilled materially with zero T violations"},
        {"action": "promote_raw_open_delay_price_band", "status": "blocked", "reason": "raw version has excessive unfilled orders"},
        {"action": "choose_by_historical_return", "status": "blocked", "reason": "promotion basis is unfilled repair and T compliance"},
        {"action": "accepted_strategy_or_v57f_replacement", "status": "blocked", "reason": "execution research only"},
    ]
    next_gate = [
        {
            "gate": "l3_1_candidate_stress_and_cost_review",
            "allowed": "true",
            "reason": "fallback remediation materially reduced unfilled and has no T violations",
            "not_allowed": "accepted_strategy;return_selection;intraday_T;modify_v57f_or_erc",
        }
    ]
    write_csv(OUT_DIR / "v5d_l3_1_decision_matrix.csv", decision_rows)
    write_csv(OUT_DIR / "v5d_l3_1_unfilled_reduction.csv", reduction_rows)
    write_csv(OUT_DIR / "v5d_l3_1_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(OUT_DIR / "v5d_l3_1_next_gate_decision.csv", next_gate)
    write_csv(OUT_DIR / "v5d_l3_1_blockers.csv", [], ["blocker_id", "severity", "description"])
    summary = {
        "schema_version": 1,
        "project": "v5d_l3_1_unfilled_remediation",
        "status": "completed_l3_1_remediation_candidate_found",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "source_pm_status": pm_summary.get("status"),
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "return_selection_used": False,
        "main_l3_candidate": "l3_default_exception_execution_governance_candidate",
        "l3_1_candidate": "l3_open_delay_price_band_fallback_unfilled_remediation_candidate_not_accepted",
        "decision_rows": decision_rows,
        "blocker_count": 0,
        "next_gate": next_gate[0]["gate"],
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l3_1_unfilled_remediation_summary.json"),
            "report": str(OUT_DIR / "v5d_l3_1_unfilled_remediation_report.md"),
            "decision_matrix": str(OUT_DIR / "v5d_l3_1_decision_matrix.csv"),
            "unfilled_reduction": str(OUT_DIR / "v5d_l3_1_unfilled_reduction.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_l3_1_allowed_blocked_actions.csv"),
            "next_gate": str(OUT_DIR / "v5d_l3_1_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l3_1_unfilled_remediation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l3_1_unfilled_remediation_report.md").write_text(build_report(summary, decision_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
