from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_forward_financial_statement_tracking") / "current"
EXPECTATION_DIR = Path("v5c_financial_statement_expectation_layer") / "current"

EXPECTATION_SUMMARY = EXPECTATION_DIR / "v5c_financial_expectation_summary.json"
EXPECTATION_PANEL = EXPECTATION_DIR / "v5c_financial_expectation_historical_panel.csv"
EXPECTATION_ACCURACY = EXPECTATION_DIR / "v5c_financial_expectation_accuracy_audit.csv"
EXPECTATION_DECISION = EXPECTATION_DIR / "v5c_financial_expectation_pm_gate_decision.csv"


def run_v5c_forward_financial_statement_tracking(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_forward_financial_statement_tracking_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_missing_required_input", blockers)
        _write_json(out / "v5c_forward_financial_statement_tracking_summary.json", summary)
        return summary

    source_summary = _read_json(root / EXPECTATION_SUMMARY)
    panel = _read_csv(root / EXPECTATION_PANEL)
    accuracy = _read_csv(root / EXPECTATION_ACCURACY)
    source_decision = _read_csv(root / EXPECTATION_DECISION)[0]

    source_audit = _source_audit(source_summary, source_decision)
    open_ledger = _open_prediction_ledger(panel, accuracy)
    queue = _report_tracking_queue(open_ledger)
    template = _tracking_template()
    accuracy_context = _accuracy_context(accuracy)
    governance = _governance_audit(open_ledger, source_audit)
    freeze = _weight_confidence_freeze_decision(source_summary, accuracy)
    decision = _pm_gate_decision(governance, open_ledger)
    next_queue = _next_queue(decision[0], freeze[0])
    blockers_out = _blockers(governance, freeze)

    _write_csv(out / "v5c_forward_financial_statement_source_audit.csv", source_audit)
    _write_csv(out / "v5c_forward_financial_statement_prediction_ledger.csv", open_ledger)
    _write_csv(out / "v5c_forward_financial_statement_open_report_queue.csv", queue)
    _write_csv(out / "v5c_forward_financial_statement_tracking_template.csv", template)
    _write_csv(out / "v5c_forward_financial_statement_accuracy_context.csv", accuracy_context)
    _write_csv(out / "v5c_forward_financial_statement_governance_audit.csv", governance)
    _write_csv(out / "v5c_v5f_weight_confidence_freeze_decision.csv", freeze)
    _write_csv(out / "v5c_forward_financial_statement_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_forward_financial_statement_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_forward_financial_statement_tracking_blockers.csv", blockers_out)
    (out / "v5c_forward_financial_statement_tracking_report.md").write_text(
        _report(open_ledger, accuracy_context, freeze, decision, next_queue),
        encoding="utf-8",
    )
    (out / "v5c_forward_financial_statement_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_forward_financial_statement_tracking_packet",
        decision[0]["pm_gate_decision"],
        blockers_out,
        open_prediction_count=len(open_ledger),
        active_prediction_count=sum(1 for row in open_ledger if row["predicted_direction"] in {"improve", "deteriorate"}),
        unknown_prediction_count=sum(1 for row in open_ledger if row["predicted_direction"] == "unknown"),
        open_code_count=len({row["code"] for row in open_ledger}),
        weight_confidence_spec_status=freeze[0]["v5f_weight_confidence_tag_spec_status"],
    )
    _write_json(out / "v5c_forward_financial_statement_tracking_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _open_prediction_ledger(panel: list[dict[str, str]], accuracy: list[dict[str, str]]) -> list[dict[str, Any]]:
    accuracy_map = {(row.get("sleeve_id", ""), row.get("expectation_id", "")): row for row in accuracy}
    latest_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in sorted(panel, key=lambda item: item.get("trade_date", "")):
        latest_by_key[(row.get("code", ""), row.get("expectation_id", ""))] = row

    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(sorted(latest_by_key.values(), key=lambda item: (item.get("sleeve_id", ""), item.get("code", ""), item.get("expectation_id", ""))), start=1):
        acc = accuracy_map.get((row.get("sleeve_id", ""), row.get("expectation_id", "")), {})
        rows.append(
            {
                "tracking_id": f"fin_forward_{idx:06d}",
                "source_expectation_event_id": row.get("expectation_event_id", ""),
                "prediction_record_date": row.get("trade_date", ""),
                "code": row.get("code", ""),
                "sleeve_id": row.get("sleeve_id", ""),
                "expectation_id": row.get("expectation_id", ""),
                "theory_driver": row.get("theory_driver", ""),
                "predicted_direction": row.get("predicted_direction", ""),
                "prediction_confidence": row.get("prediction_confidence", ""),
                "prediction_component_count": row.get("prediction_component_count", ""),
                "historical_all_hit_rate": acc.get("all_hit_rate", ""),
                "historical_active_signal_hit_rate": acc.get("active_signal_hit_rate", ""),
                "expected_next_report_status": "pending_future_visible_report",
                "actual_next_report_direction": "",
                "actual_visible_date": "",
                "closeout_status": "open",
                "allowed_use": "forward_observation_only",
                "trade_impact": "none",
                "weight_impact": "none",
                "accepted": False,
            }
        )
    return rows


def _report_tracking_queue(open_ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in open_ledger:
        grouped.setdefault((row["sleeve_id"], row["expectation_id"]), []).append(row)
    rows = []
    for idx, ((sleeve, expectation_id), group) in enumerate(sorted(grouped.items()), start=1):
        rows.append(
            {
                "queue_id": f"report_closeout_{idx:04d}",
                "sleeve_id": sleeve,
                "expectation_id": expectation_id,
                "open_prediction_count": len(group),
                "active_prediction_count": sum(1 for row in group if row["predicted_direction"] in {"improve", "deteriorate"}),
                "codes": ";".join(sorted({row["code"] for row in group})),
                "closeout_trigger": "next_visible_quarterly_or_annual_report_field_panel_update",
                "allowed_closeout_action": "record_actual_direction_and_hit_miss_only",
                "blocked_action": "no_trade_no_weight_change_no_v5f_status_change",
            }
        )
    return rows


def _tracking_template() -> list[dict[str, Any]]:
    fields = [
        ("tracking_id", "stable id from open ledger"),
        ("actual_visible_date", "date when the next financial statement field becomes PIT-visible"),
        ("actual_next_report_direction", "improve/stable/deteriorate/pending"),
        ("direction_hit", "hit/miss/not_scored"),
        ("source_report_period", "financial report period used for closeout"),
        ("source_file_or_panel", "local file or panel path"),
        ("review_notes", "PM/Quant notes; no trade instruction"),
    ]
    return [{"field_name": name, "description": desc, "required_for_closeout": True} for name, desc in fields]


def _accuracy_context(accuracy: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in accuracy:
        if row.get("expectation_id") == "ALL":
            continue
        rows.append(
            {
                "sleeve_id": row.get("sleeve_id", ""),
                "expectation_id": row.get("expectation_id", ""),
                "historical_scored_count": row.get("scored_count", ""),
                "historical_all_hit_rate": row.get("all_hit_rate", ""),
                "historical_active_signal_count": row.get("active_signal_count", ""),
                "historical_active_signal_hit_rate": row.get("active_signal_hit_rate", ""),
                "allowed_interpretation": "context_only_not_weight_evidence",
            }
        )
    return rows


def _source_audit(summary: dict[str, Any], decision: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "audit_id": "expectation_layer_completed",
            "audit_status": "pass" if summary.get("status") == "completed_financial_statement_expectation_layer" else "fail",
            "observed": summary.get("status", ""),
            "required": True,
        },
        {
            "audit_id": "expectation_layer_observation_admitted",
            "audit_status": "pass" if decision.get("admit_forward_observation") == "True" else "fail",
            "observed": decision.get("pm_gate_decision", ""),
            "required": True,
        },
        {
            "audit_id": "expectation_layer_not_trading",
            "audit_status": "pass" if decision.get("admit_trading_rule") == "False" and decision.get("admit_weight_change") == "False" else "fail",
            "observed": f"trade={decision.get('admit_trading_rule')};weight={decision.get('admit_weight_change')}",
            "required": True,
        },
    ]


def _governance_audit(open_ledger: list[dict[str, Any]], source_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        *source_audit,
        {
            "audit_id": "open_ledger_no_trade_impact",
            "audit_status": "pass" if all(row["trade_impact"] == "none" for row in open_ledger) else "fail",
            "observed": _counter(open_ledger, "trade_impact"),
            "required": True,
        },
        {
            "audit_id": "open_ledger_no_weight_impact",
            "audit_status": "pass" if all(row["weight_impact"] == "none" for row in open_ledger) else "fail",
            "observed": _counter(open_ledger, "weight_impact"),
            "required": True,
        },
        {
            "audit_id": "open_ledger_not_accepted",
            "audit_status": "pass" if all(str(row["accepted"]) == "False" for row in open_ledger) else "fail",
            "observed": _counter(open_ledger, "accepted"),
            "required": True,
        },
    ]


def _weight_confidence_freeze_decision(summary: dict[str, Any], accuracy: list[dict[str, str]]) -> list[dict[str, Any]]:
    overall = next((row for row in accuracy if row.get("expectation_id") == "ALL"), {})
    active_hit = float(overall.get("active_signal_hit_rate", 0.0) or 0.0)
    return [
        {
            "v5f_weight_confidence_tag_spec_status": "blocked_until_forward_or_pre2021_evidence",
            "reason": "active financial expectation signal is not strong enough for any weight discussion",
            "current_active_signal_hit_rate": active_hit,
            "required_before_reopen": "forward closeout or pre2021 extension must show stable active signal usefulness",
            "admit_engineering_backtest_now": False,
            "admit_weight_change_now": False,
            "accepted": False,
            "source_expectation_layer_gate": summary.get("pm_gate_decision", ""),
        }
    ]


def _pm_gate_decision(governance: list[dict[str, Any]], open_ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passed = bool(open_ledger) and all(row["audit_status"] == "pass" for row in governance)
    return [
        {
            "pm_gate_decision": "forward_financial_statement_tracking_open_observation_only" if passed else "forward_financial_statement_tracking_blocked",
            "admit_forward_tracking": str(passed),
            "admit_trading_rule": False,
            "admit_weight_change": False,
            "admit_v5f_weight_confidence_spec": False,
            "accepted": False,
            "live_approved": False,
            "v57f_core_modified": False,
            "v5f_primary_modified": False,
            "next_step": "closeout_when_next_financial_report_visible" if passed else "repair_forward_tracking_dependency",
        }
    ]


def _next_queue(decision: dict[str, Any], freeze: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "future_report_closeout_append",
            "allowed": decision["admit_forward_tracking"],
            "scope": "Append actual next report direction once PIT-visible financial statement fields are refreshed.",
            "blocked_until": "next financial report field panel update",
        },
        {
            "priority": 2,
            "next_gate": "pre2021_financial_expectation_panel_extension",
            "allowed": "True",
            "scope": "Check whether the same expectation logic works before 2021-05-01.",
            "blocked_until": "",
        },
        {
            "priority": 3,
            "next_gate": "v5f_weight_confidence_tag_spec",
            "allowed": "False",
            "scope": "Do not open engineering backtest now.",
            "blocked_until": freeze["required_before_reopen"],
        },
    ]


def _blockers(governance: list[dict[str, Any]], freeze: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    for row in governance:
        if row["audit_status"] != "pass":
            blockers.append(
                {
                    "blocker_id": row["audit_id"],
                    "severity": "fatal",
                    "status": "blocking",
                    "description": "Forward tracking governance dependency failed.",
                }
            )
    if freeze[0]["v5f_weight_confidence_tag_spec_status"].startswith("blocked"):
        blockers.append(
            {
                "blocker_id": "v5f_weight_confidence_tag_spec_not_opened",
                "severity": "nonfatal",
                "status": "intended_block",
                "description": "Weight confidence engineering remains blocked until forward or pre-2021 evidence improves.",
            }
        )
    return blockers


def _report(
    open_ledger: list[dict[str, Any]],
    accuracy_context: list[dict[str, Any]],
    freeze: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
) -> str:
    active = sum(1 for row in open_ledger if row["predicted_direction"] in {"improve", "deteriorate"})
    direction_counts = _counter(open_ledger, "predicted_direction")
    sleeve_counts = _counter(open_ledger, "sleeve_id")
    accuracy_lines = "\n".join(
        f"- {row['sleeve_id']} / {row['expectation_id']}: active hit {float(row['historical_active_signal_hit_rate'] or 0):.2%}"
        for row in accuracy_context
    )
    queue_lines = "\n".join(f"- P{row['priority']} {row['next_gate']}: allowed={row['allowed']}" for row in next_queue)
    return f"""# V5c Forward Financial Statement Tracking

## Scope
This packet records open next-report financial expectation tags. It is observation-only and cannot alter V57f, V5f, orders, or weights.

## Open Ledger
- Open predictions: {len(open_ledger)}
- Active improve/deteriorate predictions: {active}
- Direction distribution: {direction_counts}
- Sleeve distribution: {sleeve_counts}

## Historical Context
{accuracy_lines}

## V5f Weight Confidence Status
- Status: {freeze[0]['v5f_weight_confidence_tag_spec_status']}
- Reason: {freeze[0]['reason']}

## PM Gate
- Decision: {decision[0]['pm_gate_decision']}
- Accepted: false
- Trading impact: none
- Weight impact: none

## Next Queue
{queue_lines}
"""


def _rules() -> str:
    return """# Agent Execution Rules

- Record future financial statement expectations before the next report closeout.
- Close out only after fields are PIT-visible.
- Do not create orders or weight changes.
- Do not open V5f weight-confidence engineering until forward or pre-2021 evidence is stronger.
- Do not mark accepted or live approved.
"""


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [EXPECTATION_SUMMARY, EXPECTATION_PANEL, EXPECTATION_ACCURACY, EXPECTATION_DECISION]
    return [
        {
            "blocker_id": str(path).replace("\\", "/"),
            "severity": "fatal",
            "status": "missing_required_input",
            "description": "Required expectation layer file is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _summary(status: str, gate: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": status,
        "pm_gate_decision": gate,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accepted": False,
        "live_approved": False,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "trade_rule_added": False,
        "weight_change_added": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "blocker_count": len(blockers),
    }
    summary.update(extra)
    return summary


def _counter(rows: list[dict[str, Any]], field: str) -> str:
    counts = Counter(str(row.get(field, "")) for row in rows)
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run_v5c_forward_financial_statement_tracking()
