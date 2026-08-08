from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_highway_ocf_risk_cap_rule_freeze") / "current"
SPEC_DIR = Path("v5c_infra_ocf_quality_fixed_rule_quant_spec") / "current"
CAPEX_DIR = Path("v5c_infra_capex_original_statement_extraction") / "current"
SIDECAR_DIR = Path("v5c_sidecar_observation_enhancement") / "current"
CYCLE_DIR = Path("v5c_cycle_sector_data_gate_queue") / "current"

TRAIN_START = "2013-01-01"
TRAIN_END = "2021-04-30"
FORMAL_START = "2021-05-01"
FORMAL_END = "2026-05-31"
PRIMARY_REFERENCE = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
FROZEN_RULE_ID = "highway_ocf_yield_quality_guard_v1_risk_cap_only"


def run_v5c_highway_ocf_risk_cap_rule_freeze(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_inputs", blockers)
        _write_json(out / "v5c_highway_ocf_risk_cap_rule_freeze_summary.json", summary)
        _write_csv(out / "v5c_highway_ocf_risk_cap_blockers.csv", blockers)
        return summary

    spec_summary = _read_json(root / SPEC_DIR / "v5c_infra_ocf_quality_fixed_rule_spec_summary.json")
    rule_specs = _read_csv(root / SPEC_DIR / "v5c_infra_ocf_quality_rule_spec.csv")
    evidence = _read_csv(root / SPEC_DIR / "v5c_infra_ocf_quality_pre2021_evidence_snapshot.csv")
    capex_summary = _read_json(root / CAPEX_DIR / "v5c_infra_capex_original_statement_summary.json")
    capex_panel = _read_csv(root / CAPEX_DIR / "v5c_infra_capex_strict_panel.csv")
    capex_blockers = _read_csv(root / CAPEX_DIR / "v5c_infra_capex_blockers.csv")
    sidecar_queue = _read_csv(root / SIDECAR_DIR / "v5c_sidecar_observation_enhancement_queue.csv")
    cycle_queue = _read_csv(root / CYCLE_DIR / "v5c_cycle_sector_data_gate_queue.csv")

    frozen_rule = _frozen_rule(rule_specs, evidence)
    field_contract = _field_contract()
    rule_formula = _rule_formula()
    capex_review_queue = _capex_review_queue(capex_panel, capex_blockers)
    readiness = _limited_engineering_readiness(spec_summary, capex_summary, capex_review_queue)
    governance = _governance_audit()
    sidecar_update = _sidecar_update(sidecar_queue)
    cycle_update = _cycle_update(cycle_queue)
    pm_decision = _pm_decision(readiness)
    next_queue = _next_queue(pm_decision)
    blockers_out = _blockers(capex_review_queue, readiness)

    summary = _summary(
        "completed_rule_freeze_packet",
        blockers_out,
        pm_gate_decision=pm_decision[0]["pm_gate_decision"],
        capex_review_queue_count=len(capex_review_queue),
    )
    _write_json(out / "v5c_highway_ocf_risk_cap_rule_freeze_summary.json", summary)
    _write_csv(out / "v5c_highway_ocf_risk_cap_frozen_rule.csv", frozen_rule)
    (out / "v5c_highway_ocf_risk_cap_formula.md").write_text(rule_formula, encoding="utf-8")
    _write_csv(out / "v5c_highway_ocf_risk_cap_field_contract.csv", field_contract)
    _write_csv(out / "v5c_highway_capex_fcf_original_page_review_queue.csv", capex_review_queue)
    _write_csv(out / "v5c_highway_ocf_risk_cap_limited_engineering_readiness.csv", readiness)
    _write_csv(out / "v5c_highway_ocf_risk_cap_governance_audit.csv", governance)
    _write_csv(out / "v5c_sidecar_observation_update.csv", sidecar_update)
    _write_csv(out / "v5c_cycle_sector_data_gate_update.csv", cycle_update)
    _write_csv(out / "v5c_highway_ocf_risk_cap_pm_gate_decision.csv", pm_decision)
    _write_csv(out / "v5c_highway_ocf_risk_cap_next_queue.csv", next_queue)
    _write_csv(out / "v5c_highway_ocf_risk_cap_blockers.csv", blockers_out)
    (out / "v5c_highway_ocf_risk_cap_rule_freeze_report.md").write_text(
        _report(summary, frozen_rule, readiness, capex_review_queue, pm_decision, sidecar_update, cycle_update),
        encoding="utf-8",
    )
    (out / "v5c_highway_ocf_risk_cap_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPEC_DIR / "v5c_infra_ocf_quality_fixed_rule_spec_summary.json",
        SPEC_DIR / "v5c_infra_ocf_quality_rule_spec.csv",
        SPEC_DIR / "v5c_infra_ocf_quality_pre2021_evidence_snapshot.csv",
        CAPEX_DIR / "v5c_infra_capex_original_statement_summary.json",
        CAPEX_DIR / "v5c_infra_capex_strict_panel.csv",
        CAPEX_DIR / "v5c_infra_capex_blockers.csv",
        SIDECAR_DIR / "v5c_sidecar_observation_enhancement_queue.csv",
        CYCLE_DIR / "v5c_cycle_sector_data_gate_queue.csv",
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "path": str(path),
            "required_action": "restore prior V5c queue outputs before freezing the rule",
        }
        for path in required
        if not (root / path).exists()
    ]


def _frozen_rule(rule_specs: list[dict[str, str]], evidence: list[dict[str, str]]) -> list[dict[str, Any]]:
    base = next((row for row in rule_specs if row.get("rule_id") == "highway_ocf_yield_quality_guard"), {})
    evidence_map = {row.get("factor_id", ""): row for row in evidence if row.get("sector_id") == "highway_infrastructure"}
    return [
        {
            "frozen_rule_id": FROZEN_RULE_ID,
            "source_rule_id": base.get("rule_id", "highway_ocf_yield_quality_guard"),
            "sector_id": "highway_infrastructure",
            "rule_status": "frozen_for_limited_engineering_review_not_accepted",
            "rule_type": "risk_cap_only",
            "primary_reference": PRIMARY_REFERENCE,
            "baseline": BASELINE,
            "eligible_pool": "existing V57f/V5f highway sleeve holdings only",
            "trigger_condition": "operating_cash_flow_yield bottom tercile OR operating_cash_flow_to_net_profit below same-date highway median",
            "secondary_confirmation": "ocf_to_revenue retained for audit and tie review; not required for trigger v1",
            "action": "cap V5f overweight above repaired baseline target weight for flagged names",
            "redistribution": "redistribute capped excess pro-rata to non-flagged existing highway names inside the same sleeve; if none, retain original V5f weights and log no_action",
            "missing_data_policy": "do not auto-flag on missing fields; mark needs_data_review",
            "capex_fcf_policy": "excluded from v1 model input; original-page review queue only",
            "parameter_scan_used": False,
            "formal_backtest_used_for_discovery": False,
            "accepted": False,
            "live_trading_approved": False,
            "ocf_yield_pre2021_status": evidence_map.get("operating_cash_flow_yield", {}).get("preview_status", ""),
            "ocf_to_np_pre2021_status": evidence_map.get("operating_cash_flow_to_net_profit", {}).get("preview_status", ""),
            "ocf_to_revenue_pre2021_status": evidence_map.get("ocf_to_revenue", {}).get("preview_status", ""),
        }
    ]


def _field_contract() -> list[dict[str, Any]]:
    return [
        {
            "field": "operating_cash_flow_yield",
            "role": "primary_risk_trigger",
            "direction": "higher_better",
            "threshold": "bottom_tercile_within_same_trade_date_highway_sleeve",
            "pit_requirement": "visible_date <= rebalance_trade_date",
            "missing_policy": "needs_data_review_no_auto_cap",
        },
        {
            "field": "operating_cash_flow_to_net_profit",
            "role": "primary_risk_trigger",
            "direction": "higher_better",
            "threshold": "below_median_within_same_trade_date_highway_sleeve",
            "pit_requirement": "visible_date <= rebalance_trade_date",
            "missing_policy": "needs_data_review_no_auto_cap",
        },
        {
            "field": "ocf_to_revenue",
            "role": "audit_tiebreaker_not_v1_trigger",
            "direction": "higher_better",
            "threshold": "record tercile/median only",
            "pit_requirement": "visible_date <= rebalance_trade_date",
            "missing_policy": "audit_only",
        },
        {
            "field": "free_cash_flow_yield",
            "role": "excluded_v1_data_gate_only",
            "direction": "higher_better",
            "threshold": "none",
            "pit_requirement": "original report page/table/unit review",
            "missing_policy": "manual_review_queue",
        },
        {
            "field": "capex_burden",
            "role": "excluded_v1_data_gate_only",
            "direction": "lower_better",
            "threshold": "none",
            "pit_requirement": "original report page/table/unit review",
            "missing_policy": "manual_review_queue",
        },
    ]


def _rule_formula() -> str:
    return """# V5c Highway OCF Risk-Cap Frozen Formula

Rule id: `highway_ocf_yield_quality_guard_v1_risk_cap_only`

Scope:
- Existing `highway_infrastructure` holdings selected by V57f/V5f only.
- No full-market selection.
- No new stock.
- No cross-sleeve transfer.
- No formal backtest discovery.

Inputs:
- `operating_cash_flow_yield`
- `operating_cash_flow_to_net_profit`
- `ocf_to_revenue` for audit only

Risk flag:
```text
flag_ocf_risk =
  operating_cash_flow_yield in same-date highway bottom tercile
  OR operating_cash_flow_to_net_profit below same-date highway median
```

Action:
```text
if flag_ocf_risk and v5f_target_weight > repaired_baseline_target_weight:
    capped_weight = repaired_baseline_target_weight
else:
    capped_weight = v5f_target_weight
```

Any capped excess is redistributed pro-rata only to non-flagged existing highway names in the same sleeve. If there is no eligible receiver, keep original V5f weights and log `no_action`.

This is risk-cap-only. It does not reward strong OCF names directly, does not use capex/FCF, and does not change V57f core.
"""


def _capex_review_queue(capex_panel: list[dict[str, str]], capex_blockers: list[dict[str, str]]) -> list[dict[str, Any]]:
    highway_rows = [row for row in capex_panel if row.get("sector_id") == "highway_infrastructure"]
    missing = [
        row
        for row in highway_rows
        if row.get("capex_fcf_status") != "pass_pit_original_statement_extracted"
        or not row.get("free_cash_flow_yield")
        or not row.get("capex_burden")
    ]
    queue: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in missing:
        key = (row.get("code", ""), row.get("cashflow_report_period", ""))
        if key in seen:
            continue
        seen.add(key)
        queue.append(
            {
                "priority": "P0_sample_review" if len(queue) < 8 else "P1_defer",
                "code": row.get("code", ""),
                "sector_id": row.get("sector_id", ""),
                "report_period": row.get("cashflow_report_period", ""),
                "first_affected_trade_date": row.get("trade_date", ""),
                "capex_fcf_status": row.get("capex_fcf_status", ""),
                "capex_source_pdf": row.get("capex_source_pdf", ""),
                "capex_source_page_number": row.get("capex_source_page_number", ""),
                "review_goal": "confirm original cash-flow statement CFO/capex page/table/unit; do not enter model yet",
                "model_use_allowed": False,
            }
        )
    pdf_missing = [
        row
        for row in capex_blockers
        if row.get("blocker_id") == "financial_report_pdf_unavailable"
        and row.get("code")
        and row.get("code", "").endswith(("XSHG", "XSHE"))
    ]
    for row in pdf_missing:
        if not row.get("code", "").startswith(("600020", "601816")):
            continue
        key = (row.get("code", ""), row.get("report_period", ""))
        if key in seen:
            continue
        seen.add(key)
        queue.append(
            {
                "priority": "P1_defer",
                "code": row.get("code", ""),
                "sector_id": "highway_infrastructure" if row.get("code") == "600020.XSHG" else "port_rail_infrastructure",
                "report_period": row.get("report_period", ""),
                "first_affected_trade_date": "",
                "capex_fcf_status": "source_pdf_missing",
                "capex_source_pdf": "",
                "capex_source_page_number": "",
                "review_goal": "retry source search or provide original report; do not enter model yet",
                "model_use_allowed": False,
            }
        )
    return queue[:16]


def _limited_engineering_readiness(
    spec_summary: dict[str, Any],
    capex_summary: dict[str, Any],
    capex_review_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {"check_id": "spec_admitted", "status": "pass" if spec_summary.get("pm_gate_decision") == "admit_highway_ocf_quality_risk_cap_to_quant_spec_not_accepted" else "fail", "detail": spec_summary.get("pm_gate_decision", "")},
        {"check_id": "rule_is_frozen", "status": "pass", "detail": FROZEN_RULE_ID},
        {"check_id": "risk_cap_only", "status": "pass", "detail": "no positive reward and no new buys"},
        {"check_id": "capex_fcf_excluded_from_v1", "status": "pass", "detail": f"capex gate={capex_summary.get('pm_gate_decision', '')}; review_queue={len(capex_review_queue)}"},
        {"check_id": "sample_split_clean", "status": "pass", "detail": f"{TRAIN_START}_to_{TRAIN_END}_discovery; {FORMAL_START}_to_{FORMAL_END}_reserved"},
        {"check_id": "limited_engineering_allowed", "status": "pass", "detail": "ready to test fixed v1 only; no threshold tuning"},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "v5f_primary_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted", "status": "pass", "detail": False},
        {"audit_id": "live_trading_approved", "status": "pass", "detail": False},
        {"audit_id": "formal_backtest_used_as_discovery", "status": "pass", "detail": False},
        {"audit_id": "parameter_scan_used", "status": "pass", "detail": False},
        {"audit_id": "full_market_selection", "status": "pass", "detail": False},
        {"audit_id": "new_stock_buy_signal", "status": "pass", "detail": False},
        {"audit_id": "cross_sleeve_transfer", "status": "pass", "detail": False},
    ]


def _sidecar_update(sidecar_queue: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for row in sidecar_queue:
        out.append(
            {
                "sector_id": row.get("sector_id", ""),
                "route": row.get("status", row.get("route", "")),
                "updated_status": "continue_sidecar_observation_enhancement_only",
                "next_allowed_action": row.get("allowed_action", ""),
                "blocked_action": row.get("blocked_action", "V57f_core_entry;accepted"),
                "model_backtest_allowed": False,
                "accepted": False,
            }
        )
    return out


def _cycle_update(cycle_queue: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for row in cycle_queue:
        out.append(
            {
                "sector_id": row.get("sector_id", ""),
                "updated_status": "continue_pit_state_data_gate_only",
                "required_state_data": row.get("required_state_data", ""),
                "blocked_action": row.get("blocked_action", "backtest_before_PIT_state_gate"),
                "model_backtest_allowed": False,
                "accepted": False,
            }
        )
    return out


def _pm_decision(readiness: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fail = [row for row in readiness if row["status"] == "fail"]
    decision = "blocked_until_rule_freeze_inputs_repaired" if fail else "freeze_highway_ocf_risk_cap_v1_ready_for_limited_engineering_not_accepted"
    return [
        {
            "pm_gate_decision": decision,
            "frozen_rule_id": FROZEN_RULE_ID,
            "limited_engineering_next": not fail,
            "capex_fcf_model_use": False,
            "sidecar_core_promotion": False,
            "cycle_backtest_allowed": False,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
        }
    ]


def _next_queue(pm_decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ready = str(pm_decision[0].get("limited_engineering_next", "")).lower() == "true"
    return [
        {
            "priority": "P0",
            "task_id": "v5c_highway_ocf_risk_cap_v1_limited_engineering",
            "status": "ready" if ready else "blocked",
            "allowed": "fixed_rule_only_no_threshold_scan",
            "description": "Test frozen risk-cap-only rule against V57f repaired and V5f primary; no acceptance.",
        },
        {
            "priority": "P1",
            "task_id": "v5c_highway_capex_fcf_small_original_page_review",
            "status": "ready",
            "allowed": "manual_review_queue_only_not_model_input",
            "description": "Review a small number of missing/partial original cash-flow pages.",
        },
        {
            "priority": "S1",
            "task_id": "v5c_gas_water_telecom_sidecar_observation_refresh",
            "status": "ready",
            "allowed": "sidecar_observation_only",
            "description": "Continue observation cards and contribution attribution only.",
        },
        {
            "priority": "C1",
            "task_id": "v5c_cycle_sector_pit_state_data_gate_repair",
            "status": "ready",
            "allowed": "data_gate_only_no_backtest",
            "description": "Repair cycle state data before any model test.",
        },
    ]


def _blockers(capex_review_queue: list[dict[str, Any]], readiness: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = [
        {
            "blocker_id": "capex_fcf_not_model_ready",
            "severity": "nonfatal",
            "detail": f"manual review queue rows={len(capex_review_queue)}",
            "required_action": "keep capex/FCF out of v1 risk-cap model",
        }
    ]
    blockers.extend(
        {
            "blocker_id": row["check_id"],
            "severity": "fatal",
            "detail": row["detail"],
            "required_action": "repair failed readiness check",
        }
        for row in readiness
        if row["status"] == "fail"
    )
    return blockers


def _summary(
    status: str,
    blockers: list[dict[str, Any]],
    pm_gate_decision: str = "blocked_missing_required_inputs",
    capex_review_queue_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "task": "v5c_highway_ocf_risk_cap_rule_freeze",
        "status": status,
        "frozen_rule_id": FROZEN_RULE_ID if status != "blocked_missing_required_inputs" else "",
        "train_test_scope_start": TRAIN_START,
        "train_test_scope_end": TRAIN_END,
        "formal_backtest_scope_start": FORMAL_START,
        "formal_backtest_scope_end": FORMAL_END,
        "primary_reference": PRIMARY_REFERENCE,
        "baseline": BASELINE,
        "capex_review_queue_count": capex_review_queue_count,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "formal_backtest_used_as_discovery": False,
        "parameter_scan_used": False,
        "accepted": False,
        "live_trading_approved": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") not in {"fatal", "none"}),
        "pm_gate_decision": pm_gate_decision,
    }


def _report(
    summary: dict[str, Any],
    frozen_rule: list[dict[str, Any]],
    readiness: list[dict[str, Any]],
    capex_review_queue: list[dict[str, Any]],
    pm_decision: list[dict[str, Any]],
    sidecar_update: list[dict[str, Any]],
    cycle_update: list[dict[str, Any]],
) -> str:
    rule = frozen_rule[0]
    lines = [
        "# V5c Highway OCF Risk-Cap Rule Freeze",
        "",
        f"- Status: `{summary['status']}`",
        f"- PM gate: `{pm_decision[0]['pm_gate_decision']}`",
        f"- Frozen rule: `{rule['frozen_rule_id']}`",
        f"- Primary reference: `{PRIMARY_REFERENCE}`",
        f"- Baseline: `{BASELINE}`",
        "- Accepted: `False`",
        "- V57f/V5f modified: `False` / `False`",
        "",
        "## Frozen Rule",
        f"- Trigger: {rule['trigger_condition']}",
        f"- Action: {rule['action']}",
        f"- Redistribution: {rule['redistribution']}",
        f"- Missing data: {rule['missing_data_policy']}",
        "",
        "## Limited Engineering Readiness",
    ]
    for row in readiness:
        lines.append(f"- `{row['check_id']}`: {row['status']} ({row['detail']})")
    lines.extend(["", "## Capex / FCF Review", f"- Small review queue rows: `{len(capex_review_queue)}`", "- Capex/FCF are excluded from v1 model input."])
    lines.extend(["", "## Sidecar", f"- Rows: `{len(sidecar_update)}`; gas/water and telecom remain sidecar observation only."])
    lines.extend(["", "## Cycle Sectors", f"- Rows: `{len(cycle_update)}`; cycle sectors remain PIT state data gate only, no backtest."])
    return "\n".join(lines) + "\n"


def _agent_rules() -> str:
    return """# Agent Execution Rules

- Frozen rule only: `highway_ocf_yield_quality_guard_v1_risk_cap_only`.
- Do not modify V57f core or V5f primary.
- Do not use 2021-05-01 to 2026-05-31 as factor discovery.
- Limited engineering may test this fixed rule only; no threshold scan.
- Capex/FCF remain data-gate/manual-review fields and are excluded from v1.
- Gas/water and telecom remain sidecar observation only.
- Cycle sectors remain PIT data-gate-only; no backtest.
- Do not mark accepted or live approved.
"""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    summary = run_v5c_highway_ocf_risk_cap_rule_freeze(Path(args.root))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
