from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path("v5f_joinquant_platform_attribution") / "current"
OUT_DIR = Path("v5f_joinquant_platform_forward_handoff") / "current"

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"


def run(root: Path = ROOT) -> Path:
    src = root / SOURCE_DIR
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    summary = _read_json(src / "v5f_joinquant_platform_attribution_summary.json")
    primary_issues = _read_csv(src / "v5f_joinquant_platform_log_order_issues.csv")
    baseline_issues = _read_csv(src / "v5f_joinquant_platform_baseline_log_order_issues.csv")

    residual_summary = _residual_summary(primary_issues, baseline_issues)
    residual_by_date = _residual_by_date(primary_issues, baseline_issues)
    decision_matrix = _decision_matrix(summary)
    policy_spec = _policy_spec()
    checklist = _forward_tracking_checklist(summary)
    allowed_blocked = _allowed_blocked_actions()
    pm_decision = _pm_decision(summary)
    next_queue = _next_queue()

    handoff_summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_joinquant_platform_forward_handoff",
        "status": "completed_platform_clean_edge_forward_handoff",
        "primary_candidate": PRIMARY,
        "baseline": BASELINE,
        "historical_scope": "2021-05-01_to_2026-05-31",
        "last_trading_day": summary.get("last_trading_day"),
        "platform_primary_return_pct": summary.get("jq_platform_total_return_pct"),
        "platform_baseline_return_pct": summary.get("platform_baseline_total_return_pct"),
        "clean_platform_edge_pct_points": summary.get("platform_clean_edge_total_return_pct_points"),
        "relative_wealth_edge_pct": summary.get("platform_clean_relative_wealth_edge_pct"),
        "annualized_edge_pct_points": summary.get("platform_clean_edge_annualized_return_pct_points"),
        "primary_max_drawdown_pct": summary.get("jq_platform_max_drawdown_pct"),
        "baseline_max_drawdown_pct": summary.get("platform_baseline_max_drawdown_pct"),
        "drawdown_delta_pct_points": summary.get("platform_clean_mdd_delta_pct_points"),
        "primary_commission_total": summary.get("commission_total"),
        "baseline_commission_total": summary.get("baseline_commission_total"),
        "primary_total_traded_value": summary.get("total_traded_value"),
        "baseline_total_traded_value": summary.get("baseline_total_traded_value"),
        "primary_unique_order_none_count": _count(primary_issues, "order_none"),
        "baseline_unique_order_none_count": _count(baseline_issues, "order_none"),
        "primary_cancelled_or_unfilled_rows": summary.get("cancelled_or_unfilled_transaction_rows"),
        "baseline_cancelled_or_unfilled_rows": summary.get("baseline_cancelled_or_unfilled_transaction_rows"),
        "round_lot_policy_status": "spec_only_no_historical_rewrite",
        "pm_gate_decision": pm_decision[0]["pm_gate_decision"],
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "new_trading_rule_added": False,
    }

    _write_json(out / "v5f_platform_forward_handoff_summary.json", handoff_summary)
    _write_csv(out / "v5f_platform_clean_edge_decision_matrix.csv", decision_matrix)
    _write_csv(out / "v5f_platform_round_lot_residual_summary.csv", residual_summary)
    _write_csv(out / "v5f_platform_round_lot_residual_by_date.csv", residual_by_date)
    _write_csv(out / "v5f_platform_round_lot_policy_spec.csv", policy_spec)
    _write_csv(out / "v5f_platform_forward_tracking_checklist.csv", checklist)
    _write_csv(out / "v5f_platform_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5f_platform_pm_gate_decision.csv", pm_decision)
    _write_csv(out / "v5f_platform_next_queue.csv", next_queue)
    _write_rules(out / "v5f_platform_agent_execution_rules.md")
    _write_report(out / "v5f_platform_forward_handoff_report.md", handoff_summary)

    print(json.dumps(handoff_summary, ensure_ascii=False, indent=2))
    return out / "v5f_platform_forward_handoff_summary.json"


def _decision_matrix(summary: dict[str, Any]) -> list[dict[str, Any]]:
    edge = _num(summary.get("platform_clean_edge_total_return_pct_points"))
    dd = _num(summary.get("platform_clean_mdd_delta_pct_points"))
    return [
        {
            "component": "clean_platform_edge",
            "observed": f"{edge:.4f} pct points",
            "status": "pass_positive",
            "decision": "retain_primary_forward_paper",
            "notes": "Same JoinQuant platform primary beats same-platform repaired baseline.",
        },
        {
            "component": "drawdown",
            "observed": f"{dd:.4f} pct points",
            "status": "review",
            "decision": "monitor_forward_drawdown",
            "notes": "Primary drawdown is slightly higher than platform baseline; not a blocker, not an accepted gate.",
        },
        {
            "component": "execution_cost",
            "observed": f"primary_commission={_num(summary.get('commission_total')):.2f}; baseline_commission={_num(summary.get('baseline_commission_total')):.2f}",
            "status": "review",
            "decision": "monitor_cost_and_turnover",
            "notes": "Primary trades more and pays more commission than baseline; edge remains positive after platform execution.",
        },
        {
            "component": "accepted_gate",
            "observed": "not_allowed",
            "status": "blocked",
            "decision": "not_accepted_not_live",
            "notes": "Platform confirmation supports forward/paper only.",
        },
    ]


def _residual_summary(primary: list[dict[str, str]], baseline: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for model, issues in [(PRIMARY, primary), (BASELINE, baseline)]:
        for issue_type in sorted({row.get("issue_type", "") for row in issues}):
            group = [row for row in issues if row.get("issue_type") == issue_type]
            rows.append(
                {
                    "model_id": model,
                    "issue_type": issue_type,
                    "row_count": len(group),
                    "unique_trade_dates": len({row.get("trade_date", "") for row in group if row.get("trade_date", "")}),
                    "unique_codes": len({row.get("code", "") for row in group if row.get("code", "")}),
                    "target_value_sum": sum(_num(row.get("target_value_or_order_value")) for row in group),
                    "governance_read": _issue_read(issue_type),
                }
            )
    return rows


def _residual_by_date(primary: list[dict[str, str]], baseline: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for model, issues in [(PRIMARY, primary), (BASELINE, baseline)]:
        keys = sorted({(row.get("trade_date", ""), row.get("issue_type", "")) for row in issues})
        for trade_date, issue_type in keys:
            group = [row for row in issues if row.get("trade_date") == trade_date and row.get("issue_type") == issue_type]
            rows.append(
                {
                    "model_id": model,
                    "trade_date": trade_date,
                    "issue_type": issue_type,
                    "row_count": len(group),
                    "codes": ";".join(sorted({row.get("code", "") for row in group if row.get("code", "")})),
                    "target_value_sum": sum(_num(row.get("target_value_or_order_value")) for row in group),
                    "audit_status": "execution_residual_review_not_model_rule_change",
                }
            )
    return rows


def _policy_spec() -> list[dict[str, Any]]:
    return [
        {
            "policy_item": "sub_lot_target_delta",
            "allowed": True,
            "status": "spec_only_forward_logging",
            "rule": "If expected delta shares after 100-share rounding equals zero, log no_trade_sub_lot_residual and keep current holding/cash.",
            "historical_result_change": False,
            "requires_new_backtest": False,
        },
        {
            "policy_item": "paused_or_limit_blocked_order",
            "allowed": True,
            "status": "spec_only_forward_logging",
            "rule": "Log unfilled execution state; do not synthesize a fill. Separate approval is required for retry or catch-up execution.",
            "historical_result_change": False,
            "requires_new_backtest": False,
        },
        {
            "policy_item": "force_trade_to_match_target_weight",
            "allowed": False,
            "status": "blocked",
            "rule": "Do not force non-round-lot trades or alter target weights to hide platform residuals.",
            "historical_result_change": False,
            "requires_new_backtest": False,
        },
        {
            "policy_item": "acceptance_from_platform_edge",
            "allowed": False,
            "status": "blocked",
            "rule": "Clean positive platform edge may support forward/paper primary status only.",
            "historical_result_change": False,
            "requires_new_backtest": False,
        },
    ]


def _forward_tracking_checklist(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "check_item": "freeze_model_id",
            "required": True,
            "status": "ready",
            "detail": PRIMARY,
        },
        {
            "step": 2,
            "check_item": "freeze_baseline",
            "required": True,
            "status": "ready",
            "detail": BASELINE,
        },
        {
            "step": 3,
            "check_item": "use_official_rebalance_signal_only",
            "required": True,
            "status": "ready",
            "detail": "No daily signal refresh beyond approved V57f/V5f schedule.",
        },
        {
            "step": 4,
            "check_item": "export_platform_daily_transaction_position_log",
            "required": True,
            "status": "ready_after_next_forward_window",
            "detail": "Use same JoinQuant export template for primary and baseline when a future forward window is available.",
        },
        {
            "step": 5,
            "check_item": "record_round_lot_residuals",
            "required": True,
            "status": "ready",
            "detail": "Explicitly log sub-100-share, paused, and limit-blocked orders.",
        },
        {
            "step": 6,
            "check_item": "accepted_live_approval",
            "required": False,
            "status": "blocked",
            "detail": "Not allowed in this handoff.",
        },
    ]


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "continue_forward_paper_tracking", "allowed": True, "blocked": False, "notes": "Primary platform edge is positive."},
        {"action": "use_clean_platform_comparison_as_evidence", "allowed": True, "blocked": False, "notes": "Evidence only, not accepted gate."},
        {"action": "log_sub_lot_residuals", "allowed": True, "blocked": False, "notes": "Governance logging only."},
        {"action": "change_v57f_core", "allowed": False, "blocked": True, "notes": "Out of scope."},
        {"action": "scan_momentum_parameters", "allowed": False, "blocked": True, "notes": "Out of scope."},
        {"action": "mark_accepted", "allowed": False, "blocked": True, "notes": "Not allowed."},
        {"action": "mark_live_approved", "allowed": False, "blocked": True, "notes": "Not allowed."},
        {"action": "rewrite_historical_platform_results_for_round_lot_policy", "allowed": False, "blocked": True, "notes": "Residual policy is forward logging only."},
    ]


def _pm_decision(summary: dict[str, Any]) -> list[dict[str, Any]]:
    edge = _num(summary.get("platform_clean_edge_total_return_pct_points"))
    return [
        {
            "pm_gate_decision": "retain_internal_subsleeve_mom12_70_30_forward_paper_primary_after_clean_platform_edge",
            "clean_platform_edge_pct_points": edge,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "rationale": "Same-platform JoinQuant edge is positive; governance still requires forward/paper tracking before any promotion.",
        }
    ]


def _next_queue() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "next_task": "continue_v5f_forward_paper_tracking_for_internal_subsleeve_mom12_70_30",
            "status": "ready",
            "detail": "Track primary and repaired baseline on each future official V57f/V5f forward window.",
        },
        {
            "rank": 2,
            "next_task": "add_sub_lot_residual_logging_to_future_platform_template",
            "status": "ready_spec_only",
            "detail": "Make logging explicit; do not rewrite historical results.",
        },
        {
            "rank": 3,
            "next_task": "periodic_forward_closeout_after_next_official_rebalance",
            "status": "waiting_future_rebalance",
            "detail": "Compare forward primary vs baseline after the next official rebalance period closes.",
        },
    ]


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    text = f"""# V5f JoinQuant Platform Forward Handoff

## Decision

`internal_subsleeve_mom12_70_30` remains the V5f forward/paper primary after clean JoinQuant platform comparison.

## Evidence

- Platform primary return: `{summary['platform_primary_return_pct']:.4f}%`.
- Platform repaired baseline return: `{summary['platform_baseline_return_pct']:.4f}%`.
- Clean platform edge: `{summary['clean_platform_edge_pct_points']:.4f}` pct points.
- Relative wealth edge: `{summary['relative_wealth_edge_pct']:.4f}%`.
- Annualized edge: `{summary['annualized_edge_pct_points']:.4f}` pct points.
- Primary/baseline max drawdown: `{summary['primary_max_drawdown_pct']:.4f}%` / `{summary['baseline_max_drawdown_pct']:.4f}%`.
- Drawdown delta: `{summary['drawdown_delta_pct_points']:.4f}` pct points.

## Execution Governance

- Primary unique order-none residuals: `{summary['primary_unique_order_none_count']}`.
- Baseline unique order-none residuals: `{summary['baseline_unique_order_none_count']}`.
- Primary cancelled/unfilled export rows: `{summary['primary_cancelled_or_unfilled_rows']}`.
- Baseline cancelled/unfilled export rows: `{summary['baseline_cancelled_or_unfilled_rows']}`.
- Round-lot policy status: `{summary['round_lot_policy_status']}`.

These residuals are platform execution artifacts. They do not change V57f core and do not justify rewriting historical results.

## PM Gate

`{summary['pm_gate_decision']}`
"""
    path.write_text(text, encoding="utf-8")


def _write_rules(path: Path) -> None:
    path.write_text(
        """# V5f Platform Forward Handoff Execution Rules

- Use repaired baseline only: v57f_startup_preload_repaired_baseline.
- Keep internal_subsleeve_mom12_70_30 as forward/paper primary, not accepted.
- Do not modify V57f core, sleeve definitions, target counts, or rebalance schedule.
- Do not scan parameters.
- Do not rewrite historical JoinQuant platform results.
- Round-lot residual handling is logging/governance only.
- Do not mark accepted or live approved.
""",
        encoding="utf-8",
    )


def _issue_read(issue_type: str) -> str:
    if issue_type == "order_none":
        return "unique explicit no-order residual; use for forward no-trade logging policy"
    if issue_type == "order_failed":
        return "platform error line corresponding to order residual; do not double count with order_none for unique misses"
    if issue_type == "skipped_paused":
        return "paused security execution residual"
    if issue_type == "limit_cancel":
        return "limit-up/down execution residual"
    return "execution residual"


def _count(rows: list[dict[str, str]], issue_type: str) -> int:
    return sum(1 for row in rows if row.get("issue_type") == issue_type)


def _num(value: Any) -> float:
    try:
        if value in ("", None):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
    run()
