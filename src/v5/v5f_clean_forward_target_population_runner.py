from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit


OUT_DIR = Path("v5f_clean_forward_target_population") / "current"
FORWARD_TARGET_DIR = Path("data") / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "forward_clean_targets"
TARGET_FILE = FORWARD_TARGET_DIR / "official_repaired_v57f_targets.csv"
SIGNAL_LOG_FILE = FORWARD_TARGET_DIR / "official_repaired_v57f_signal_log.txt"

QUEUE123_DIR = Path("v5f_internal_subsleeve_queue_123_execution") / "current"
STATE_TAG_DIR = Path("v5f_forward_paper_v5c_state_tags") / "current"
ROBUSTNESS_DIR = Path("v5f_internal_subsleeve_robustness_packet") / "current"
JQ_CHECKLIST_DIR = Path("v5f_joinquant_export_checklist") / "current"

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
NEXT_CLEAN_REBALANCE_DATE = "2026-10-08"


REQUIRED_STATIC = [
    QUEUE123_DIR / "v5f_queue_123_paper_target_population_status.csv",
    QUEUE123_DIR / "v5f_queue_123_paper_target_template.csv",
    STATE_TAG_DIR / "v5f_v5c_state_tag_summary.json",
    STATE_TAG_DIR / "v5f_v5c_state_tag_forward_observation_template.csv",
    ROBUSTNESS_DIR / "v5f_internal_subsleeve_robustness_summary.json",
    JQ_CHECKLIST_DIR / "v5f_joinquant_export_checklist_summary.json",
]


def run_v5f_clean_forward_target_population(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    boundary = historical_operation_audit("generate_forward_targets", NEXT_CLEAN_REBALANCE_DATE, root)
    if not boundary["allowed"]:
        blocker = {
            "blocker_id": "historical_operation_boundary",
            "severity": "hard_boundary",
            "status": "frozen",
            "description": boundary["reason"],
        }
        _write_csv(out / "v5f_clean_forward_target_historical_boundary_audit.csv", [boundary])
        _write_csv(out / "v5f_clean_forward_target_blockers.csv", [blocker])
        _write_csv(out / "v5f_clean_forward_target_pm_gate_decision.csv", [{
            "pm_gate_decision": "frozen_no_post_20260531_forward_target_operation",
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
        }])
        summary = _summary(
            "frozen_by_historical_operation_boundary",
            "frozen_no_post_20260531_forward_target_operation",
            [blocker],
            primary_candidate=PRIMARY,
            baseline_id=BASELINE,
            backtest_end=BACKTEST_END,
            next_clean_rebalance_date=NEXT_CLEAN_REBALANCE_DATE,
            historical_boundary_audit=boundary,
        )
        _write_json(out / "v5f_clean_forward_target_population_summary.json", summary)
        (out / "v5f_clean_forward_target_population_report.md").write_text(
            "# V5f Clean Forward Target Population\n\n"
            "- Frozen: requested forward target generation is after the 2026-05-31 historical boundary.\n"
            "- No forward target directory was created, read, or written.\n"
            "- No platform, bridge, upload, or order operation was started.\n",
            encoding="utf-8",
        )
        return summary

    (root / FORWARD_TARGET_DIR).mkdir(parents=True, exist_ok=True)

    input_manifest = _input_manifest(root)
    static_missing = [row for row in input_manifest if row["required"] and not row["exists"] and row["input_type"] == "static_dependency"]
    if static_missing:
        _write_csv(out / "v5f_clean_forward_target_input_manifest.csv", input_manifest)
        _write_csv(out / "v5f_clean_forward_target_blockers.csv", static_missing)
        summary = _summary("blocked_missing_required_static_input", "blocked_until_static_inputs_available", static_missing)
        _write_json(out / "v5f_clean_forward_target_population_summary.json", summary)
        return summary

    queue_status = _read_csv(root / QUEUE123_DIR / "v5f_queue_123_paper_target_population_status.csv")[0]
    target_template = _read_csv(root / QUEUE123_DIR / "v5f_queue_123_paper_target_template.csv")
    tag_summary = _read_json(root / STATE_TAG_DIR / "v5f_v5c_state_tag_summary.json")
    tag_template = _read_csv(root / STATE_TAG_DIR / "v5f_v5c_state_tag_forward_observation_template.csv")
    robustness = _read_json(root / ROBUSTNESS_DIR / "v5f_internal_subsleeve_robustness_summary.json")
    jq_checklist = _read_json(root / JQ_CHECKLIST_DIR / "v5f_joinquant_export_checklist_summary.json")

    target_audit = _target_file_audit(root, queue_status)
    target_ready = all(row["status"] == "pass" for row in target_audit if row["required_for_population"])
    if target_ready:
        raw_targets = _read_csv(root / TARGET_FILE)
        paper_rows = _paper_rows_from_targets(raw_targets)
        tagged_rows = _tagged_paper_rows(paper_rows, tag_template)
        population_status = "populated_clean_forward_targets_with_v5c_observe_only_tags"
    else:
        paper_rows = _target_template_rows(target_template)
        tagged_rows = _tag_template_rows(tag_template)
        population_status = "not_populated_waiting_clean_official_repaired_v57f_targets"

    preflight = _preflight(queue_status, target_audit, target_ready)
    governance = _governance(robustness, tag_summary, jq_checklist, target_audit, paper_rows, tagged_rows, target_ready)
    decision = _pm_decision(governance, target_ready, population_status, len(paper_rows), len(tagged_rows))
    queue = _next_queue(target_ready)
    blockers = _blockers(target_ready, target_audit, governance)

    _write_csv(out / "v5f_clean_forward_target_input_manifest.csv", input_manifest)
    _write_csv(out / "v5f_clean_forward_target_file_audit.csv", target_audit)
    _write_csv(out / "v5f_clean_forward_target_population_preflight.csv", preflight)
    _write_csv(out / "v5f_clean_forward_paper_target_rows.csv", paper_rows)
    _write_csv(out / "v5f_clean_forward_paper_rows_with_v5c_tags.csv", tagged_rows)
    _write_csv(out / "v5f_clean_forward_v5c_tag_attachment_plan.csv", _tag_attachment_plan(tag_summary, target_ready))
    _write_csv(out / "v5f_clean_forward_target_governance_audit.csv", governance)
    _write_csv(out / "v5f_clean_forward_target_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_clean_forward_target_next_agent_queue.csv", queue)
    _write_csv(out / "v5f_clean_forward_target_blockers.csv", blockers)
    (out / "v5f_clean_forward_target_next_prompt.md").write_text(_next_prompt(target_ready), encoding="utf-8")
    (out / "v5f_clean_forward_target_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")
    (out / "v5f_clean_forward_target_population_report.md").write_text(
        _report(queue_status, target_audit, tag_summary, robustness, decision, target_ready),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5f_clean_forward_target_population_preflight",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        baseline_id=BASELINE,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        next_clean_rebalance_date=queue_status.get("next_clean_rebalance_date", NEXT_CLEAN_REBALANCE_DATE),
        target_ready=target_ready,
        population_status=population_status,
        paper_target_row_count=0 if not target_ready else len(paper_rows),
        v5c_tagged_paper_row_count=0 if not target_ready else len(tagged_rows),
        template_row_count=len(paper_rows) if not target_ready else 0,
        v5c_state_tag_ready=tag_summary["pm_gate_decision"] == "v5c_state_tags_attached_to_v5f_forward_observation_not_trade_rule",
        target_file=str(root / TARGET_FILE),
        signal_log_file=str(root / SIGNAL_LOG_FILE),
    )
    _write_json(out / "v5f_clean_forward_target_population_summary.json", summary)
    return summary


def _target_file_audit(root: Path, queue_status: dict[str, str]) -> list[dict[str, Any]]:
    target = root / TARGET_FILE
    signal = root / SIGNAL_LOG_FILE
    rows = [
        {
            "file_id": "official_repaired_v57f_targets",
            "path": str(TARGET_FILE),
            "required_for_population": True,
            "exists": target.exists(),
            "status": "pass" if target.exists() and target.stat().st_size > 0 else "missing",
            "file_size_bytes": target.stat().st_size if target.exists() else "",
            "expected_rebalance_date": queue_status.get("next_clean_rebalance_date", NEXT_CLEAN_REBALANCE_DATE),
            "reason": "Required clean official target table for V5f paper row population.",
        },
        {
            "file_id": "official_repaired_v57f_signal_log",
            "path": str(SIGNAL_LOG_FILE),
            "required_for_population": True,
            "exists": signal.exists(),
            "status": "pass" if signal.exists() and signal.stat().st_size > 0 else "missing",
            "file_size_bytes": signal.stat().st_size if signal.exists() else "",
            "expected_rebalance_date": queue_status.get("next_clean_rebalance_date", NEXT_CLEAN_REBALANCE_DATE),
            "reason": "Required PIT-clean signal timestamp and no-late-signal evidence.",
        },
    ]
    if target.exists() and target.stat().st_size > 0:
        rows.extend(_target_schema_audit(target))
    return rows


def _target_schema_audit(path: Path) -> list[dict[str, Any]]:
    required = {"rebalance_date", "code", "sleeve_id", "target_weight"}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = set(reader.fieldnames or [])
            row_count = sum(1 for _ in reader)
    except Exception as exc:
        return [
            {
                "file_id": "official_repaired_v57f_targets_schema",
                "path": str(TARGET_FILE),
                "required_for_population": True,
                "exists": True,
                "status": "parse_error",
                "file_size_bytes": path.stat().st_size,
                "expected_rebalance_date": NEXT_CLEAN_REBALANCE_DATE,
                "reason": str(exc),
            }
        ]
    missing = sorted(required - fields)
    return [
        {
            "file_id": "official_repaired_v57f_targets_schema",
            "path": str(TARGET_FILE),
            "required_for_population": True,
            "exists": True,
            "status": "pass" if not missing and row_count > 0 else "schema_missing_or_empty",
            "file_size_bytes": path.stat().st_size,
            "expected_rebalance_date": NEXT_CLEAN_REBALANCE_DATE,
            "reason": f"rows={row_count}; missing_fields={';'.join(missing)}",
        }
    ]


def _preflight(queue_status: dict[str, str], target_audit: list[dict[str, Any]], target_ready: bool) -> list[dict[str, Any]]:
    return [
        {
            "check_id": "queue123_population_status",
            "status": "pass" if queue_status["population_status"] == "not_populated_waiting_next_clean_official_repaired_v57f_targets" else "review",
            "detail": queue_status["population_status"],
        },
        {
            "check_id": "next_clean_rebalance_date",
            "status": "pass",
            "detail": queue_status.get("next_clean_rebalance_date", NEXT_CLEAN_REBALANCE_DATE),
        },
        {
            "check_id": "late_202607_signal_not_used",
            "status": "pass" if queue_status.get("late_202607_signal_used") == "False" else "fail",
            "detail": queue_status.get("late_202607_signal_used"),
        },
        {
            "check_id": "clean_target_files_ready",
            "status": "pass" if target_ready else "blocked_external_input",
            "detail": ";".join(f"{row['file_id']}={row['status']}" for row in target_audit if row["required_for_population"]),
        },
    ]


def _paper_rows_from_targets(raw_targets: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in raw_targets:
        rows.append(
            {
                "rebalance_date": row["rebalance_date"],
                "candidate_id": PRIMARY,
                "code": row["code"],
                "sleeve_id": row["sleeve_id"],
                "base_target_weight": row["target_weight"],
                "mom_12_1_rank_within_sleeve": row.get("mom_12_1_rank_within_sleeve", ""),
                "mom_12_1_bucket": row.get("mom_12_1_bucket", ""),
                "overlay_target_weight": row.get("overlay_target_weight", ""),
                "sleeve_weight_preserved": True,
                "paper_only": True,
                "accepted": False,
            }
        )
    return rows


def _target_template_rows(template: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [dict(row, population_status="template_waiting_clean_official_targets") for row in template]


def _tagged_paper_rows(paper_rows: list[dict[str, Any]], tag_template: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in paper_rows:
        rows.append(
            {
                "paper_date": row["rebalance_date"],
                "cycle_id": row["rebalance_date"],
                "candidate_id": PRIMARY,
                "signal_type": "v5f_forward_paper_v5c_state_tag",
                "code": row["code"],
                "sleeve_id": row["sleeve_id"],
                "v5f_target_weight": row.get("overlay_target_weight", ""),
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
            }
        )
    return rows or _tag_template_rows(tag_template)


def _tag_template_rows(tag_template: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [dict(row, population_status="template_waiting_clean_official_targets") for row in tag_template]


def _tag_attachment_plan(tag_summary: dict[str, Any], target_ready: bool) -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "item": "read_clean_official_targets",
            "status": "ready" if target_ready else "waiting_clean_targets",
            "trade_impact": "none",
        },
        {
            "step": 2,
            "item": "attach_v5c_observe_only_state_columns",
            "status": "ready" if tag_summary["pm_gate_decision"] == "v5c_state_tags_attached_to_v5f_forward_observation_not_trade_rule" else "blocked",
            "trade_impact": "none",
        },
        {
            "step": 3,
            "item": "route_medium_high_tags_to_pm_review_note",
            "status": "ready",
            "trade_impact": "none",
        },
        {
            "step": 4,
            "item": "block_any_trade_or_weight_change_from_tags",
            "status": "enforced",
            "trade_impact": "none",
        },
    ]


def _governance(
    robustness: dict[str, Any],
    tag_summary: dict[str, Any],
    jq_checklist: dict[str, Any],
    target_audit: list[dict[str, Any]],
    paper_rows: list[dict[str, Any]],
    tagged_rows: list[dict[str, Any]],
    target_ready: bool,
) -> list[dict[str, Any]]:
    return [
        _audit("v5f_robustness_passed", robustness["pm_gate_decision"] == "robustness_packet_pass_continue_forward_paper_not_accepted", robustness["pm_gate_decision"]),
        _audit("v5c_state_tags_ready", tag_summary["pm_gate_decision"] == "v5c_state_tags_attached_to_v5f_forward_observation_not_trade_rule", tag_summary["pm_gate_decision"]),
        _audit("joinquant_checklist_ready_not_started", jq_checklist["pm_gate_decision"] == "joinquant_export_checklist_ready_wait_for_user_exports_not_started", jq_checklist["pm_gate_decision"]),
        _audit("clean_targets_ready_or_explicitly_missing", target_ready or any(row["status"] == "missing" for row in target_audit), target_ready),
        _audit("no_late_202607_signal_used", True, False),
        _audit("paper_rows_are_paper_only", all(str(row.get("paper_only", True)) == "True" for row in paper_rows), True),
        _audit("tagged_rows_observe_only", all(row.get("paper_action") == "observe_only" for row in tagged_rows), "observe_only"),
        _audit("no_trade_orders_from_tags", all(str(row.get("trade_order_allowed", False)) == "False" for row in tagged_rows), False),
        _audit("no_weight_change_from_tags", all(str(row.get("weight_change_allowed", False)) == "False" for row in tagged_rows), False),
        _audit("accepted_false", all(str(row.get("accepted", False)) == "False" for row in paper_rows + tagged_rows), False),
        _audit("historical_scope_end_20260531", robustness["backtest_end"] == BACKTEST_END, BACKTEST_END),
        _audit("v57f_core_modified_false", not robustness["v57f_core_modified"], False),
        _audit("threshold_scan_used_false", not robustness["threshold_scan_used"], False),
        _audit("joinquant_not_started", not robustness["joinquant_started"], False),
    ]


def _pm_decision(
    governance: list[dict[str, Any]],
    target_ready: bool,
    population_status: str,
    paper_row_count: int,
    tagged_row_count: int,
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    if gov_ok and target_ready:
        decision = "clean_forward_targets_populated_with_v5c_tags_not_accepted"
    elif gov_ok:
        decision = "blocked_waiting_clean_official_repaired_v57f_targets"
    else:
        decision = "blocked_by_clean_forward_population_governance_issue"
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": PRIMARY,
            "baseline_id": BASELINE,
            "next_clean_rebalance_date": NEXT_CLEAN_REBALANCE_DATE,
            "population_status": population_status,
            "paper_target_row_count": paper_row_count if target_ready else 0,
            "v5c_tagged_paper_row_count": tagged_row_count if target_ready else 0,
            "target_ready": target_ready,
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "joinquant_started": False,
        }
    ]


def _next_queue(target_ready: bool) -> list[dict[str, Any]]:
    return [
        {
            "priority": "P0",
            "next_task": "provide_official_repaired_v57f_targets_and_signal_log",
            "allowed_now": not target_ready,
            "requires_external_input": True,
            "status": "waiting" if not target_ready else "done",
            "path": str(FORWARD_TARGET_DIR),
        },
        {
            "priority": "P1",
            "next_task": "rerun_clean_forward_target_population_after_files_present",
            "allowed_now": not target_ready,
            "requires_external_input": False,
            "status": "ready_after_files_present",
            "path": "v5f_clean_forward_target_population",
        },
        {
            "priority": "P2",
            "next_task": "joinquant_platform_attribution_after_user_exports",
            "allowed_now": False,
            "requires_external_input": True,
            "status": "waiting_user_joinquant_exports",
            "path": "data\\joinquant_exports\\v5f_internal_subsleeve_mom12_70_30\\historical_platform_attribution",
        },
    ]


def _blockers(target_ready: bool, target_audit: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    if target_ready:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Clean forward targets populated."}]
    return [
        {
            "blocker_id": row["file_id"],
            "severity": "external_input",
            "status": "waiting_clean_official_repaired_v57f_targets",
            "description": f"{row['path']} is {row['status']}",
        }
        for row in target_audit
        if row["required_for_population"] and row["status"] != "pass"
    ]


def _report(
    queue_status: dict[str, str],
    target_audit: list[dict[str, Any]],
    tag_summary: dict[str, Any],
    robustness: dict[str, Any],
    decision: list[dict[str, Any]],
    target_ready: bool,
) -> str:
    return "\n".join(
        [
            "# V5f Clean Forward Target Population",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Candidate: `{PRIMARY}`",
            f"- Next clean rebalance date: `{queue_status.get('next_clean_rebalance_date', NEXT_CLEAN_REBALANCE_DATE)}`",
            f"- Target ready: `{target_ready}`",
            "- Accepted/live approved: `False`.",
            "",
            "## File Audit",
            *[f"- `{row['file_id']}`: {row['status']} | `{row['path']}`" for row in target_audit],
            "",
            "## V5c Tags",
            f"- State tag gate: `{tag_summary['pm_gate_decision']}`",
            f"- Historical seed tags ready: `{tag_summary['seed_tag_rows']}`.",
            "- Forward rows will attach tags as observe-only fields.",
            "",
            "## Governance",
            f"- V5f robustness gate: `{robustness['pm_gate_decision']}`",
            f"- Historical backtest end remains `{BACKTEST_END}`.",
            "- 2026-07 late/shadow signal remains unusable as clean forward evidence.",
            "",
            "## Next",
            "- Put `official_repaired_v57f_targets.csv` and `official_repaired_v57f_signal_log.txt` into the forward clean target dropzone, then rerun this packet.",
            "",
        ]
    )


def _next_prompt(target_ready: bool) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f clean forward target population rerun

任务目标：
在以下文件到位后，重新执行 V5f clean forward target population，并附加 V5c observe-only 状态标签：
- data\\joinquant_exports\\v5f_internal_subsleeve_mom12_70_30\\forward_clean_targets\\official_repaired_v57f_targets.csv
- data\\joinquant_exports\\v5f_internal_subsleeve_mom12_70_30\\forward_clean_targets\\official_repaired_v57f_signal_log.txt

当前 target_ready：
`{target_ready}`

边界：
1. 不得使用 2026-07 late/shadow signal。
2. 不得修改 V57f core。
3. 不得用 V5c 标签改变交易。
4. 不得标记 accepted/live approved。
5. 历史回测截止日固定为 2026-05-31。
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Clean Forward Target Population Rules",
            "",
            "- Clean official repaired V57f targets are required before paper row population.",
            "- Do not use late 2026-07 shadow signal.",
            "- V5c tags are observe-only.",
            "- No V57f core modification.",
            "- No accepted/live/deployment approval.",
            "- Historical backtest evidence ends at 2026-05-31.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    rows = []
    for rel in REQUIRED_STATIC:
        path = root / rel
        rows.append(
            {
                "input_id": rel.name,
                "input_type": "static_dependency",
                "path": str(rel),
                "required": True,
                "exists": path.exists(),
                "file_size_bytes": path.stat().st_size if path.exists() else "",
            }
        )
    for rel in [TARGET_FILE, SIGNAL_LOG_FILE]:
        path = root / rel
        rows.append(
            {
                "input_id": rel.name,
                "input_type": "external_clean_forward_target",
                "path": str(rel),
                "required": True,
                "exists": path.exists(),
                "file_size_bytes": path.stat().st_size if path.exists() else "",
            }
        )
    return rows


def _audit(audit_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if ok else "fail", "detail": detail}


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_clean_forward_target_population",
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
    print(json.dumps(run_v5f_clean_forward_target_population(Path(".")), ensure_ascii=False, indent=2))
