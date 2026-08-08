from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_post_exit_5min_monitoring_audit_packet") / "current"
DATA_GATE_DIR = Path("v5e_post_exit_5min_monitoring_data_gate") / "current"
EXIT_LOG = Path("v5e_limited_engineering_loop") / "current" / "v5e_exit_action_log.csv"
CASH_ROBUST_DIR = Path("v5e_cash_drag_robustness_packet") / "current"
V5E_MAIN = "v5e_profit_lock_main_20pct_sell50"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_post_exit_5min_monitoring_audit(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_post_exit_5min_audit_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_post_exit_5min_audit_summary.json", summary)
        return summary

    exit_events = _exit_events(root)
    event_returns = _event_returns(root, exit_events)
    missing_reasons = _missing_reasons(root)
    event_summary = _impact_summary(event_returns)
    by_year = _group_summary(event_returns, "execution_year")
    by_sleeve = _group_summary(event_returns, "sleeve")
    by_stock = _group_summary(event_returns, "code")
    top_events = sorted(
        event_returns,
        key=lambda row: abs(float(row["cash_vs_continue_hold_delta_value"] or 0.0)),
        reverse=True,
    )[:25]
    ideal_comparison = _ideal_model_comparison(event_returns)
    decision = _pm_gate_decision(event_summary, ideal_comparison, missing_reasons)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers = _audit_blockers(missing_reasons)

    _write_csv(out / "v5e_post_exit_5min_event_returns.csv", event_returns)
    _write_csv(out / "v5e_post_exit_5min_missed_upside_avoided_loss.csv", event_summary)
    _write_csv(out / "v5e_post_exit_5min_impact_by_year.csv", by_year)
    _write_csv(out / "v5e_post_exit_5min_impact_by_sleeve.csv", by_sleeve)
    _write_csv(out / "v5e_post_exit_5min_impact_by_stock.csv", by_stock)
    _write_csv(out / "v5e_post_exit_5min_top_impact_events.csv", top_events)
    _write_csv(out / "v5e_post_exit_5min_missing_data_reason.csv", missing_reasons)
    _write_csv(out / "v5e_post_exit_5min_ideal_model_comparison.csv", ideal_comparison)
    _write_csv(out / "v5e_post_exit_5min_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_post_exit_5min_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_post_exit_5min_audit_blockers.csv", blockers)
    (out / "v5e_post_exit_5min_next_prompt.md").write_text(_next_prompt(), encoding="utf-8")
    (out / "v5e_post_exit_5min_audit_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_post_exit_5min_monitoring_audit",
        decision[0]["pm_gate_decision"],
        [],
        event_count=len(event_returns),
        ideal_model_count=len(ideal_comparison),
        missing_stock_dates=len(missing_reasons),
        coverage_rate_pct=_data_gate_summary(root).get("coverage_rate_pct", 0.0),
        main_findings=event_summary,
    )
    _write_json(out / "v5e_post_exit_5min_audit_summary.json", summary)
    (out / "v5e_post_exit_5min_audit_report.md").write_text(_report(summary, decision, event_summary, ideal_comparison), encoding="utf-8")
    return summary


def _exit_events(root: Path) -> list[dict[str, Any]]:
    exits = pd.read_csv(root / EXIT_LOG)
    exits = exits[exits["version_id"].eq(V5E_MAIN)].reset_index(drop=True)
    sleeve_lookup = _sleeve_lookup(root)
    rows: list[dict[str, Any]] = []
    for idx, row in exits.iterrows():
        key = (str(row["execution_date"]), str(row["code"]))
        rows.append(
            {
                "exit_action_id": f"{row['trigger_date']}|{row['execution_date']}|{row['code']}|{idx + 1}",
                "version_id": str(row["version_id"]),
                "execution_date": str(row["execution_date"]),
                "trigger_date": str(row["trigger_date"]),
                "code": str(row["code"]),
                "sleeve": sleeve_lookup.get(key, ""),
                "trigger_reason": str(row.get("trigger_reason", "")),
                "exit_value": float(row.get("value", 0.0)),
                "exit_price": float(row.get("price", 0.0)),
                "amount": float(row.get("amount", 0.0)),
            }
        )
    return rows


def _event_returns(root: Path, exit_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    req = pd.read_csv(root / DATA_GATE_DIR / "v5e_post_exit_5min_requirement.csv")
    cov = pd.read_csv(root / DATA_GATE_DIR / "v5e_post_exit_5min_coverage_audit.csv")
    metrics = pd.read_csv(root / DATA_GATE_DIR / "v5e_post_exit_5min_monitoring_metrics.csv")
    daily = _daily_until_next_rebalance(root)
    req_cov = req.merge(cov[["monitoring_id", "coverage_status"]], on="monitoring_id", how="left")
    metric_by_id = {str(row["monitoring_id"]): row for _, row in metrics.iterrows()}
    rows: list[dict[str, Any]] = []
    for event in exit_events:
        event_req = req_cov[req_cov["source_exit_action_ids"].astype(str).str.contains(event["exit_action_id"], regex=False, na=False)].copy()
        event_req = event_req[event_req["trade_date"].astype(str) >= event["execution_date"]]
        available_ids = [str(v) for v in event_req.loc[event_req["coverage_status"].eq("available"), "monitoring_id"].tolist()]
        metric_rows = [metric_by_id[mid] for mid in available_ids if mid in metric_by_id]
        metric_rows = sorted(metric_rows, key=lambda r: str(r["trade_date"]))
        missing_count = int(len(event_req) - len(metric_rows))
        return_5min = ""
        last_close = ""
        max_intraday_return = ""
        min_intraday_return = ""
        if metric_rows and event["exit_price"] > 0:
            last_close = float(metric_rows[-1]["last_close"])
            highs = [float(r["intraday_high"]) for r in metric_rows if pd.notna(r["intraday_high"])]
            lows = [float(r["intraday_low"]) for r in metric_rows if pd.notna(r["intraday_low"])]
            return_5min = last_close / event["exit_price"] - 1.0
            max_intraday_return = max(highs) / event["exit_price"] - 1.0 if highs else ""
            min_intraday_return = min(lows) / event["exit_price"] - 1.0 if lows else ""
        daily_return = daily.get((event["execution_date"], event["code"]), {}).get("stock_return_until_next_rebalance", "")
        selected_return = return_5min if return_5min != "" else daily_return
        selected_return = float(selected_return) if selected_return != "" and pd.notna(selected_return) else 0.0
        missed = max(selected_return, 0.0) * event["exit_value"]
        avoided = max(-selected_return, 0.0) * event["exit_value"]
        rows.append(
            {
                **event,
                "next_rebalance_date": daily.get((event["execution_date"], event["code"]), {}).get("next_rebalance_date", _next_rebalance_from_req(event_req)),
                "execution_year": event["execution_date"][:4],
                "required_stock_dates": int(len(event_req)),
                "available_stock_dates": int(len(metric_rows)),
                "missing_stock_dates": missing_count,
                "coverage_rate": (len(metric_rows) / len(event_req)) if len(event_req) else 0.0,
                "last_5min_close_before_rebalance": last_close,
                "post_exit_return_5min_vs_exit_price": return_5min,
                "post_exit_return_daily_until_next_rebalance": daily_return,
                "selected_post_exit_return": selected_return,
                "max_intraday_return_vs_exit_price": max_intraday_return,
                "min_intraday_return_vs_exit_price": min_intraday_return,
                "missed_upside_value": missed,
                "avoided_loss_value": avoided,
                "cash_vs_continue_hold_delta_value": -selected_return * event["exit_value"],
                "cash_policy_helped": selected_return < 0,
                "cash_policy_hurt": selected_return > 0,
                "ideal_hindsight_action": "continue_hold_sold_fraction" if selected_return > 0 else "hold_cash",
                "ideal_hindsight_extra_value_vs_cash": missed,
                "monitoring_only": True,
                "trade_trigger_allowed": False,
            }
        )
    return rows


def _impact_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_value = sum(float(row["exit_value"]) for row in rows)
    missed = sum(float(row["missed_upside_value"]) for row in rows)
    avoided = sum(float(row["avoided_loss_value"]) for row in rows)
    delta = sum(float(row["cash_vs_continue_hold_delta_value"]) for row in rows)
    hurt_count = sum(1 for row in rows if row["cash_policy_hurt"])
    helped_count = sum(1 for row in rows if row["cash_policy_helped"])
    return [
        {
            "version_id": V5E_MAIN,
            "event_count": len(rows),
            "total_exit_value": total_value,
            "cash_policy_helped_event_count": helped_count,
            "cash_policy_hurt_event_count": hurt_count,
            "missed_upside_value": missed,
            "avoided_loss_value": avoided,
            "net_cash_vs_continue_hold_delta_value": delta,
            "missed_upside_pct_of_exit_value": missed / total_value if total_value else 0.0,
            "avoided_loss_pct_of_exit_value": avoided / total_value if total_value else 0.0,
            "net_cash_vs_continue_hold_pct_of_exit_value": delta / total_value if total_value else 0.0,
            "dominant_effect": "missed_upside" if missed > avoided else "avoided_loss",
            "monitoring_only": True,
            "ideal_model_tradable": False,
        }
    ]


def _group_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get(key, "")), []).append(row)
    output = []
    for group, items in sorted(grouped.items()):
        total_value = sum(float(row["exit_value"]) for row in items)
        missed = sum(float(row["missed_upside_value"]) for row in items)
        avoided = sum(float(row["avoided_loss_value"]) for row in items)
        output.append(
            {
                key: group,
                "event_count": len(items),
                "total_exit_value": total_value,
                "missed_upside_value": missed,
                "avoided_loss_value": avoided,
                "net_cash_vs_continue_hold_delta_value": avoided - missed,
                "missed_upside_pct_of_exit_value": missed / total_value if total_value else 0.0,
                "avoided_loss_pct_of_exit_value": avoided / total_value if total_value else 0.0,
                "dominant_effect": "missed_upside" if missed > avoided else "avoided_loss",
            }
        )
    return output


def _ideal_model_comparison(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_value = sum(float(row["exit_value"]) for row in rows)
    hold_pnl = sum(float(row["selected_post_exit_return"]) * float(row["exit_value"]) for row in rows)
    ideal_pnl = sum(max(float(row["selected_post_exit_return"]), 0.0) * float(row["exit_value"]) for row in rows)
    avoided = sum(max(-float(row["selected_post_exit_return"]), 0.0) * float(row["exit_value"]) for row in rows)
    return [
        {
            "model_id": "actual_v5e_hold_cash_until_next_rebalance",
            "model_type": "implemented_policy_candidate_not_accepted",
            "uses_future_information": False,
            "uses_5min_trigger": False,
            "trade_trigger_allowed": False,
            "pnl_on_sold_fraction_until_next_rebalance": 0.0,
            "incremental_value_vs_cash": 0.0,
            "incremental_pct_of_exit_value_vs_cash": 0.0,
            "diagnostic_conclusion": "Clean governance but exposes cash-drag opportunity cost.",
        },
        {
            "model_id": "counterfactual_continue_hold_sold_fraction",
            "model_type": "counterfactual_diagnostic",
            "uses_future_information": False,
            "uses_5min_trigger": False,
            "trade_trigger_allowed": False,
            "pnl_on_sold_fraction_until_next_rebalance": hold_pnl,
            "incremental_value_vs_cash": hold_pnl,
            "incremental_pct_of_exit_value_vs_cash": hold_pnl / total_value if total_value else 0.0,
            "diagnostic_conclusion": "Measures whether cash policy missed upside or avoided losses after exits.",
        },
        {
            "model_id": "ideal_hindsight_cash_or_continue_hold_upper_bound",
            "model_type": "oracle_upper_bound_not_tradable",
            "uses_future_information": True,
            "uses_5min_trigger": False,
            "trade_trigger_allowed": False,
            "pnl_on_sold_fraction_until_next_rebalance": ideal_pnl,
            "incremental_value_vs_cash": ideal_pnl,
            "incremental_pct_of_exit_value_vs_cash": ideal_pnl / total_value if total_value else 0.0,
            "avoided_loss_value_if_cash_kept_for_losers": avoided,
            "diagnostic_conclusion": "Upper bound only; cannot be accepted or engineered as a strategy because it chooses with future outcomes.",
        },
    ]


def _pm_gate_decision(
    event_summary: list[dict[str, Any]],
    ideal_comparison: list[dict[str, Any]],
    missing_reasons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summary = event_summary[0]
    if summary["dominant_effect"] == "missed_upside":
        decision = "open_sleeve_cash_policy_quant_spec_and_keep_profit_lock_forward_tracking"
        next_gate = "v5e_sleeve_cash_policy_quant_spec"
    else:
        decision = "retain_profit_lock_cash_policy_with_forward_monitoring"
        next_gate = "v5e_forward_paper_tracking"
    return [
        {
            "pm_gate_decision": decision,
            "next_gate": next_gate,
            "accepted": False,
            "ideal_model_accepted": False,
            "full_holding_period_5min_trigger_allowed": False,
            "trade_trigger_allowed": False,
            "threshold_scan_used": False,
            "v57f_core_modified": False,
            "missing_stock_dates": len(missing_reasons),
            "reason": "Post-exit monitoring is diagnostic only. The ideal hindsight model is an upper bound and uses future outcomes, so it cannot become a tradable V5e rule.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5e_sleeve_cash_policy_quant_spec",
            "task": "Specify sleeve cash bucket / sleeve-level cash policy using pre-registered boundaries",
            "allowed": decision.startswith("open_sleeve_cash_policy"),
        },
        {
            "priority": 2,
            "next_gate": "v5e_profit_lock_forward_paper_tracking",
            "task": "Keep profit-lock main as forward/paper tracking candidate, not accepted",
            "allowed": True,
        },
        {
            "priority": 3,
            "next_gate": "do_not_engineer_ideal_hindsight_model",
            "task": "Archive ideal hindsight comparison as diagnostic upper bound only",
            "allowed": True,
        },
    ]


def _missing_reasons(root: Path) -> list[dict[str, Any]]:
    path = root / DATA_GATE_DIR / "v5e_post_exit_5min_missing_daily_crosscheck.csv"
    if path.exists() and path.stat().st_size > 3:
        rows = _read_csv(path)
        for row in rows:
            row["minute_missing_reason"] = "paused_zero_volume_no_intraday_bars" if str(row.get("paused", "")) in {"1", "1.0"} else "baostock_empty_response_review_required"
            row["can_fill_with_5min"] = False
            row["can_use_daily_to_fabricate_5min"] = False
        return rows
    return _read_csv(root / DATA_GATE_DIR / "v5e_post_exit_5min_missing_windows.csv")


def _audit_blockers(missing_reasons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not missing_reasons:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "No missing medium post-exit 5min windows."}]
    return [
        {
            "blocker_id": "paused_zero_volume_5min_windows_unavailable",
            "severity": "data_quality",
            "status": "not_fatal_for_monitoring_audit",
            "count": len(missing_reasons),
            "description": "Remaining missing 5min windows correspond to local daily paused=1, volume=0, money=0 rows. Do not fabricate 5min bars.",
        }
    ]


def _sleeve_lookup(root: Path) -> dict[tuple[str, str], str]:
    path = root / CASH_ROBUST_DIR / "v5e_exit_until_next_rebalance_return.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    df = df[df["version_id"].eq(V5E_MAIN)]
    return {(str(row["execution_date"]), str(row["code"])): str(row.get("sleeve", "")) for _, row in df.iterrows()}


def _daily_until_next_rebalance(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    path = root / CASH_ROBUST_DIR / "v5e_exit_until_next_rebalance_return.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    df = df[df["version_id"].eq(V5E_MAIN)]
    return {(str(row["execution_date"]), str(row["code"])): row.to_dict() for _, row in df.iterrows()}


def _next_rebalance_from_req(event_req: pd.DataFrame) -> str:
    if event_req.empty or "next_rebalance_date" not in event_req.columns:
        return ""
    values = event_req["next_rebalance_date"].dropna().astype(str).unique().tolist()
    return values[0] if values else ""


def _data_gate_summary(root: Path) -> dict[str, Any]:
    path = root / DATA_GATE_DIR / "v5e_post_exit_5min_monitoring_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        DATA_GATE_DIR / "v5e_post_exit_5min_monitoring_summary.json",
        DATA_GATE_DIR / "v5e_post_exit_5min_requirement.csv",
        DATA_GATE_DIR / "v5e_post_exit_5min_coverage_audit.csv",
        DATA_GATE_DIR / "v5e_post_exit_5min_monitoring_metrics.csv",
        EXIT_LOG,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
        }
        for path in required
        if not (root / path).exists()
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    event_count: int = 0,
    ideal_model_count: int = 0,
    missing_stock_dates: int = 0,
    coverage_rate_pct: float = 0.0,
    main_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    main_findings = main_findings or []
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_post_exit_5min_monitoring_audit_packet",
        "status": status,
        "pm_gate_decision": decision,
        "scope": "medium_post_exit_to_next_rebalance",
        "event_count": event_count,
        "ideal_model_count": ideal_model_count,
        "missing_stock_dates": missing_stock_dates,
        "coverage_rate_pct": coverage_rate_pct,
        "monitoring_only": True,
        "trade_trigger_allowed": False,
        "minute_data_used_for_trigger": False,
        "full_holding_period_fetch": False,
        "full_holding_period_5min_trigger_allowed": False,
        "ideal_model_tradable": False,
        "accepted": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
        "main_findings": main_findings,
    }


def _report(
    summary: dict[str, Any],
    decision: list[dict[str, Any]],
    event_summary: list[dict[str, Any]],
    ideal_comparison: list[dict[str, Any]],
) -> str:
    finding = event_summary[0] if event_summary else {}
    return "\n".join(
        [
            "# V5e Post-Exit 5min Monitoring Audit Packet",
            "",
            f"- Status: `{summary['status']}`",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`",
            "- Scope: medium post-exit to next V57f rebalance; monitoring only.",
            "- Forbidden: 5min trade trigger, reentry, threshold changes, accepted marking.",
            "",
            "## Finding",
            f"- Event count: {finding.get('event_count', 0)}",
            f"- Dominant effect: `{finding.get('dominant_effect', '')}`",
            f"- Missed upside value: {finding.get('missed_upside_value', 0)}",
            f"- Avoided loss value: {finding.get('avoided_loss_value', 0)}",
            f"- Net cash vs continue-hold delta: {finding.get('net_cash_vs_continue_hold_delta_value', 0)}",
            "",
            "## Ideal Model",
            "- The ideal hindsight model is diagnostic only and uses future outcomes; it is not tradable and not accepted.",
            f"- Compared models: {len(ideal_comparison)}",
            "",
        ]
    )


def _next_prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e sleeve cash policy Quant spec after post-exit monitoring audit

任务目标：
基于 `v5e_post_exit_5min_monitoring_audit_packet/current/` 的 post-exit monitoring 结果，生成 sleeve cash policy Quant spec。只允许解决卖出后现金拖累的治理边界，不得修改 V57f，不得新增止盈阈值，不得允许 reentry before next rebalance，不得把理想事后模型工程化。

必须先阅读：
- v5e_post_exit_5min_monitoring_audit_packet\\current\\v5e_post_exit_5min_audit_summary.json
- v5e_post_exit_5min_monitoring_audit_packet\\current\\v5e_post_exit_5min_ideal_model_comparison.csv
- v5e_post_exit_5min_monitoring_audit_packet\\current\\v5e_post_exit_5min_missed_upside_avoided_loss.csv
- v5e_cash_policy_review\\current\\v5e_cash_policy_review_summary.json

输出：
生成 sleeve cash policy Quant spec 队列和数据门。不得回测，不得 accepted。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Post-Exit 5min Monitoring Audit Rules",
            "",
            "- Medium post-exit monitoring only.",
            "- Do not use 5min data to trigger trades.",
            "- Do not implement the ideal hindsight model.",
            "- Do not allow reentry before next rebalance.",
            "- Do not modify V57f or V5e thresholds.",
            "- Do not mark accepted.",
            "",
        ]
    )


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
    result = run_v5e_post_exit_5min_monitoring_audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
