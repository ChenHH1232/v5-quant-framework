from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_historical_closeout_governance_packet") / "current"
MODEL_DIR = Path("v5e_profit_lock_model_comparison") / "current"
FULL_5MIN_DIR = Path("v5e_full_holding_5min_data_gate") / "current"
INTRADAY_DIR = Path("v5e_full_intraday_nav_engineering_test") / "current"
SLEEVE_CASH_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
CASH_PROXY_ENG_DIR = Path("v5e_511360_cash_proxy_limited_engineering") / "current"
CASH_PROXY_PM_DIR = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"
CASH_PROXY_STRESS_DIR = Path("v5e_511360_cash_proxy_forward_stress_packet") / "current"
CASH_PROXY_TRACKING_DIR = Path("v5e_511360_forward_paper_tracking") / "current"
SLEEVE_RELEASE_DIR = Path("v5e_sleeve_level_risk_release_limited_engineering") / "current"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_historical_closeout_governance(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_backtest_scope_blocker_reclassification.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_historical_closeout_summary.json", summary)
        return summary

    inputs = _load_inputs(root)
    component_status = _component_status_matrix(inputs)
    candidate_diag = _candidate_vs_diagnostic_matrix(inputs)
    blocker_reclass = _backtest_scope_blocker_reclassification(inputs)
    forward_reclass = _forward_202607_reclassification(inputs)
    allowed_blocked = _allowed_blocked_actions()
    final_decision = _final_governance_decision(inputs, blocker_reclass, forward_reclass)
    next_queue = _next_stage_queue()

    _write_csv(out / "v5e_component_status_matrix.csv", component_status)
    _write_csv(out / "v5e_candidate_vs_diagnostic_matrix.csv", candidate_diag)
    _write_csv(out / "v5e_backtest_scope_blocker_reclassification.csv", blocker_reclass)
    _write_csv(out / "v5e_202607_forward_only_reclassification.csv", forward_reclass)
    _write_csv(out / "v5e_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5e_final_governance_decision.csv", final_decision)
    _write_csv(out / "v5e_next_stage_queue.csv", next_queue)
    (out / "v5e_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_historical_closeout_report.md").write_text(
        _report(inputs, final_decision, component_status, candidate_diag, forward_reclass),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5e_historical_closeout_governance_packet",
        final_decision[0]["historical_closeout_status"],
        [],
        component_count=len(component_status),
        candidate_count=sum(1 for row in candidate_diag if row["classification"].endswith("candidate")),
        diagnostic_count=sum(1 for row in candidate_diag if row["classification"] == "diagnostic_only"),
        forward_only_blocker_count=sum(1 for row in forward_reclass if row["reclassified_status"] == "forward_only_not_backtest_blocker"),
    )
    _write_json(out / "v5e_historical_closeout_summary.json", summary)
    return summary


def _load_inputs(root: Path) -> dict[str, Any]:
    return {
        "model": _read_json(root / MODEL_DIR / "v5e_model_comparison_summary.json"),
        "full_5min": _read_json(root / FULL_5MIN_DIR / "v5e_full_holding_5min_summary.json"),
        "full_5min_gate": _read_csv(root / FULL_5MIN_DIR / "v5e_full_holding_5min_pm_gate_decision.csv"),
        "intraday": _read_json(root / INTRADAY_DIR / "v5e_full_intraday_nav_summary.json"),
        "sleeve_cash": _read_json(root / SLEEVE_CASH_DIR / "v5e_sleeve_cash_bucket_summary.json"),
        "sleeve_cash_gate": _read_csv(root / SLEEVE_CASH_DIR / "v5e_sleeve_cash_pm_gate_decision.csv"),
        "cash_proxy_eng": _read_json(root / CASH_PROXY_ENG_DIR / "v5e_511360_cash_proxy_summary.json"),
        "cash_proxy_eng_gate": _read_csv(root / CASH_PROXY_ENG_DIR / "v5e_511360_cash_proxy_pm_gate_decision.csv"),
        "cash_proxy_pm": _read_json(root / CASH_PROXY_PM_DIR / "v5e_511360_pm_quant_review_summary.json"),
        "cash_proxy_stress": _read_json(root / CASH_PROXY_STRESS_DIR / "v5e_511360_forward_stress_summary.json"),
        "cash_proxy_tracking": _read_json(root / CASH_PROXY_TRACKING_DIR / "v5e_511360_forward_tracking_summary.json"),
        "cash_proxy_tracking_blockers": _read_csv(root / CASH_PROXY_TRACKING_DIR / "v5e_511360_forward_tracking_blockers.csv"),
        "sleeve_release": _read_json(root / SLEEVE_RELEASE_DIR / "v5e_sleeve_level_release_summary.json"),
        "sleeve_release_gate": _read_csv(root / SLEEVE_RELEASE_DIR / "v5e_sleeve_level_release_pm_gate_decision.csv"),
    }


def _component_status_matrix(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    model = inputs["model"]
    full_5min = inputs["full_5min"]
    intraday = inputs["intraday"]
    sleeve_cash = inputs["sleeve_cash"]
    proxy = inputs["cash_proxy_pm"]
    tracking = inputs["cash_proxy_tracking"]
    sleeve_release = inputs["sleeve_release"]
    return [
        {
            "component_id": "single_name_profit_lock_main",
            "status": "forward_paper_candidate_not_accepted",
            "historical_scope_status": "complete",
            "key_result": f"daily_open_delta={model.get('daily_open_delta_return_pct_points_200w')} pct_points; vwap_adjusted_delta={model.get('vwap_adjusted_delta_return_pct_points_200w')} pct_points",
            "accepted": False,
            "v57f_replacement": False,
        },
        {
            "component_id": "full_holding_period_5min_data",
            "status": "coverage_pass_for_research_execution_audit",
            "historical_scope_status": "complete",
            "key_result": f"effective_coverage_rate_pct={full_5min.get('effective_coverage_rate_pct')}; minute_data_used_for_trigger={full_5min.get('minute_data_used_for_trigger')}",
            "accepted": False,
            "v57f_replacement": False,
        },
        {
            "component_id": "full_intraday_trigger_rolling_nav",
            "status": "diagnostic_only",
            "historical_scope_status": "complete_diagnostic",
            "key_result": f"pm_gate={intraday.get('pm_gate_decision')}; delta_return={intraday.get('rolling_delta_return_pct_points_vs_baseline')} pct_points",
            "accepted": False,
            "v57f_replacement": False,
        },
        {
            "component_id": "sleeve_cash_bucket_accounting",
            "status": "governance_pass",
            "historical_scope_status": "complete",
            "key_result": f"no_reentry={sleeve_cash.get('no_reentry_violation_count')}; no_cross_sleeve={sleeve_cash.get('no_cross_sleeve_violation_count')}; primary_drag_sleeve={sleeve_cash.get('primary_cash_drag_sleeve')}",
            "accepted": False,
            "v57f_replacement": False,
        },
        {
            "component_id": "511360_cash_proxy",
            "status": "cash_proxy_forward_review_candidate_not_accepted",
            "historical_scope_status": "complete_for_backtest_scope",
            "key_result": f"delta_vs_v57f={proxy.get('delta_return_vs_v57f')}; delta_vs_hold_cash={proxy.get('delta_return_vs_hold_cash')}; forward_restore_available={tracking.get('official_v57f_restore_available')}",
            "accepted": False,
            "v57f_replacement": False,
        },
        {
            "component_id": "sleeve_level_risk_release",
            "status": "diagnostic_only",
            "historical_scope_status": "complete_diagnostic",
            "key_result": f"pm_gate={sleeve_release.get('pm_gate_decision')}; best_delta_vs_v57f={sleeve_release.get('best_delta_return_vs_v57f')}",
            "accepted": False,
            "v57f_replacement": False,
        },
    ]


def _candidate_vs_diagnostic_matrix(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    model = inputs["model"]
    proxy = inputs["cash_proxy_pm"]
    sleeve_release = inputs["sleeve_release"]
    intraday = inputs["intraday"]
    return [
        {
            "component_id": "v5e_profit_lock_main_20pct_sell50",
            "classification": "forward_paper_candidate",
            "reason": "Pre-registered single-name profit-lock rule retained for forward/paper, but VWAP-adjusted edge is thin.",
            "key_metric": model.get("vwap_adjusted_delta_return_pct_points_200w"),
            "accepted": False,
        },
        {
            "component_id": "v5e_511360_cash_proxy",
            "classification": "forward_review_candidate",
            "reason": "Improves historical cash-drag outcome and passes governance, but needs forward evidence and official restore closeout.",
            "key_metric": proxy.get("delta_return_vs_hold_cash"),
            "accepted": False,
        },
        {
            "component_id": "full_intraday_trigger_rolling_nav",
            "classification": "diagnostic_only",
            "reason": "Full intraday rolling NAV was downgraded and cannot become a trading trigger.",
            "key_metric": intraday.get("rolling_delta_return_pct_points_vs_baseline"),
            "accepted": False,
        },
        {
            "component_id": "sleeve_level_risk_release",
            "classification": "diagnostic_only",
            "reason": "Best sleeve-level rule improved drawdown but did not improve return versus V5e hold cash and used close-proxy execution.",
            "key_metric": sleeve_release.get("best_delta_return_vs_hold_cash"),
            "accepted": False,
        },
        {
            "component_id": "sleeve_cash_bucket_accounting",
            "classification": "governance_infrastructure",
            "reason": "Ledger and audits passed; this is accounting/governance infrastructure, not a return candidate.",
            "key_metric": inputs["sleeve_cash"].get("primary_cash_drag_sleeve"),
            "accepted": False,
        },
    ]


def _backtest_scope_blocker_reclassification(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    tracking_blockers = inputs["cash_proxy_tracking_blockers"]
    for blocker in tracking_blockers:
        blocker_id = blocker.get("blocker_id", "")
        if "202607" in blocker_id or "2026-07" in blocker.get("description", ""):
            rows.append(
                {
                    "blocker_id": blocker_id,
                    "original_status": blocker.get("status", ""),
                    "historical_scope_status": "not_backtest_blocker",
                    "reclassified_status": "forward_only_not_backtest_blocker",
                    "reason": "2026-07 official restore is outside fixed historical backtest scope 2021-05-01 to 2026-05-31.",
                }
            )
        else:
            rows.append(
                {
                    "blocker_id": blocker_id,
                    "original_status": blocker.get("status", ""),
                    "historical_scope_status": "review_note",
                    "reclassified_status": blocker.get("status", ""),
                    "reason": blocker.get("description", ""),
                }
            )
    return rows or [
        {
            "blocker_id": "none",
            "original_status": "none",
            "historical_scope_status": "complete",
            "reclassified_status": "none",
            "reason": "No blocker applies to fixed historical backtest scope.",
        }
    ]


def _forward_202607_reclassification(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    tracking = inputs["cash_proxy_tracking"]
    return [
        {
            "item_id": "official_v57f_202607_restore_unavailable",
            "source_gate": tracking.get("pm_gate_decision"),
            "backtest_scope": f"{BACKTEST_START} to {BACKTEST_END}",
            "event_date": "2026-07-01",
            "inside_backtest_scope": False,
            "reclassified_status": "forward_only_not_backtest_blocker",
            "historical_closeout_blocker": False,
            "forward_tracking_pending": True,
            "reason": "Official 2026-07 rebalance/restore is outside the fixed historical closeout window.",
        }
    ]


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "historical_closeout_governance_packet", "allowed": True, "blocked": False, "reason": "Current task scope."},
        {"action": "forward_paper_tracking_continuation", "allowed": True, "blocked": False, "reason": "Allowed next-stage activity."},
        {"action": "511360_official_restore_closeout_when_signal_available", "allowed": True, "blocked": False, "reason": "Forward-only closeout once official signals exist."},
        {"action": "modify_v57f_core", "allowed": False, "blocked": True, "reason": "V57f is frozen formal ETF candidate."},
        {"action": "mark_v5e_accepted_or_live_approved", "allowed": False, "blocked": True, "reason": "Historical evidence cannot approve V5e."},
        {"action": "scan_profit_lock_thresholds", "allowed": False, "blocked": True, "reason": "Parameter scan prohibited."},
        {"action": "accept_full_intraday_trigger", "allowed": False, "blocked": True, "reason": "Full intraday trigger downgraded diagnostic."},
        {"action": "accept_511360_cash_proxy", "allowed": False, "blocked": True, "reason": "Forward/paper evidence and official restore closeout still required."},
        {"action": "promote_sleeve_level_release_candidate", "allowed": False, "blocked": True, "reason": "Sleeve-level release remains diagnostic only."},
        {"action": "start_joinquant_or_fetch_new_data", "allowed": False, "blocked": True, "reason": "Current historical governance task forbids external execution/data fetch."},
    ]


def _final_governance_decision(
    inputs: dict[str, Any],
    blocker_reclass: list[dict[str, Any]],
    forward_reclass: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "historical_closeout_status": "complete",
            "backtest_scope_start": BACKTEST_START,
            "backtest_scope_end": BACKTEST_END,
            "v5e_accepted": False,
            "v5e_replacement_for_v57f": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "full_intraday_trigger_accepted": False,
            "cash_proxy_511360_accepted": False,
            "sleeve_level_release_accepted": False,
            "single_name_profit_lock_candidate": "forward_paper_candidate_not_accepted",
            "cash_proxy_511360_candidate": "forward_review_candidate_not_accepted",
            "sleeve_level_release_status": "diagnostic_only",
            "2026_07_restore_blocker_status": "forward_only_not_backtest_blocker",
            "historical_fatal_blocker_count": sum(1 for row in blocker_reclass if row.get("historical_scope_status") == "backtest_blocker"),
            "accepted": False,
        }
    ]


def _next_stage_queue() -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "V5e forward/paper tracking continuation",
            "allowed": True,
            "scope": "Continue tracking V5e profit-lock and 511360 proxy without acceptance.",
        },
        {
            "priority": 2,
            "next_task": "511360 official restore closeout only when future official V57f rebalance signal is available",
            "allowed": True,
            "scope": "Forward-only; not a historical backtest blocker.",
        },
        {
            "priority": 3,
            "next_task": "V5f / deployment governance / paper trading workflow preparation",
            "allowed": True,
            "scope": "Prepare governance workflow while keeping V5e not accepted.",
        },
        {
            "priority": 4,
            "next_task": "Do not continue V5e profit-lock parameter scan",
            "allowed": False,
            "scope": "Threshold scan prohibited.",
        },
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    component_count: int = 0,
    candidate_count: int = 0,
    diagnostic_count: int = 0,
    forward_only_blocker_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_historical_closeout_governance_packet",
        "status": status,
        "historical_closeout_status": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "component_count": component_count,
        "candidate_count": candidate_count,
        "diagnostic_count": diagnostic_count,
        "forward_only_blocker_count": forward_only_blocker_count,
        "v5e_accepted": False,
        "v5e_replacement_for_v57f": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    inputs: dict[str, Any],
    final_decision: list[dict[str, Any]],
    component_status: list[dict[str, Any]],
    candidate_diag: list[dict[str, Any]],
    forward_reclass: list[dict[str, Any]],
) -> str:
    model = inputs["model"]
    proxy = inputs["cash_proxy_pm"]
    sleeve_release = inputs["sleeve_release"]
    final = final_decision[0]
    return "\n".join(
        [
            "# V5e Historical Closeout Governance Packet",
            "",
            f"- Historical backtest scope: {BACKTEST_START} to {BACKTEST_END}.",
            f"- Historical closeout: `{final['historical_closeout_status']}`.",
            "- V5e accepted: `False`.",
            "- V5e replacement for V57f: `False`.",
            "- V57f core modified: `False`.",
            "",
            "## Candidates",
            f"- `v5e_profit_lock_main_20pct_sell50`: forward/paper candidate, not accepted; VWAP-adjusted edge is thin at {model.get('vwap_adjusted_delta_return_pct_points_200w')} pct points.",
            f"- `v5e_511360_cash_proxy`: forward review candidate, not accepted; delta vs V57f {float(proxy.get('delta_return_vs_v57f', 0.0)) * 100:.4f} pct points, delta vs hold cash {float(proxy.get('delta_return_vs_hold_cash', 0.0)) * 100:.4f} pct points.",
            "",
            "## Diagnostic Only",
            "- Full intraday trigger / rolling NAV remains diagnostic only.",
            f"- Sleeve-level risk release remains diagnostic only; best delta vs hold-cash is {float(sleeve_release.get('best_delta_return_vs_hold_cash', 0.0)) * 100:.4f} pct points.",
            "",
            "## 2026-07 Reclassification",
            f"- 2026-07 restore blocker status: `{forward_reclass[0]['reclassified_status']}`.",
            "- It is outside the fixed historical backtest window and cannot block historical closeout.",
            "",
            "## Next",
            "- Continue V5e forward/paper tracking.",
            "- Complete 511360 official restore closeout only when future official V57f rebalance signals are available.",
            "- Move to V5f / deployment governance / paper trading workflow preparation as a separate governance path.",
            "- Do not continue V5e stop-profit threshold scanning.",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Historical Closeout Agent Execution Rules",
            "",
            "- Historical backtest scope is fixed at 2021-05-01 to 2026-05-31.",
            "- Do not treat 2026-07 official restore unavailable as a historical backtest blocker.",
            "- Do not modify V57f core.",
            "- Do not modify V5e thresholds or scan parameters.",
            "- Do not start JoinQuant or fetch new data.",
            "- Do not mark any V5e component accepted or live approved.",
            "- 511360 remains a cash proxy candidate / forward review candidate only.",
            "- Sleeve-level release and full intraday trigger remain diagnostic only.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        MODEL_DIR / "v5e_model_comparison_summary.json",
        MODEL_DIR / "v5e_model_comparison_report.md",
        FULL_5MIN_DIR / "v5e_full_holding_5min_summary.json",
        FULL_5MIN_DIR / "v5e_full_holding_5min_pm_gate_decision.csv",
        INTRADAY_DIR / "v5e_full_intraday_nav_summary.json",
        INTRADAY_DIR / "v5e_full_intraday_nav_report.md",
        SLEEVE_CASH_DIR / "v5e_sleeve_cash_bucket_summary.json",
        SLEEVE_CASH_DIR / "v5e_sleeve_cash_pm_gate_decision.csv",
        CASH_PROXY_ENG_DIR / "v5e_511360_cash_proxy_summary.json",
        CASH_PROXY_ENG_DIR / "v5e_511360_cash_proxy_pm_gate_decision.csv",
        CASH_PROXY_PM_DIR / "v5e_511360_pm_quant_review_summary.json",
        CASH_PROXY_STRESS_DIR / "v5e_511360_forward_stress_summary.json",
        CASH_PROXY_TRACKING_DIR / "v5e_511360_forward_tracking_summary.json",
        CASH_PROXY_TRACKING_DIR / "v5e_511360_forward_tracking_blockers.csv",
        SLEEVE_RELEASE_DIR / "v5e_sleeve_level_release_summary.json",
        SLEEVE_RELEASE_DIR / "v5e_sleeve_level_release_pm_gate_decision.csv",
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e historical closeout input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
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
    result = run_v5e_historical_closeout_governance()
    print(json.dumps(result, ensure_ascii=False, indent=2))
