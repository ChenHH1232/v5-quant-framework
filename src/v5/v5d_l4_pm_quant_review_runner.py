from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


IN_DIR = Path("v5d_l4_rebalance_neighborhood_order_completion") / "current"
OUT_DIR = IN_DIR
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


def run() -> dict[str, Any]:
    required = [
        IN_DIR / "v5d_l4_order_completion_summary.json",
        IN_DIR / "v5d_l4_engineering_comparison.csv",
        IN_DIR / "v5d_l4_candidate_gate_decision.csv",
        IN_DIR / "v5d_l4_unfilled_reason_summary.csv",
    ]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        write_csv(IN_DIR / "v5d_l4_pm_quant_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        return {"status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}

    engineering_summary = json.loads((IN_DIR / "v5d_l4_order_completion_summary.json").read_text(encoding="utf-8"))
    comparison = pd.read_csv(IN_DIR / "v5d_l4_engineering_comparison.csv")
    gate = pd.read_csv(IN_DIR / "v5d_l4_candidate_gate_decision.csv")
    rows: list[dict[str, Any]] = []
    for strategy_id in sorted(comparison["strategy_id"].unique()):
        base = comparison[(comparison["strategy_id"] == strategy_id) & (comparison["version_id"] == "baseline_l2_size_aware")].iloc[0]
        d1 = comparison[(comparison["strategy_id"] == strategy_id) & (comparison["version_id"] == "l4_d0_d1_completion")].iloc[0]
        d2 = comparison[(comparison["strategy_id"] == strategy_id) & (comparison["version_id"] == "l4_d0_d1_d2_final_cleanup")].iloc[0]
        candidate = comparison[(comparison["strategy_id"] == strategy_id) & (comparison["version_id"] == "l4_exception_governed_completion")].iloc[0]
        rows.append(
            {
                "strategy_id": strategy_id,
                "baseline_unfilled": int(base["unfilled_order_count"]),
                "d1_unfilled": int(d1["unfilled_order_count"]),
                "d2_unfilled": int(d2["unfilled_order_count"]),
                "candidate_unfilled": int(candidate["unfilled_order_count"]),
                "unfilled_reduction_vs_baseline": int(base["unfilled_order_count"]) - int(candidate["unfilled_order_count"]),
                "baseline_return": base["strategy_return"],
                "candidate_return": candidate["strategy_return"],
                "candidate_delta_return_vs_l2": candidate["delta_return_vs_l2_size_aware"],
                "candidate_max_drawdown": candidate["max_drawdown"],
                "candidate_t_violation_count": int(candidate["t_violation_count"]),
                "pm_quant_decision": "promote_to_l4_execution_policy_candidate_not_accepted" if int(candidate["unfilled_order_count"]) < int(base["unfilled_order_count"]) and int(candidate["t_violation_count"]) == 0 else "diagnostic_only",
                "decision_basis": "unfilled_reduction_and_zero_T_not_return_selection",
                "review_note": "D+2 added no incremental fill versus D+1 in this window" if int(d2["unfilled_order_count"]) == int(d1["unfilled_order_count"]) else "D+2 added incremental completion",
            }
        )
    allowed_blocked = [
        {"action": "promote_l4_exception_governed_completion_to_candidate", "status": "allowed", "reason": "unfilled count improves and T violations are zero"},
        {"action": "promote_by_historical_return", "status": "blocked", "reason": "L4 is order completion governance, not return optimization"},
        {"action": "infinite_chase_after_D2", "status": "blocked", "reason": "finite D0/D1/D2 completion only"},
        {"action": "D_minus_1_pretrade", "status": "blocked", "reason": "rebalance target not proven PIT-visible on D-1"},
        {"action": "intraday_T", "status": "blocked", "reason": "hard governance block"},
        {"action": "modify_v57f_or_erc", "status": "blocked", "reason": "frozen/candidate governance"},
    ]
    next_gate = [
        {
            "gate": "l4_execution_policy_candidate_cost_and_closeout",
            "decision": "promote_candidate_not_accepted",
            "allowed_next_action": "cost/slippage review or V5d closeout",
            "blocked_actions": "accepted_strategy;v57f_replacement;return_selection;intraday_T;infinite_chase",
        }
    ]
    write_csv(IN_DIR / "v5d_l4_pm_quant_review_matrix.csv", rows)
    write_csv(IN_DIR / "v5d_l4_pm_quant_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(IN_DIR / "v5d_l4_pm_quant_next_gate.csv", next_gate)
    write_csv(IN_DIR / "v5d_l4_pm_quant_blockers.csv", [], ["blocker_id", "severity", "description"])
    summary = {
        "schema_version": 1,
        "project": "v5d_l4_pm_quant_review",
        "status": "completed_l4_pm_quant_review",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "engineering_status": engineering_summary.get("status"),
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "return_selection_used": False,
        "policy_decision": "l4_exception_governed_completion_promote_to_execution_policy_candidate_not_accepted",
        "review_rows": rows,
        "blocker_count": 0,
        "next_gate": next_gate[0]["gate"],
    }
    (IN_DIR / "v5d_l4_pm_quant_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# V5d L4 PM/Quant Review",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Review basis: unfilled reduction, zero T violations, PIT-safe fixed D0/D1/D2 completion. Return is logged but not used for promotion.",
        "",
        "| Strategy | Baseline Unfilled | Candidate Unfilled | Reduction | Candidate Return | Delta vs L2 | T Violations |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row['strategy_id']}` | {row['baseline_unfilled']} | {row['candidate_unfilled']} | {row['unfilled_reduction_vs_baseline']} | {pct(row['candidate_return'])} | {pct(row['candidate_delta_return_vs_l2'])} | {row['candidate_t_violation_count']} |")
    lines.extend(["", "## PM Read", "", "L4 exception-governed completion is a valid execution policy candidate because it reduces residual unfilled orders with zero T violations. D+2 did not add incremental fills in this sample, so D+1 is the practical completion window, while D+2 remains a finite cleanup boundary."])
    (IN_DIR / "v5d_l4_pm_quant_review_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
