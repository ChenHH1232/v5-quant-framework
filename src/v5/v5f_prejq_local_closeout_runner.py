from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_prejq_local_closeout") / "current"
ROBUSTNESS_DIR = Path("v5f_internal_subsleeve_robustness_packet") / "current"
STATE_TAG_DIR = Path("v5f_forward_paper_v5c_state_tags") / "current"
CLEAN_TARGET_DIR = Path("v5f_clean_forward_target_population") / "current"
JQ_DIR = Path("v5f_joinquant_export_checklist") / "current"
OVERHEAT_DIR = Path("v5c_overheat_no_new_overweight_limited_engineering") / "current"
V5G_DIR = Path("v5g_vs_midterm_model_comparison") / "current"

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"


REQUIRED = [
    ROBUSTNESS_DIR / "v5f_internal_subsleeve_robustness_summary.json",
    STATE_TAG_DIR / "v5f_v5c_state_tag_summary.json",
    CLEAN_TARGET_DIR / "v5f_clean_forward_target_population_summary.json",
    CLEAN_TARGET_DIR / "v5f_clean_forward_target_blockers.csv",
    JQ_DIR / "v5f_joinquant_export_checklist_summary.json",
    JQ_DIR / "v5f_joinquant_required_exports.csv",
    OVERHEAT_DIR / "v5c_overheat_no_new_overweight_summary.json",
    V5G_DIR / "v5g_vs_midterm_summary.json",
]


def run_v5f_prejq_local_closeout(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    manifest = _input_manifest(root)
    missing = [row for row in manifest if row["required"] and not row["exists"]]
    if missing:
        _write_csv(out / "v5f_prejq_local_closeout_input_manifest.csv", manifest)
        _write_csv(out / "v5f_prejq_local_closeout_blockers.csv", missing)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", missing)
        _write_json(out / "v5f_prejq_local_closeout_summary.json", summary)
        return summary

    robustness = _read_json(root / ROBUSTNESS_DIR / "v5f_internal_subsleeve_robustness_summary.json")
    tags = _read_json(root / STATE_TAG_DIR / "v5f_v5c_state_tag_summary.json")
    clean = _read_json(root / CLEAN_TARGET_DIR / "v5f_clean_forward_target_population_summary.json")
    clean_blockers = _read_csv(root / CLEAN_TARGET_DIR / "v5f_clean_forward_target_blockers.csv")
    jq = _read_json(root / JQ_DIR / "v5f_joinquant_export_checklist_summary.json")
    exports = _read_csv(root / JQ_DIR / "v5f_joinquant_required_exports.csv")
    overheat = _read_json(root / OVERHEAT_DIR / "v5c_overheat_no_new_overweight_summary.json")
    v5g = _read_json(root / V5G_DIR / "v5g_vs_midterm_summary.json")

    component_matrix = _component_matrix(robustness, tags, clean, jq, overheat, v5g)
    external_inputs = _external_input_matrix(clean, clean_blockers, exports, jq)
    model_decision = _model_decision_matrix(robustness, overheat, v5g)
    allowed_blocked = _allowed_blocked_actions()
    governance = _governance(robustness, tags, clean, jq, overheat, v5g)
    decision = _pm_decision(governance, clean, jq)
    queue = _next_queue(clean, jq)
    blockers = _blockers(external_inputs, governance)

    _write_csv(out / "v5f_prejq_local_closeout_input_manifest.csv", manifest)
    _write_csv(out / "v5f_prejq_component_status_matrix.csv", component_matrix)
    _write_csv(out / "v5f_prejq_external_input_matrix.csv", external_inputs)
    _write_csv(out / "v5f_prejq_model_decision_matrix.csv", model_decision)
    _write_csv(out / "v5f_prejq_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5f_prejq_governance_audit.csv", governance)
    _write_csv(out / "v5f_prejq_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_prejq_next_agent_queue.csv", queue)
    _write_csv(out / "v5f_prejq_local_closeout_blockers.csv", blockers)
    (out / "v5f_prejq_next_prompt.md").write_text(_next_prompt(), encoding="utf-8")
    (out / "v5f_prejq_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")
    (out / "v5f_prejq_local_closeout_report.md").write_text(
        _report(robustness, tags, clean, jq, overheat, v5g, decision, external_inputs),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5f_prejq_local_closeout",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        baseline_id=BASELINE,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        v5f_return_pct=robustness["strategy_return_pct"],
        v5f_delta_return_pct_points_vs_repaired_baseline=robustness["delta_return_pct_points_vs_repaired_baseline"],
        v5f_delta_drawdown_pct_points_vs_repaired_baseline=robustness["delta_max_drawdown_pct_points_vs_repaired_baseline"],
        v5c_state_tags_ready=tags["pm_gate_decision"] == "v5c_state_tags_attached_to_v5f_forward_observation_not_trade_rule",
        clean_forward_target_ready=clean["target_ready"],
        joinquant_exports_ready=False,
        external_input_count=len(external_inputs),
        waiting_external_input_count=sum(1 for row in external_inputs if row["status"].startswith("waiting")),
        overheat_guard_status=overheat["pm_gate_decision"],
        v5g_status=v5g["pm_gate_decision"],
        local_work_remaining_without_external_inputs=False,
    )
    _write_json(out / "v5f_prejq_local_closeout_summary.json", summary)
    return summary


def _component_matrix(
    robustness: dict[str, Any],
    tags: dict[str, Any],
    clean: dict[str, Any],
    jq: dict[str, Any],
    overheat: dict[str, Any],
    v5g: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "component": "v5f_primary_candidate",
            "status": "ready_forward_paper_not_accepted",
            "pm_gate": robustness["pm_gate_decision"],
            "role": "primary_candidate",
            "result": f"+{float(robustness['delta_return_pct_points_vs_repaired_baseline']):.4f} pct vs repaired baseline",
            "accepted": False,
        },
        {
            "component": "v5c_state_tags",
            "status": "ready_observe_only",
            "pm_gate": tags["pm_gate_decision"],
            "role": "risk_observation_context",
            "result": f"{tags['seed_tag_rows']} seed tags; {tags['pm_review_queue_rows']} PM review-note rows",
            "accepted": False,
        },
        {
            "component": "v5c_overheat_guard",
            "status": "diagnostic_only",
            "pm_gate": overheat["pm_gate_decision"],
            "role": "do_not_replace_primary",
            "result": f"{float(overheat['candidate_delta_return_pct_points_vs_primary']):.4f} pct vs V5f champion",
            "accepted": False,
        },
        {
            "component": "v5g_new_models",
            "status": "secondary_or_diagnostic",
            "pm_gate": v5g["pm_gate_decision"],
            "role": "not_replacement",
            "result": f"{float(v5g['delta_return_pct_points_vs_midterm_champion']):.4f} pct vs V5f champion",
            "accepted": False,
        },
        {
            "component": "clean_forward_target_population",
            "status": clean["population_status"],
            "pm_gate": clean["pm_gate_decision"],
            "role": "waiting_external_clean_targets",
            "result": f"target_ready={clean['target_ready']}",
            "accepted": False,
        },
        {
            "component": "joinquant_platform_attribution",
            "status": "waiting_user_exports",
            "pm_gate": jq["pm_gate_decision"],
            "role": "platform_replication_next",
            "result": f"{jq['required_export_count']} exports required",
            "accepted": False,
        },
    ]


def _external_input_matrix(
    clean: dict[str, Any],
    clean_blockers: list[dict[str, str]],
    exports: list[dict[str, str]],
    jq: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for blocker in clean_blockers:
        if blocker["blocker_id"] == "none":
            continue
        rows.append(
            {
                "input_id": blocker["blocker_id"],
                "scope": "forward_clean_target_population",
                "file_name": blocker["description"].split(" is ")[0],
                "required": True,
                "status": "waiting_clean_official_repaired_v57f_targets",
                "blocks": "paper_target_population",
                "historical_backtest_blocker": False,
                "reason": blocker["description"],
            }
        )
    for row in exports:
        if row["scope"] == "forward_clean_target_population":
            continue
        rows.append(
            {
                "input_id": row["export_id"],
                "scope": row["scope"],
                "file_name": str(Path(jq["dropzone_root"]) / "historical_platform_attribution" / row["file_name"]),
                "required": row["required"],
                "status": "waiting_user_joinquant_export",
                "blocks": "platform_attribution",
                "historical_backtest_blocker": False,
                "reason": row["why_needed"],
            }
        )
    return rows


def _model_decision_matrix(robustness: dict[str, Any], overheat: dict[str, Any], v5g: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "model_id": PRIMARY,
            "decision": "keep_primary_forward_paper_candidate_not_accepted",
            "return_pct": robustness["strategy_return_pct"],
            "delta_return_pct_points_vs_repaired_baseline": robustness["delta_return_pct_points_vs_repaired_baseline"],
            "delta_return_pct_points_vs_primary": 0.0,
            "accepted": False,
        },
        {
            "model_id": overheat["candidate_id"],
            "decision": "diagnostic_only_do_not_replace",
            "return_pct": overheat["candidate_return_pct"],
            "delta_return_pct_points_vs_repaired_baseline": overheat["candidate_delta_return_pct_points_vs_repaired_baseline"],
            "delta_return_pct_points_vs_primary": overheat["candidate_delta_return_pct_points_vs_primary"],
            "accepted": False,
        },
        {
            "model_id": v5g["best_new_model_id"],
            "decision": "secondary_observation_do_not_replace",
            "return_pct": "",
            "delta_return_pct_points_vs_repaired_baseline": v5g["best_new_delta_return_pct_points_vs_baseline"],
            "delta_return_pct_points_vs_primary": v5g["delta_return_pct_points_vs_midterm_champion"],
            "accepted": False,
        },
    ]


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "continue_v5f_forward_paper_candidate_status", "allowed": True, "blocked": False},
        {"action": "attach_v5c_observe_only_tags_when_targets_available", "allowed": True, "blocked": False},
        {"action": "run_platform_attribution_after_user_exports", "allowed": True, "blocked": False},
        {"action": "populate_paper_targets_without_clean_official_targets", "allowed": False, "blocked": True},
        {"action": "use_late_202607_shadow_signal", "allowed": False, "blocked": True},
        {"action": "promote_v5c_overheat_guard_to_primary", "allowed": False, "blocked": True},
        {"action": "replace_v5f_with_v5g01", "allowed": False, "blocked": True},
        {"action": "mark_accepted_or_live_approved", "allowed": False, "blocked": True},
        {"action": "modify_v57f_core", "allowed": False, "blocked": True},
        {"action": "scan_parameters", "allowed": False, "blocked": True},
    ]


def _governance(
    robustness: dict[str, Any],
    tags: dict[str, Any],
    clean: dict[str, Any],
    jq: dict[str, Any],
    overheat: dict[str, Any],
    v5g: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _audit("v5f_robustness_passed", robustness["pm_gate_decision"] == "robustness_packet_pass_continue_forward_paper_not_accepted", robustness["pm_gate_decision"]),
        _audit("v5c_tags_observe_only_ready", tags["pm_gate_decision"] == "v5c_state_tags_attached_to_v5f_forward_observation_not_trade_rule", tags["pm_gate_decision"]),
        _audit("clean_target_missing_classified_external_input", clean["pm_gate_decision"] == "blocked_waiting_clean_official_repaired_v57f_targets", clean["pm_gate_decision"]),
        _audit("joinquant_exports_waiting_not_started", jq["pm_gate_decision"] == "joinquant_export_checklist_ready_wait_for_user_exports_not_started", jq["pm_gate_decision"]),
        _audit("v5c_overheat_guard_not_replacing", overheat["pm_gate_decision"] == "overheat_no_new_overweight_diagnostic_only_do_not_replace_v5f_champion", overheat["pm_gate_decision"]),
        _audit("v5g_not_replacing_primary", v5g["pm_gate_decision"] == "midterm_internal_subsleeve_champion_remains_primary_v5g_new_models_secondary", v5g["pm_gate_decision"]),
        _audit("historical_scope_end_20260531", robustness["backtest_end"] == BACKTEST_END and clean["backtest_end"] == BACKTEST_END, BACKTEST_END),
        _audit("accepted_false", not robustness["accepted"] and not tags["accepted"] and not clean["accepted"] and not jq["accepted"] and not overheat["accepted"] and not v5g["accepted"], False),
        _audit("live_trading_approved_false", not robustness["live_trading_approved"] and not tags["live_trading_approved"] and not clean["live_trading_approved"] and not jq["live_trading_approved"], False),
        _audit("v57f_core_modified_false", not robustness["v57f_core_modified"] and not tags["v57f_core_modified"] and not clean["v57f_core_modified"] and not jq["v57f_core_modified"] and not overheat["v57f_core_modified"] and not v5g["v57f_core_modified"], False),
        _audit("threshold_scan_used_false", not robustness["threshold_scan_used"] and not tags["threshold_scan_used"] and not clean["threshold_scan_used"] and not jq["threshold_scan_used"] and not overheat["threshold_scan_used"] and not v5g["threshold_scan_used"], False),
        _audit("joinquant_not_started", not robustness["joinquant_started"] and not tags["joinquant_started"] and not clean["joinquant_started"] and not jq["joinquant_started"] and not overheat["joinquant_started"] and not v5g["joinquant_started"], False),
    ]


def _pm_decision(governance: list[dict[str, Any]], clean: dict[str, Any], jq: dict[str, Any]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    return [
        {
            "pm_gate_decision": "prejq_local_closeout_complete_wait_external_inputs" if gov_ok else "blocked_by_prejq_local_governance_issue",
            "primary_candidate": PRIMARY,
            "baseline_id": BASELINE,
            "local_closeout_complete": gov_ok,
            "clean_forward_target_ready": clean["target_ready"],
            "joinquant_exports_ready": False,
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "joinquant_started": False,
        }
    ]


def _next_queue(clean: dict[str, Any], jq: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": "P0",
            "next_task": "provide_clean_official_repaired_v57f_targets_for_2026_10_08",
            "allowed_now": not clean["target_ready"],
            "requires_external_input": True,
            "path": "data\\joinquant_exports\\v5f_internal_subsleeve_mom12_70_30\\forward_clean_targets",
        },
        {
            "priority": "P1",
            "next_task": "provide_joinquant_historical_platform_exports",
            "allowed_now": jq["pm_gate_decision"] == "joinquant_export_checklist_ready_wait_for_user_exports_not_started",
            "requires_external_input": True,
            "path": "data\\joinquant_exports\\v5f_internal_subsleeve_mom12_70_30\\historical_platform_attribution",
        },
        {
            "priority": "P2",
            "next_task": "rerun_clean_forward_target_population_after_files_present",
            "allowed_now": False,
            "requires_external_input": False,
            "path": "v5f_clean_forward_target_population",
        },
        {
            "priority": "P3",
            "next_task": "run_platform_attribution_after_exports_present",
            "allowed_now": False,
            "requires_external_input": False,
            "path": "platform_attribution",
        },
    ]


def _blockers(external_inputs: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [
        {
            "blocker_id": row["input_id"],
            "severity": "external_input",
            "status": row["status"],
            "description": row["file_name"],
        }
        for row in external_inputs
    ]


def _report(
    robustness: dict[str, Any],
    tags: dict[str, Any],
    clean: dict[str, Any],
    jq: dict[str, Any],
    overheat: dict[str, Any],
    v5g: dict[str, Any],
    decision: list[dict[str, Any]],
    external_inputs: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Pre-JQ Local Closeout",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary: `{PRIMARY}`",
            f"- Benchmark: `{BASELINE}`",
            f"- Historical scope: `{BACKTEST_START}` to `{BACKTEST_END}`.",
            "- Accepted/live approved: `False`.",
            "",
            "## Local Model State",
            f"- V5f champion return: `{float(robustness['strategy_return_pct']):.4f}%`.",
            f"- Delta vs repaired baseline: `{float(robustness['delta_return_pct_points_vs_repaired_baseline']):.4f}` pct points.",
            f"- Drawdown delta vs repaired baseline: `{float(robustness['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f}` pct points.",
            "",
            "## Addenda",
            f"- V5c state tags: `{tags['pm_gate_decision']}`, seed tags `{tags['seed_tag_rows']}`.",
            f"- V5c overheat guard: `{overheat['pm_gate_decision']}`, delta vs primary `{float(overheat['candidate_delta_return_pct_points_vs_primary']):.4f}` pct.",
            f"- V5g: `{v5g['pm_gate_decision']}`, best new delta vs primary `{float(v5g['delta_return_pct_points_vs_midterm_champion']):.4f}` pct.",
            "",
            "## External Inputs",
            *[f"- `{row['input_id']}`: {row['status']} | {row['file_name']}" for row in external_inputs],
            "",
            "## Decision",
            "- Local pre-JQ work is complete.",
            "- Do not fabricate clean forward targets.",
            "- Do not use the 2026-07 late/shadow signal.",
            "- Continue only when clean targets or JoinQuant exports are supplied.",
            "",
        ]
    )


def _next_prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f external input intake after pre-JQ local closeout

任务目标：
当 clean official repaired V57f targets 或 JoinQuant historical platform exports 到位后，继续执行对应 intake。当前本地 pre-JQ closeout 已完成，不要再扫参数或开新模型。

必须先阅读：
- v5f_prejq_local_closeout\\current\\v5f_prejq_local_closeout_summary.json
- v5f_prejq_local_closeout\\current\\v5f_prejq_external_input_matrix.csv
- v5f_prejq_local_closeout\\current\\v5f_prejq_next_agent_queue.csv

边界：
1. 不得使用 2026-07 late/shadow signal。
2. 不得修改 V57f。
3. 不得标记 accepted/live approved。
4. 历史回测截止日固定为 2026-05-31。
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Pre-JQ Local Closeout Rules",
            "",
            "- Local pre-JQ work is complete after this packet.",
            "- External inputs are required for target population or platform attribution.",
            "- Do not use late 2026-07 shadow signal.",
            "- Do not modify V57f core.",
            "- Do not scan parameters.",
            "- Do not mark accepted/live/deployment approved.",
            "- Historical scope ends at 2026-05-31.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    rows = []
    for rel in REQUIRED:
        path = root / rel
        rows.append({"path": str(rel), "required": True, "exists": path.exists(), "file_size_bytes": path.stat().st_size if path.exists() else ""})
    return rows


def _audit(audit_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if ok else "fail", "detail": detail}


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_prejq_local_closeout",
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
    print(json.dumps(run_v5f_prejq_local_closeout(Path(".")), ensure_ascii=False, indent=2))
