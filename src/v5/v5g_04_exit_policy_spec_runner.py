from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5g_04_exit_policy_spec") / "current"
DATA_GATE_DIR = Path("v5g_04_cash_proxy_policy_data_gate") / "current"
V5E_511360_AUDIT = Path("v5e_511360_pit_data_audit") / "current"
V5E_511360_REVIEW = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"
V5E_511360_ENGINEERING = Path("v5e_511360_cash_proxy_limited_engineering") / "current"
V5E_SLEEVE_CASH = Path("v5e_sleeve_cash_bucket_engineering") / "current"
V5G_01_ENGINEERING = Path("v5g_01_state_gated_internal_subsleeve_limited_engineering") / "current"

REQUIRED = [
    DATA_GATE_DIR / "v5g_04_cash_proxy_policy_data_gate_summary.json",
    DATA_GATE_DIR / "v5g_04_cash_proxy_policy_matrix.csv",
    DATA_GATE_DIR / "v5g_04_511360_data_source_audit.csv",
    V5E_511360_AUDIT / "v5e_511360_pit_data_audit_summary.json",
    V5E_511360_REVIEW / "v5e_511360_pm_quant_review_summary.json",
    V5E_511360_ENGINEERING / "v5e_511360_cash_proxy_summary.json",
]


def run_v5g_04_exit_policy_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5g_04_exit_policy_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5g_04_exit_policy_summary.json", summary)
        return summary

    data_gate = _read_json(root / DATA_GATE_DIR / "v5g_04_cash_proxy_policy_data_gate_summary.json")
    pm_review = _read_json(root / V5E_511360_REVIEW / "v5e_511360_pm_quant_review_summary.json")
    engineering = _read_json(root / V5E_511360_ENGINEERING / "v5e_511360_cash_proxy_summary.json")
    sleeve_cash = _read_json(root / V5E_SLEEVE_CASH / "v5e_sleeve_cash_bucket_summary.json") if (root / V5E_SLEEVE_CASH / "v5e_sleeve_cash_bucket_summary.json").exists() else {}
    v5g01 = _read_json(root / V5G_01_ENGINEERING / "v5g_01_state_gated_engineering_summary.json") if (root / V5G_01_ENGINEERING / "v5g_01_state_gated_engineering_summary.json").exists() else {}

    dependency = _dependency_audit(data_gate, pm_review, engineering, sleeve_cash, v5g01)
    rule_spec = _rule_spec()
    cash_sources = _cash_source_matrix(sleeve_cash, v5g01)
    lifecycle = _lifecycle()
    data_requirements = _data_requirements()
    governance = _governance(data_gate, pm_review, rule_spec, cash_sources)
    decision = _pm_decision(governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5g_04_exit_policy_dependency_audit.csv", dependency)
    _write_csv(out / "v5g_04_exit_policy_rule_spec.csv", rule_spec)
    _write_csv(out / "v5g_04_cash_source_admission_matrix.csv", cash_sources)
    _write_csv(out / "v5g_04_511360_attachment_lifecycle.csv", lifecycle)
    _write_csv(out / "v5g_04_pit_execution_data_requirements.csv", data_requirements)
    _write_csv(out / "v5g_04_governance_boundary.csv", governance)
    _write_csv(out / "v5g_04_exit_policy_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_04_exit_policy_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5g_04_exit_policy_blockers.csv", blockers_out)
    (out / "v5g_04_exit_policy_report.md").write_text(_report(decision, cash_sources), encoding="utf-8")
    (out / "v5g_04_exit_policy_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5g_04_exit_policy_spec",
        decision[0]["pm_gate_decision"],
        blockers_out,
        exit_policy_spec_pass=decision[0]["exit_policy_spec_pass"],
        cash_proxy_asset="511360",
        cash_proxy_attachment_approved=False,
        limited_engineering_started=False,
        engineering_backtest_started=False,
        admitted_cash_source_count=sum(1 for row in cash_sources if row["admission_status"] in {"admitted_existing_governed_cash_event", "admitted_future_after_separate_approval"}),
    )
    _write_json(out / "v5g_04_exit_policy_summary.json", summary)
    return summary


def _dependency_audit(
    data_gate: dict[str, Any],
    pm_review: dict[str, Any],
    engineering: dict[str, Any],
    sleeve_cash: dict[str, Any],
    v5g01: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {"dependency_id": "v5g_04_cash_proxy_data_gate", "status": "pass" if data_gate.get("data_gate_pass") else "fail", "observed": data_gate.get("pm_gate_decision", "")},
        {"dependency_id": "511360_pm_quant_review", "status": "pass" if pm_review.get("fatal_blocker_count") == 0 else "fail", "observed": pm_review.get("pm_gate_decision", "")},
        {"dependency_id": "511360_limited_engineering", "status": "pass" if engineering.get("fatal_blocker_count") == 0 else "fail", "observed": engineering.get("pm_gate_decision", "")},
        {"dependency_id": "v5e_sleeve_cash_bucket", "status": "available" if sleeve_cash else "optional_missing", "observed": sleeve_cash.get("pm_gate_decision", "")},
        {"dependency_id": "v5g_01_state_gate_cash_source", "status": "no_cash_event" if v5g01 else "optional_missing", "observed": v5g01.get("pm_gate_decision", "")},
    ]


def _rule_spec() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "v5g_04_511360_after_approved_cash_event_only",
            "candidate_asset": "511360",
            "policy_type": "cash_proxy_attachment_spec",
            "entry_condition": "preapproved_cash_event_exists_and_cash_bucket_is_frozen_until_restore",
            "entry_timing": "next_tradeable_session_after_cash_event_execution",
            "exit_condition": "official_restore_or_next_rebalance_requires_cash",
            "exit_timing": "official_restore_trade_date_or_rebalance_trade_date",
            "allowed_cash_sources": "approved_v5e_sleeve_cash_bucket;future_approved_v5g_exit_cash_bucket",
            "blocked_cash_sources": "baseline_idle_cash;unapproved_state_gate;full_market_timing;manual_cash_raise",
            "reentry_allowed": False,
            "new_stock_buy_allowed": False,
            "cross_sleeve_transfer_allowed": False,
            "default_live_use_allowed": False,
            "accepted": False,
            "notes": "This spec admits the attachment rule only; it does not attach 511360 to V5f/V5g without a separately approved cash event.",
        }
    ]


def _cash_source_matrix(sleeve_cash: dict[str, Any], v5g01: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "cash_source_id": "v5e_profit_lock_sleeve_cash_bucket",
            "source_status": "available" if sleeve_cash else "source_file_optional_missing",
            "creates_cash": True,
            "admission_status": "admitted_existing_governed_cash_event" if sleeve_cash else "review_after_source_available",
            "511360_attachable": bool(sleeve_cash),
            "notes": "Existing V5e governed sleeve cash bucket can be a source, but V5e remains not accepted/live approved.",
        },
        {
            "cash_source_id": "v5g_01_state_gated_internal_subsleeve",
            "source_status": "engineered_no_cash_event" if v5g01 else "not_engineered_or_missing",
            "creates_cash": False,
            "admission_status": "blocked_no_cash_bucket",
            "511360_attachable": False,
            "notes": "State gate reverts hot sleeves to baseline internal weights; it does not raise cash.",
        },
        {
            "cash_source_id": "future_v5g_risk_release_cash_bucket",
            "source_status": "future_separate_approval_required",
            "creates_cash": True,
            "admission_status": "admitted_future_after_separate_approval",
            "511360_attachable": False,
            "notes": "Attachable only after a fixed exit/risk-release rule is separately specified and approved.",
        },
        {
            "cash_source_id": "baseline_idle_cash",
            "source_status": "exists_in_baseline",
            "creates_cash": False,
            "admission_status": "blocked",
            "511360_attachable": False,
            "notes": "Do not convert ordinary V57f cash buffer into 511360 by default.",
        },
    ]


def _lifecycle() -> list[dict[str, Any]]:
    return [
        {"step": 1, "stage": "cash_event_confirmed", "required_audit": "cash event must be generated by an approved V5e/V5g rule", "trade_effect": "cash bucket created"},
        {"step": 2, "stage": "proxy_entry_check", "required_audit": "511360 PIT price/liquidity/execution data available", "trade_effect": "eligible for proxy buy only after separate engineering approval"},
        {"step": 3, "stage": "holding_period", "required_audit": "proxy belongs to original cash bucket and sleeve attribution", "trade_effect": "no stock reentry and no cross-sleeve transfer"},
        {"step": 4, "stage": "restore_or_rebalance", "required_audit": "official V57f restore/rebalance demand exists", "trade_effect": "sell proxy and release cash to restore/rebalance"},
        {"step": 5, "stage": "closeout", "required_audit": "cash reconciliation and no live approval", "trade_effect": "tracking packet only"},
    ]


def _data_requirements() -> list[dict[str, Any]]:
    return [
        {"data_domain": "511360_daily_price", "required": True, "pit_required": True, "status": "already_passed_in_v5e_511360_gate"},
        {"data_domain": "511360_nav_or_iopv", "required": True, "pit_required": True, "status": "already_passed_in_v5e_511360_gate"},
        {"data_domain": "511360_5min_execution", "required": "if intraday execution proxy is used", "pit_required": True, "status": "reuse_or_data_gate_before_engineering"},
        {"data_domain": "cash_event_ledger", "required": True, "pit_required": True, "status": "required_before_attachment_engineering"},
        {"data_domain": "restore_calendar", "required": True, "pit_required": True, "status": "official V57f restore/rebalance only"},
        {"data_domain": "fees_slippage_tax", "required": True, "pit_required": True, "status": "required_before limited engineering"},
    ]


def _governance(
    data_gate: dict[str, Any],
    pm_review: dict[str, Any],
    rule_spec: list[dict[str, Any]],
    cash_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {"audit_id": "data_gate_pass", "status": "pass" if data_gate.get("data_gate_pass") else "fail", "detail": data_gate.get("pm_gate_decision", "")},
        {"audit_id": "cash_proxy_review_candidate_not_accepted", "status": "pass" if pm_review.get("accepted") is False else "fail", "detail": pm_review.get("pm_gate_decision", "")},
        {"audit_id": "fixed_asset_only_511360", "status": "pass" if {row["candidate_asset"] for row in rule_spec} == {"511360"} else "fail", "detail": "511360"},
        {"audit_id": "default_live_use_blocked", "status": "pass" if all(not row["default_live_use_allowed"] for row in rule_spec) else "fail", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": False},
        {"audit_id": "state_gate_no_cash_proxy_attachment", "status": "pass" if not any(row["cash_source_id"] == "v5g_01_state_gated_internal_subsleeve" and row["511360_attachable"] for row in cash_sources) else "fail", "detail": "v5g_01 creates no cash bucket"},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pm_decision(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    decision = (
        "v5g_04_exit_policy_spec_pass_cash_proxy_attachable_after_approved_cash_event_not_engineering"
        if gov_ok
        else "blocked_by_v5g_04_exit_policy_governance_issue"
    )
    return [
        {
            "pm_gate_decision": decision,
            "exit_policy_spec_pass": gov_ok,
            "cash_proxy_attachment_approved_now": False,
            "admit_limited_engineering_now": False,
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "engineering_backtest_started": False,
            "next_step": "open_cash_proxy_attachment_limited_engineering_after_cash_event_approval" if gov_ok else "repair_exit_policy_governance",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5g_04_cash_proxy_attachment_limited_engineering",
            "allowed": decision == "v5g_04_exit_policy_spec_pass_cash_proxy_attachable_after_approved_cash_event_not_engineering",
            "status": "blocked_until_specific_cash_event_is_approved",
        },
        {
            "priority": 2,
            "next_gate": "do_not_attach_511360_to_v5g_01_state_gate",
            "allowed": False,
            "status": "blocked_no_cash_bucket",
        },
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]}
        for row in governance
        if row["status"] != "pass"
    ]


def _report(decision: list[dict[str, Any]], cash_sources: list[dict[str, Any]]) -> str:
    attachable = [row["cash_source_id"] for row in cash_sources if row["511360_attachable"]]
    return "\n".join(
        [
            "# V5g 04 Exit Policy Spec",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Currently attachable cash sources: `{';'.join(attachable) if attachable else 'none'}`",
            "- 511360 attachment approved now: `False`",
            "- Engineering backtest started: `False`",
            "- Accepted: `False`",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5g 04 Agent Execution Rules",
            "",
            "- 511360 can only be used after a preapproved cash event.",
            "- Do not convert baseline idle cash into 511360 by default.",
            "- Do not attach 511360 to V5g 01 state gate because it creates no cash bucket.",
            "- Do not modify V57f core.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    blockers = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            blockers.append({"blocker_id": f"missing_{rel.name}", "severity": "fatal", "status": "blocking", "path": str(rel)})
    return blockers


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5g_04_exit_policy_spec",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }
    payload.update(extra)
    return payload


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run_v5g_04_exit_policy_spec()
