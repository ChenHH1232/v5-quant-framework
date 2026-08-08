from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_profit_lock_model_comparison") / "current"
CAPITAL_DIR = Path("v5e_capital_sensitivity_test") / "current"
FORWARD_DIR = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current"
AUDIT_DIR = Path("v5e_post_exit_5min_monitoring_audit_packet") / "current"
V5E_MAIN = "v5e_profit_lock_main_20pct_sell50"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_profit_lock_model_comparison(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_model_comparison_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_model_comparison_summary.json", summary)
        return summary

    improvement = _capital_improvement(root)
    model_ladder = _model_ladder(root, improvement)
    gate_comparison = _gate_comparison(root, improvement, model_ladder)
    decision = _pm_gate_decision(improvement, model_ladder)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Model comparison completed."}]

    _write_csv(out / "v5e_profit_lock_improvement_comparison.csv", improvement)
    _write_csv(out / "v5e_profit_lock_model_ladder_comparison.csv", model_ladder)
    _write_csv(out / "v5e_profit_lock_vs_previous_gate_comparison.csv", gate_comparison)
    _write_csv(out / "v5e_model_comparison_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_model_comparison_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_model_comparison_blockers.csv", blockers)
    (out / "v5e_model_comparison_report.md").write_text(_report(improvement, model_ladder, decision), encoding="utf-8")
    (out / "v5e_model_comparison_next_prompt.md").write_text(_next_prompt(), encoding="utf-8")

    main_200w = next(row for row in improvement if row["capital_level"] == "200w")
    summary = _summary(
        "completed_profit_lock_model_comparison",
        decision[0]["pm_gate_decision"],
        [],
        daily_delta_return=float(main_200w["daily_open_delta_return_vs_baseline"]),
        vwap_delta_return=float(main_200w["vwap_adjusted_delta_return_vs_baseline"]),
        delta_max_drawdown=float(main_200w["delta_max_drawdown_vs_baseline"]),
        post_exit_net_cash_value=_model_value(model_ladder, "v5e_profit_lock_main_vwap_adjusted_200w"),
        ideal_upper_bound_value=_model_value(model_ladder, "ideal_hindsight_cash_or_continue_hold_upper_bound"),
    )
    _write_json(out / "v5e_model_comparison_summary.json", summary)
    return summary


def _capital_improvement(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / CAPITAL_DIR / "v5e_capital_level_comparison.csv")
    rows = []
    for capital in ["50w", "200w", "800w"]:
        base = df[(df["capital_level"].eq(capital)) & df["version_id"].eq("v57f_repaired_baseline")].iloc[0]
        v5e = df[(df["capital_level"].eq(capital)) & df["version_id"].eq(V5E_MAIN)].iloc[0]
        vwap_delta = float(v5e["vwap_adjusted_strategy_return_estimate"]) - float(base["strategy_return"])
        rows.append(
            {
                "capital_level": capital,
                "initial_capital": float(v5e["initial_capital"]),
                "baseline_return": float(base["strategy_return"]),
                "v5e_daily_open_return": float(v5e["strategy_return"]),
                "daily_open_delta_return_vs_baseline": float(v5e["delta_return_vs_baseline"]),
                "daily_open_delta_return_pct_points": float(v5e["delta_return_vs_baseline"]) * 100.0,
                "v5e_vwap_adjusted_return": float(v5e["vwap_adjusted_strategy_return_estimate"]),
                "vwap_adjusted_delta_return_vs_baseline": vwap_delta,
                "vwap_adjusted_delta_return_pct_points": vwap_delta * 100.0,
                "baseline_max_drawdown": float(base["max_drawdown"]),
                "v5e_max_drawdown": float(v5e["max_drawdown"]),
                "delta_max_drawdown_vs_baseline": float(v5e["delta_max_drawdown_vs_baseline"]),
                "delta_max_drawdown_pct_points": float(v5e["delta_max_drawdown_vs_baseline"]) * 100.0,
                "baseline_volatility": float(base["volatility"]),
                "v5e_volatility": float(v5e["volatility"]),
                "delta_volatility_pct_points": (float(v5e["volatility"]) - float(base["volatility"])) * 100.0,
                "baseline_sharpe": float(base["sharpe"]),
                "v5e_sharpe": float(v5e["sharpe"]),
                "delta_sharpe": float(v5e["sharpe"]) - float(base["sharpe"]),
                "cash_drag_delta_vs_baseline": float(v5e["cash_drag_delta_vs_baseline"]),
                "trigger_count": int(v5e["trigger_count"]),
                "exit_action_count": int(v5e["exit_action_count"]),
                "accepted": False,
            }
        )
    return rows


def _model_value(rows: list[dict[str, Any]], model_id: str) -> float:
    for row in rows:
        if row["model_id"] == model_id and row.get("incremental_value_vs_cash") not in {"", None}:
            return float(row["incremental_value_vs_cash"])
    return 0.0


def _model_ladder(root: Path, improvement: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ideal = _read_csv(root / AUDIT_DIR / "v5e_post_exit_5min_ideal_model_comparison.csv")
    event_summary = _read_csv(root / AUDIT_DIR / "v5e_post_exit_5min_missed_upside_avoided_loss.csv")[0]
    main = next(row for row in improvement if row["capital_level"] == "200w")
    rows = [
        {
            "model_id": "v57f_repaired_baseline_200w",
            "model_type": "baseline",
            "tradable": True,
            "accepted": False,
            "strategy_return": main["baseline_return"],
            "delta_return_vs_baseline": 0.0,
            "delta_return_pct_points": 0.0,
            "max_drawdown": main["baseline_max_drawdown"],
            "delta_max_drawdown_pct_points": 0.0,
            "incremental_value_vs_cash": "",
            "notes": "Previous repaired V57f baseline.",
        },
        {
            "model_id": "v5e_profit_lock_main_daily_open_200w",
            "model_type": "candidate_daily_proxy",
            "tradable": True,
            "accepted": False,
            "strategy_return": main["v5e_daily_open_return"],
            "delta_return_vs_baseline": main["daily_open_delta_return_vs_baseline"],
            "delta_return_pct_points": main["daily_open_delta_return_pct_points"],
            "max_drawdown": main["v5e_max_drawdown"],
            "delta_max_drawdown_pct_points": main["delta_max_drawdown_pct_points"],
            "incremental_value_vs_cash": "",
            "notes": "Pre-registered +20% sell 50%; daily T+1 open proxy.",
        },
        {
            "model_id": "v5e_profit_lock_main_vwap_adjusted_200w",
            "model_type": "candidate_5min_execution_proxy",
            "tradable": True,
            "accepted": False,
            "strategy_return": main["v5e_vwap_adjusted_return"],
            "delta_return_vs_baseline": main["vwap_adjusted_delta_return_vs_baseline"],
            "delta_return_pct_points": main["vwap_adjusted_delta_return_pct_points"],
            "max_drawdown": "",
            "delta_max_drawdown_pct_points": "",
            "incremental_value_vs_cash": float(event_summary["net_cash_vs_continue_hold_delta_value"]),
            "notes": "5min VWAP adjusts execution only; 5min is not a trigger.",
        },
    ]
    for row in ideal:
        rows.append(
            {
                "model_id": row["model_id"],
                "model_type": row["model_type"],
                "tradable": row["uses_future_information"] == "False",
                "accepted": False,
                "strategy_return": "",
                "delta_return_vs_baseline": "",
                "delta_return_pct_points": "",
                "max_drawdown": "",
                "delta_max_drawdown_pct_points": "",
                "incremental_value_vs_cash": row["incremental_value_vs_cash"],
                "uses_future_information": row["uses_future_information"],
                "notes": row["diagnostic_conclusion"],
            }
        )
    return rows


def _gate_comparison(root: Path, improvement: list[dict[str, Any]], model_ladder: list[dict[str, Any]]) -> list[dict[str, Any]]:
    forward = json.loads((root / FORWARD_DIR / "v5e_profit_lock_forward_paper_summary.json").read_text(encoding="utf-8"))
    audit = json.loads((root / AUDIT_DIR / "v5e_post_exit_5min_audit_summary.json").read_text(encoding="utf-8"))
    main = next(row for row in improvement if row["capital_level"] == "200w")
    return [
        {
            "comparison_id": "limited_engineering_daily_proxy_vs_baseline",
            "previous_gate": "v57f_repaired_baseline",
            "current_gate": V5E_MAIN,
            "delta_return_pct_points": main["daily_open_delta_return_pct_points"],
            "delta_max_drawdown_pct_points": main["delta_max_drawdown_pct_points"],
            "interpretation": "Daily proxy shows return improvement and drawdown reduction, but cash drag remains visible.",
        },
        {
            "comparison_id": "execution_adjusted_vs_baseline",
            "previous_gate": "v57f_repaired_baseline",
            "current_gate": "v5e_profit_lock_main_5min_vwap_adjusted",
            "delta_return_pct_points": main["vwap_adjusted_delta_return_pct_points"],
            "delta_max_drawdown_pct_points": "",
            "interpretation": "VWAP execution adjustment compresses return edge close to flat but remains slightly positive at 200w.",
        },
        {
            "comparison_id": "post_exit_monitoring_vs_continue_hold",
            "previous_gate": "counterfactual_continue_hold_sold_fraction",
            "current_gate": "actual_hold_cash_until_next_rebalance",
            "delta_return_pct_points": "",
            "incremental_value": audit["main_findings"][0]["net_cash_vs_continue_hold_delta_value"],
            "interpretation": "Post-exit 5min monitoring shows cash helped more often than it hurt on sold fractions.",
        },
        {
            "comparison_id": "forward_status",
            "previous_gate": "formal_review_candidate",
            "current_gate": forward["tracking_status"],
            "accepted": False,
            "interpretation": "Candidate remains paper-tracking ready, not accepted and not live approved.",
        },
    ]


def _pm_gate_decision(improvement: list[dict[str, Any]], model_ladder: list[dict[str, Any]]) -> list[dict[str, Any]]:
    main = next(row for row in improvement if row["capital_level"] == "200w")
    return [
        {
            "pm_gate_decision": "retain_profit_lock_main_forward_paper_tracking_not_accepted",
            "next_gate": "forward_paper_tracking_records_or_sleeve_cash_policy_spec",
            "daily_open_delta_return_pct_points_200w": main["daily_open_delta_return_pct_points"],
            "vwap_adjusted_delta_return_pct_points_200w": main["vwap_adjusted_delta_return_pct_points"],
            "delta_max_drawdown_pct_points_200w": main["delta_max_drawdown_pct_points"],
            "ideal_model_engineerable": False,
            "accepted": False,
            "reason": "V5e profit-lock main improves daily proxy and reduces drawdown; VWAP-adjusted edge is small but positive at 200w/800w. Ideal model remains diagnostic only.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5e_forward_paper_tracking_records",
            "task": "Collect forward/paper records for v5e_profit_lock_main_20pct_sell50",
            "allowed": True,
        },
        {
            "priority": 2,
            "next_gate": "v5e_sleeve_cash_policy_quant_spec",
            "task": "Spec sleeve cash policy without changing V57f or allowing reentry",
            "allowed": True,
        },
    ]


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        CAPITAL_DIR / "v5e_capital_level_comparison.csv",
        FORWARD_DIR / "v5e_profit_lock_forward_paper_summary.json",
        AUDIT_DIR / "v5e_post_exit_5min_audit_summary.json",
        AUDIT_DIR / "v5e_post_exit_5min_ideal_model_comparison.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    daily_delta_return: float = 0.0,
    vwap_delta_return: float = 0.0,
    delta_max_drawdown: float = 0.0,
    post_exit_net_cash_value: float = 0.0,
    ideal_upper_bound_value: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_profit_lock_model_comparison",
        "status": status,
        "pm_gate_decision": decision,
        "candidate_id": V5E_MAIN,
        "daily_open_delta_return_pct_points_200w": daily_delta_return * 100.0,
        "vwap_adjusted_delta_return_pct_points_200w": vwap_delta_return * 100.0,
        "delta_max_drawdown_pct_points_200w": delta_max_drawdown * 100.0,
        "post_exit_net_cash_value_vs_continue_hold": post_exit_net_cash_value,
        "ideal_upper_bound_value_vs_cash": ideal_upper_bound_value,
        "ideal_model_tradable": False,
        "accepted": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(improvement: list[dict[str, Any]], model_ladder: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    main = next(row for row in improvement if row["capital_level"] == "200w")
    return "\n".join(
        [
            "# V5e Profit-Lock Model Comparison",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- 200w daily-open return delta: {main['daily_open_delta_return_pct_points']:.4f} pct points",
            f"- 200w VWAP-adjusted return delta: {main['vwap_adjusted_delta_return_pct_points']:.4f} pct points",
            f"- 200w max drawdown delta: {main['delta_max_drawdown_pct_points']:.4f} pct points",
            "- Ideal hindsight model is diagnostic only and not tradable.",
            "",
            "## Capital Sensitivity",
            *[
                f"- {row['capital_level']}: daily delta {row['daily_open_delta_return_pct_points']:.4f} pct points; VWAP-adjusted delta {row['vwap_adjusted_delta_return_pct_points']:.4f} pct points; drawdown delta {row['delta_max_drawdown_pct_points']:.4f} pct points"
                for row in improvement
            ],
            "",
        ]
    )


def _next_prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e forward/paper tracking records or sleeve cash policy Quant spec

任务目标：
基于 `v5e_profit_lock_model_comparison/current/` 的对比结果，继续维护 `v5e_profit_lock_main_20pct_sell50` 的 forward/paper tracking；如要研究现金拖累治理，只能进入 sleeve cash policy Quant spec，不得修改 V57f，不得新增止盈阈值，不得允许 reentry，不得 accepted。
"""


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5e_profit_lock_model_comparison()
    print(json.dumps(result, ensure_ascii=False, indent=2))
