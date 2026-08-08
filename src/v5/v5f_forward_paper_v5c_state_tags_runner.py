from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_forward_paper_v5c_state_tags") / "current"
PREJQ_DIR = Path("v5f_prejq_v5c_v5g_integration") / "current"
OVERHEAT_ENGINEERING_DIR = Path("v5c_overheat_no_new_overweight_limited_engineering") / "current"
PAPER_ARTIFACT_DIR = Path("v5f_paper_workflow_artifacts") / "current"
JQ_CHECKLIST_DIR = Path("v5f_joinquant_export_checklist") / "current"

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"


REQUIRED = [
    PREJQ_DIR / "v5f_prejq_v5c_v5g_integration_summary.json",
    PREJQ_DIR / "v5c_v5f_forward_observe_only_tags.csv",
    PREJQ_DIR / "v5c_v5f_state_active_weight_audit.csv",
    OVERHEAT_ENGINEERING_DIR / "v5c_overheat_no_new_overweight_summary.json",
    PAPER_ARTIFACT_DIR / "v5f_paper_artifact_summary.json",
    PAPER_ARTIFACT_DIR / "v5f_daily_paper_signal_log_template.csv",
    PAPER_ARTIFACT_DIR / "v5f_governance_audit_log_template.csv",
    JQ_CHECKLIST_DIR / "v5f_joinquant_export_checklist_summary.json",
]


def run_v5f_forward_paper_v5c_state_tags(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    manifest = _input_manifest(root)
    missing = [row for row in manifest if row["required"] and not row["exists"]]
    if missing:
        _write_csv(out / "v5f_v5c_state_tag_input_manifest.csv", manifest)
        _write_csv(out / "v5f_v5c_state_tag_blockers.csv", missing)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", missing)
        _write_json(out / "v5f_v5c_state_tag_summary.json", summary)
        return summary

    prejq = _read_json(root / PREJQ_DIR / "v5f_prejq_v5c_v5g_integration_summary.json")
    overheat = _read_json(root / OVERHEAT_ENGINEERING_DIR / "v5c_overheat_no_new_overweight_summary.json")
    paper = _read_json(root / PAPER_ARTIFACT_DIR / "v5f_paper_artifact_summary.json")
    jq_checklist = _read_json(root / JQ_CHECKLIST_DIR / "v5f_joinquant_export_checklist_summary.json")
    seed_tags_raw = _read_csv(root / PREJQ_DIR / "v5c_v5f_forward_observe_only_tags.csv")
    state_audit = _read_csv(root / PREJQ_DIR / "v5c_v5f_state_active_weight_audit.csv")
    paper_template = _read_csv(root / PAPER_ARTIFACT_DIR / "v5f_daily_paper_signal_log_template.csv")
    governance_template = _read_csv(root / PAPER_ARTIFACT_DIR / "v5f_governance_audit_log_template.csv")

    schema = _tag_schema()
    seed_tags = _seed_tags(seed_tags_raw)
    observation_template = _forward_observation_template(paper_template, governance_template)
    by_sleeve = _watch_summary_by_sleeve(seed_tags)
    by_rebalance = _watch_summary_by_rebalance(seed_tags)
    review_queue = _pm_review_queue(seed_tags)
    governance = _governance(prejq, overheat, paper, jq_checklist, seed_tags, state_audit, observation_template)
    allowed_blocked = _allowed_blocked_actions()
    decision = _pm_decision(governance, seed_tags, review_queue)
    queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers = _blockers(governance)

    _write_csv(out / "v5f_v5c_state_tag_input_manifest.csv", manifest)
    _write_csv(out / "v5f_v5c_state_tag_schema.csv", schema)
    _write_csv(out / "v5f_v5c_state_tag_historical_seed.csv", seed_tags)
    _write_csv(out / "v5f_v5c_state_tag_forward_observation_template.csv", observation_template)
    _write_csv(out / "v5f_v5c_state_tag_watch_summary_by_sleeve.csv", by_sleeve)
    _write_csv(out / "v5f_v5c_state_tag_watch_summary_by_rebalance.csv", by_rebalance)
    _write_csv(out / "v5f_v5c_state_tag_pm_review_queue.csv", review_queue)
    _write_csv(out / "v5f_v5c_state_tag_governance_audit.csv", governance)
    _write_csv(out / "v5f_v5c_state_tag_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5f_v5c_state_tag_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_v5c_state_tag_next_agent_queue.csv", queue)
    _write_csv(out / "v5f_v5c_state_tag_blockers.csv", blockers)
    (out / "v5f_v5c_state_tag_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5f_v5c_state_tag_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")
    (out / "v5f_v5c_state_tag_report.md").write_text(
        _report(prejq, overheat, seed_tags, by_sleeve, by_rebalance, review_queue, decision),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5f_forward_paper_v5c_state_tags",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        baseline_id=BASELINE,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        seed_tag_rows=len(seed_tags),
        unique_seed_rebalance_dates=len({row["source_historical_rebalance_date"] for row in seed_tags}),
        unique_codes=len({row["code"] for row in seed_tags}),
        unique_sleeves=len({row["sleeve_id"] for row in seed_tags}),
        pm_review_queue_rows=len(review_queue),
        trade_order_allowed_count=sum(1 for row in seed_tags if row["trade_order_allowed"]),
        weight_change_allowed_count=sum(1 for row in seed_tags if row["weight_change_allowed"]),
        overheat_engineering_gate=overheat["pm_gate_decision"],
        joinquant_export_status=jq_checklist["pm_gate_decision"],
    )
    _write_json(out / "v5f_v5c_state_tag_summary.json", summary)
    return summary


def _tag_schema() -> list[dict[str, Any]]:
    return [
        _field("paper_date", True, "Future forward/paper date. Blank in historical seed rows."),
        _field("candidate_id", True, "V5f candidate id; currently internal_subsleeve_mom12_70_30."),
        _field("code", True, "Holding code from repaired V57f/V5f pool."),
        _field("sleeve_id", True, "Original V57f sleeve id."),
        _field("v5f_target_weight", True, "V5f champion target weight for context only."),
        _field("v5f_weight_delta", True, "V5f active weight delta for context only."),
        _field("valuation_state", True, "V5c valuation tag."),
        _field("crowding_state", True, "V5c liquidity/crowding tag."),
        _field("sleeve_overheat_state", True, "V5c sleeve overheat/cooldown tag."),
        _field("broad_trend_state", True, "V5c broad trend tag."),
        _field("allowed_action", True, "Must remain record_observe_only_tag."),
        _field("trade_order_allowed", True, "Must be false."),
        _field("weight_change_allowed", True, "Must be false."),
        _field("accepted", True, "Must be false."),
    ]


def _field(name: str, required: bool, description: str) -> dict[str, Any]:
    return {"field_name": name, "required": required, "description": description}


def _seed_tags(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for index, row in enumerate(rows, start=1):
        severity = _severity(row)
        out.append(
            {
                "tag_id": f"v5f_v5c_seed_{index:05d}",
                "template_id": row["template_id"],
                "paper_date": row["paper_date"],
                "source_historical_rebalance_date": row["source_historical_rebalance_date"],
                "candidate_id": row["candidate_id"],
                "code": row["code"],
                "sleeve_id": row["sleeve_id"],
                "v5f_target_weight": _float(row["v5f_target_weight"]),
                "v5f_weight_delta": _float(row["v5f_weight_delta"]),
                "active_direction": "overweight" if _float(row["v5f_weight_delta"]) > 0 else "underweight" if _float(row["v5f_weight_delta"]) < 0 else "neutral",
                "valuation_state": row["valuation_state"],
                "crowding_state": row["crowding_state"],
                "sleeve_overheat_state": row["sleeve_overheat_state"],
                "broad_trend_state": row["broad_trend_state"],
                "risk_tag_severity": severity,
                "pm_review_required": severity in {"high", "medium"},
                "allowed_action": "record_observe_only_tag",
                "trade_order_allowed": False,
                "weight_change_allowed": False,
                "cash_raise_allowed": False,
                "cross_sleeve_transfer_allowed": False,
                "accepted": False,
            }
        )
    return out


def _severity(row: dict[str, str]) -> str:
    if row["sleeve_overheat_state"] == "valuation_price_flow_overheat_watch":
        return "high"
    if row["sleeve_overheat_state"] in {"valuation_overheat_watch", "cooldown_or_stress_watch"}:
        return "medium"
    if row["crowding_state"] != "normal" or row["valuation_state"] == "valuation_overheat_watch":
        return "low"
    return "info"


def _forward_observation_template(
    paper_template: list[dict[str, str]],
    governance_template: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "paper_date": "",
            "cycle_id": "",
            "candidate_id": PRIMARY,
            "signal_type": "v5f_forward_paper_v5c_state_tag",
            "code": "",
            "sleeve_id": "",
            "v5f_target_weight": "",
            "v5f_weight_delta": "",
            "valuation_state": "",
            "crowding_state": "",
            "sleeve_overheat_state": "",
            "broad_trend_state": "",
            "risk_tag_severity": "",
            "paper_action": "observe_only",
            "execution_proxy": "none",
            "trade_order_allowed": False,
            "weight_change_allowed": False,
            "cash_raise_allowed": False,
            "accepted": False,
            "source_template_fields": ";".join(paper_template[0].keys()) if paper_template else "",
            "source_governance_fields": ";".join(governance_template[0].keys()) if governance_template else "",
        }
    ]


def _watch_summary_by_sleeve(seed_tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sleeve in sorted({row["sleeve_id"] for row in seed_tags}):
        group = [row for row in seed_tags if row["sleeve_id"] == sleeve]
        rows.append(_summary_row({"sleeve_id": sleeve}, group))
    return rows


def _watch_summary_by_rebalance(seed_tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for date in sorted({row["source_historical_rebalance_date"] for row in seed_tags}):
        group = [row for row in seed_tags if row["source_historical_rebalance_date"] == date]
        rows.append(_summary_row({"source_historical_rebalance_date": date}, group))
    return rows


def _summary_row(prefix: dict[str, Any], group: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        **prefix,
        "tag_count": len(group),
        "high_count": sum(1 for row in group if row["risk_tag_severity"] == "high"),
        "medium_count": sum(1 for row in group if row["risk_tag_severity"] == "medium"),
        "low_count": sum(1 for row in group if row["risk_tag_severity"] == "low"),
        "overweight_tag_count": sum(1 for row in group if row["active_direction"] == "overweight"),
        "underweight_tag_count": sum(1 for row in group if row["active_direction"] == "underweight"),
        "pm_review_required_count": sum(1 for row in group if row["pm_review_required"]),
        "trade_impact": "none",
        "accepted": False,
    }


def _pm_review_queue(seed_tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [row for row in seed_tags if row["pm_review_required"]]
    rows = []
    for index, row in enumerate(selected, start=1):
        rows.append(
            {
                "review_id": f"v5f_v5c_review_{index:04d}",
                "source_tag_id": row["tag_id"],
                "source_historical_rebalance_date": row["source_historical_rebalance_date"],
                "candidate_id": row["candidate_id"],
                "code": row["code"],
                "sleeve_id": row["sleeve_id"],
                "risk_tag_severity": row["risk_tag_severity"],
                "valuation_state": row["valuation_state"],
                "crowding_state": row["crowding_state"],
                "sleeve_overheat_state": row["sleeve_overheat_state"],
                "broad_trend_state": row["broad_trend_state"],
                "allowed_pm_action": "record_review_note_only",
                "blocked_pm_action": "trade_order_or_weight_change",
                "status": "seed_for_future_forward_review",
                "accepted": False,
            }
        )
    return rows


def _governance(
    prejq: dict[str, Any],
    overheat: dict[str, Any],
    paper: dict[str, Any],
    jq_checklist: dict[str, Any],
    seed_tags: list[dict[str, Any]],
    state_audit: list[dict[str, str]],
    observation_template: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _audit("prejq_integration_passed", prejq["pm_gate_decision"] == "prejq_v5c_v5g_integration_pass_observe_only_and_overheat_candidate_ready", prejq["pm_gate_decision"]),
        _audit("overheat_guard_diagnostic_only", overheat["pm_gate_decision"] == "overheat_no_new_overweight_diagnostic_only_do_not_replace_v5f_champion", overheat["pm_gate_decision"]),
        _audit("paper_artifacts_ready", paper["paper_artifact_decision"] == "paper_artifacts_ready_not_deployment_approved", paper["paper_artifact_decision"]),
        _audit("joinquant_waiting_not_started", jq_checklist["pm_gate_decision"] == "joinquant_export_checklist_ready_wait_for_user_exports_not_started", jq_checklist["pm_gate_decision"]),
        _audit("seed_tags_available", len(seed_tags) > 0, len(seed_tags)),
        _audit("state_join_rows_available", len(state_audit) == prejq["joined_stock_rebalance_rows"], len(state_audit)),
        _audit("candidate_id_locked", all(row["candidate_id"] == PRIMARY for row in seed_tags), PRIMARY),
        _audit("observe_only_action_locked", all(row["allowed_action"] == "record_observe_only_tag" for row in seed_tags), "record_observe_only_tag"),
        _audit("no_trade_orders_from_tags", all(not row["trade_order_allowed"] for row in seed_tags + observation_template), False),
        _audit("no_weight_change_from_tags", all(not row["weight_change_allowed"] for row in seed_tags + observation_template), False),
        _audit("no_cash_raise_from_tags", all(not row["cash_raise_allowed"] for row in seed_tags + observation_template), False),
        _audit("accepted_false", all(not row["accepted"] for row in seed_tags + observation_template), False),
        _audit("v57f_core_modified_false", not prejq["v57f_core_modified"] and not overheat["v57f_core_modified"], False),
        _audit("threshold_scan_used_false", not prejq["threshold_scan_used"] and not overheat["threshold_scan_used"], False),
        _audit("historical_scope_end_20260531", prejq["backtest_end"] == BACKTEST_END and overheat["backtest_end"] == BACKTEST_END, BACKTEST_END),
    ]


def _audit(audit_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if ok else "fail", "detail": detail}


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "attach_v5c_state_tags_to_forward_paper_rows", "allowed": True, "blocked": False},
        {"action": "record_pm_review_note_for_medium_high_tags", "allowed": True, "blocked": False},
        {"action": "change_v5f_weight_from_v5c_tag", "allowed": False, "blocked": True},
        {"action": "sell_stock_from_v5c_overheat_tag", "allowed": False, "blocked": True},
        {"action": "raise_cash_from_v5c_tag", "allowed": False, "blocked": True},
        {"action": "promote_overheat_guard_to_primary", "allowed": False, "blocked": True},
        {"action": "mark_accepted_or_live_approved", "allowed": False, "blocked": True},
        {"action": "start_joinquant", "allowed": False, "blocked": True},
    ]


def _pm_decision(
    governance: list[dict[str, Any]],
    seed_tags: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    return [
        {
            "pm_gate_decision": "v5c_state_tags_attached_to_v5f_forward_observation_not_trade_rule"
            if gov_ok
            else "blocked_by_v5c_state_tag_governance_issue",
            "primary_candidate": PRIMARY,
            "baseline_id": BASELINE,
            "seed_tag_rows": len(seed_tags),
            "pm_review_queue_rows": len(review_queue),
            "observe_only_forward_ready": gov_ok,
            "trade_path_changed": False,
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "joinquant_started": False,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    ready = decision == "v5c_state_tags_attached_to_v5f_forward_observation_not_trade_rule"
    return [
        {
            "priority": "P0",
            "next_task": "wait_for_clean_official_repaired_v57f_targets_and_populate_v5f_paper_rows_with_v5c_tags",
            "allowed_now": False,
            "requires_external_input": True,
            "status": "waiting_clean_forward_targets",
        },
        {
            "priority": "P1",
            "next_task": "joinquant_platform_attribution_after_user_exports",
            "allowed_now": False,
            "requires_external_input": True,
            "status": "waiting_user_joinquant_exports",
        },
        {
            "priority": "P2",
            "next_task": "continue_v5f_primary_forward_candidate_status",
            "allowed_now": ready,
            "requires_external_input": False,
            "status": "ready",
        },
        {
            "priority": "P3",
            "next_task": "do_not_promote_v5c_overheat_guard_to_primary",
            "allowed_now": ready,
            "requires_external_input": False,
            "status": "done_diagnostic_only",
        },
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if not failed:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "V5c state tags are ready for observe-only V5f forward/paper use."}]
    return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]


def _report(
    prejq: dict[str, Any],
    overheat: dict[str, Any],
    seed_tags: list[dict[str, Any]],
    by_sleeve: list[dict[str, Any]],
    by_rebalance: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    top_sleeve = max(by_sleeve, key=lambda row: row["tag_count"])
    top_rebalance = max(by_rebalance, key=lambda row: row["tag_count"])
    return "\n".join(
        [
            "# V5f Forward/Paper V5c State Tags",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Candidate: `{PRIMARY}`",
            f"- Historical seed scope: `{BACKTEST_START}` to `{BACKTEST_END}`.",
            "- Trade impact: `none`.",
            "- Accepted/live approved: `False`.",
            "",
            "## Seed Tags",
            f"- Seed tag rows: `{len(seed_tags)}`.",
            f"- PM review queue rows: `{len(review_queue)}`.",
            f"- Top sleeve by tag count: `{top_sleeve['sleeve_id']}` ({top_sleeve['tag_count']}).",
            f"- Top rebalance by tag count: `{top_rebalance['source_historical_rebalance_date']}` ({top_rebalance['tag_count']}).",
            "",
            "## Upstream Decisions",
            f"- Pre-JQ integration: `{prejq['pm_gate_decision']}`.",
            f"- Overheat guard engineering: `{overheat['pm_gate_decision']}`.",
            "- Overheat guard stays diagnostic and does not replace V5f champion.",
            "",
            "## Forward Use",
            "- Attach V5c state fields to future V5f paper rows when clean official repaired V57f targets are available.",
            "- Medium/high tags route to PM review note only.",
            "- No orders, weight changes, cash raises, or acceptance can be generated from these tags.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f clean forward target population with V5c observe-only state tags

任务目标：
当 clean official repaired V57f targets 可用时，为 `internal_subsleeve_mom12_70_30` 填充 forward/paper 目标行，并附加 V5c valuation/crowding/overheat observe-only 标签。

来源 gate：
`{decision["pm_gate_decision"]}`

必须先阅读：
- v5f_forward_paper_v5c_state_tags\\current\\v5f_v5c_state_tag_summary.json
- v5f_forward_paper_v5c_state_tags\\current\\v5f_v5c_state_tag_forward_observation_template.csv
- v5f_joinquant_export_checklist\\current\\v5f_joinquant_export_checklist_summary.json

禁止事项：
1. 不得用 V5c 标签改变交易。
2. 不得单股卖出或加仓。
3. 不得 raise cash。
4. 不得修改 V57f。
5. 不得标记 accepted/live approved。
6. 不得把 2026-05-31 之后作为历史回测。
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Forward/Paper V5c State Tag Rules",
            "",
            "- V5c state tags are observe-only.",
            "- Tags may route PM review notes but cannot create orders.",
            "- No V57f core modification.",
            "- No V5f weight change from state tags.",
            "- No accepted/live/deployment approval.",
            "- Historical scope remains 2021-05-01 to 2026-05-31.",
            "- JoinQuant waits for user exports.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    rows = []
    for rel in REQUIRED:
        path = root / rel
        rows.append({"path": str(rel), "required": True, "exists": path.exists(), "file_size_bytes": path.stat().st_size if path.exists() else ""})
    return rows


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_forward_paper_v5c_state_tags",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "engineering_backtest_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }
    payload.update(extra)
    return payload


def _float(value: Any) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
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
    print(json.dumps(run_v5f_forward_paper_v5c_state_tags(Path(".")), ensure_ascii=False, indent=2))
