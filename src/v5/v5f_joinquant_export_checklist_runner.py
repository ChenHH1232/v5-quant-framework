from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_joinquant_export_checklist") / "current"
ROBUSTNESS_DIR = Path("v5f_internal_subsleeve_robustness_packet") / "current"
FORWARD_CONTINUATION_DIR = Path("v5f_forward_continuation_v5g01_closeout") / "current"
PAPER_ARTIFACT_DIR = Path("v5f_paper_workflow_artifacts") / "current"
EXPORT_ROOT = Path("data") / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30"

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"


REQUIRED = [
    ROBUSTNESS_DIR / "v5f_internal_subsleeve_robustness_summary.json",
    ROBUSTNESS_DIR / "v5f_internal_subsleeve_robustness_pm_gate_decision.csv",
    FORWARD_CONTINUATION_DIR / "v5f_forward_continuation_summary.json",
    FORWARD_CONTINUATION_DIR / "v5f_clean_forward_target_audit.csv",
    PAPER_ARTIFACT_DIR / "v5f_paper_artifact_summary.json",
    PAPER_ARTIFACT_DIR / "v5f_handoff_checklist.csv",
]


def run_v5f_joinquant_export_checklist(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (root / EXPORT_ROOT / "historical_platform_attribution").mkdir(parents=True, exist_ok=True)
    (root / EXPORT_ROOT / "forward_clean_targets").mkdir(parents=True, exist_ok=True)

    input_manifest = _input_manifest(root)
    missing = [row for row in input_manifest if row["required"] and not row["exists"]]
    if missing:
        _write_csv(out / "v5f_joinquant_input_manifest.csv", input_manifest)
        _write_csv(out / "v5f_joinquant_blockers.csv", missing)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", missing)
        _write_json(out / "v5f_joinquant_export_checklist_summary.json", summary)
        return summary

    robustness = _read_json(root / ROBUSTNESS_DIR / "v5f_internal_subsleeve_robustness_summary.json")
    robust_gate = _read_csv(root / ROBUSTNESS_DIR / "v5f_internal_subsleeve_robustness_pm_gate_decision.csv")[0]
    forward = _read_json(root / FORWARD_CONTINUATION_DIR / "v5f_forward_continuation_summary.json")
    clean_target_audit = _read_csv(root / FORWARD_CONTINUATION_DIR / "v5f_clean_forward_target_audit.csv")
    paper_artifacts = _read_json(root / PAPER_ARTIFACT_DIR / "v5f_paper_artifact_summary.json")
    handoff = _read_csv(root / PAPER_ARTIFACT_DIR / "v5f_handoff_checklist.csv")

    required_exports = _required_exports()
    field_schema = _field_schema()
    dropzone = _dropzone_manifest(root)
    attribution_plan = _platform_attribution_plan()
    clean_preflight = _clean_target_preflight(clean_target_audit, forward)
    quality_gates = _quality_gates(robustness, robust_gate, forward, paper_artifacts, handoff)
    allowed_blocked = _allowed_blocked_actions()
    decision = _pm_decision(quality_gates, clean_preflight)
    queue = _next_agent_queue(decision[0]["pm_gate_decision"], clean_preflight)
    blockers = _blockers(quality_gates)

    _write_csv(out / "v5f_joinquant_input_manifest.csv", input_manifest)
    _write_csv(out / "v5f_joinquant_required_exports.csv", required_exports)
    _write_csv(out / "v5f_joinquant_export_field_schema.csv", field_schema)
    _write_csv(out / "v5f_joinquant_export_dropzone_manifest.csv", dropzone)
    _write_csv(out / "v5f_joinquant_platform_attribution_plan.csv", attribution_plan)
    _write_csv(out / "v5f_joinquant_clean_target_preflight.csv", clean_preflight)
    _write_csv(out / "v5f_joinquant_export_quality_gates.csv", quality_gates)
    _write_csv(out / "v5f_joinquant_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5f_joinquant_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_joinquant_next_agent_queue.csv", queue)
    _write_csv(out / "v5f_joinquant_blockers.csv", blockers)
    (out / "v5f_joinquant_user_action_checklist.md").write_text(_user_action_checklist(required_exports, dropzone), encoding="utf-8")
    (out / "v5f_joinquant_next_prompt.md").write_text(_next_prompt(queue), encoding="utf-8")
    (out / "v5f_joinquant_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5f_joinquant_export_checklist_report.md").write_text(
        _report(robustness, required_exports, clean_preflight, quality_gates, decision),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5f_joinquant_export_checklist",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        baseline_id=BASELINE,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        local_5min_bar_source_policy="baostock_only",
        joinquant_platform_minute_backtest_allowed=True,
        jqdata_sdk_minute_bar_source_allowed=False,
        platform_backtest_frequency="minute",
        required_export_count=len(required_exports),
        historical_export_count=sum(1 for row in required_exports if row["scope"] == "historical_platform_attribution"),
        forward_export_count=sum(1 for row in required_exports if row["scope"] == "forward_clean_target_population"),
        dropzone_root=str(root / EXPORT_ROOT),
        target_population_status=forward["target_population_status"],
        robustness_gate=robustness["pm_gate_decision"],
    )
    _write_json(out / "v5f_joinquant_export_checklist_summary.json", summary)
    return summary


def _required_exports() -> list[dict[str, Any]]:
    return [
        {
            "export_id": "H01",
            "scope": "historical_platform_attribution",
            "file_name": "daily_returns.csv",
            "required": True,
            "date_range": f"{BACKTEST_START} to {BACKTEST_END}",
            "content": "JoinQuant platform minute-level backtest daily benchmark and strategy returns / NAV for the tested strategy.",
            "why_needed": "Compare platform minute-backtest NAV path against local repaired-baseline evidence.",
        },
        {
            "export_id": "H02",
            "scope": "historical_platform_attribution",
            "file_name": "transactions.csv",
            "required": True,
            "date_range": f"{BACKTEST_START} to {BACKTEST_END}",
            "content": "Minute-backtest order fills with datetime/time if available, code, side, amount, price, value, commission/tax if available.",
            "why_needed": "Diagnose minute fill timing, cost, odd-lot, and order-path differences.",
        },
        {
            "export_id": "H03",
            "scope": "historical_platform_attribution",
            "file_name": "positions.csv",
            "required": True,
            "date_range": f"{BACKTEST_START} to {BACKTEST_END}",
            "content": "Daily or rebalance-date holdings, share amounts, market value, portfolio value, and cash.",
            "why_needed": "Check holdings and cash path against local internal sub-sleeve model.",
        },
        {
            "export_id": "H04",
            "scope": "historical_platform_attribution",
            "file_name": "logs.txt",
            "required": True,
            "date_range": f"{BACKTEST_START} to {BACKTEST_END}",
            "content": "Minute-backtest frequency/config, rebalance selections, blocked orders, warnings, script version, and any runtime exceptions.",
            "why_needed": "Confirm platform run frequency, governance, and execution state; explain platform mismatches.",
        },
        {
            "export_id": "H05",
            "scope": "historical_platform_attribution",
            "file_name": "script_snapshot.py",
            "required": True,
            "date_range": f"{BACKTEST_START} to {BACKTEST_END}",
            "content": "Exact JoinQuant script used for platform run.",
            "why_needed": "Freeze implementation identity; prevent accidental rule drift.",
        },
        {
            "export_id": "F01",
            "scope": "forward_clean_target_population",
            "file_name": "official_repaired_v57f_targets.csv",
            "required": True,
            "date_range": "next clean official V57f rebalance only",
            "content": "Official repaired V57f target rows: rebalance_date, code, sleeve_id, target_weight.",
            "why_needed": "Populate V5f forward/paper target rows without using late/shadow signals.",
        },
        {
            "export_id": "F02",
            "scope": "forward_clean_target_population",
            "file_name": "official_repaired_v57f_signal_log.txt",
            "required": True,
            "date_range": "next clean official V57f rebalance only",
            "content": "Signal generation timestamp, input snapshot, and no-late-signal proof.",
            "why_needed": "Prove PIT-clean forward target availability before paper population.",
        },
    ]


def _field_schema() -> list[dict[str, Any]]:
    return [
        _field("daily_returns.csv", "date", True, "YYYY-MM-DD trading date."),
        _field("daily_returns.csv", "benchmark_return", True, "Daily benchmark return or NAV column accepted by platform attribution parser."),
        _field("daily_returns.csv", "strategy_return", True, "Daily strategy return or NAV column accepted by platform attribution parser."),
        _field("transactions.csv", "trade_datetime_or_trade_date_time", True, "Minute fill timestamp preferred; trade_date plus time is acceptable."),
        _field("transactions.csv", "trade_date", True, "Fill date; can be parsed to YYYY-MM-DD if timestamp is split or unavailable."),
        _field("transactions.csv", "time", False, "Fill time for minute-level attribution when exported separately."),
        _field("transactions.csv", "code", True, "A-share code; raw JoinQuant or normalized code is acceptable."),
        _field("transactions.csv", "side", True, "buy/sell if export supports it; otherwise infer from amount/value signs in attribution step."),
        _field("transactions.csv", "amount", True, "Filled shares."),
        _field("transactions.csv", "price", True, "Fill price."),
        _field("transactions.csv", "commission", False, "Commission if available."),
        _field("positions.csv", "trade_date", True, "Position date."),
        _field("positions.csv", "code", True, "Holding code or JoinQuant target name parsable to code."),
        _field("positions.csv", "amount", True, "Holding shares."),
        _field("positions.csv", "market_value", True, "Position market value."),
        _field("positions.csv", "cash", True, "Cash row or cash field."),
        _field("official_repaired_v57f_targets.csv", "rebalance_date", True, "Clean official future rebalance date."),
        _field("official_repaired_v57f_targets.csv", "code", True, "V57f target code."),
        _field("official_repaired_v57f_targets.csv", "sleeve_id", True, "V57f sleeve id."),
        _field("official_repaired_v57f_targets.csv", "target_weight", True, "Official repaired V57f target weight."),
    ]


def _field(file_name: str, field_name: str, required: bool, description: str) -> dict[str, Any]:
    return {"file_name": file_name, "field_name": field_name, "required": required, "description": description}


def _dropzone_manifest(root: Path) -> list[dict[str, Any]]:
    historical = root / EXPORT_ROOT / "historical_platform_attribution"
    forward = root / EXPORT_ROOT / "forward_clean_targets"
    return [
        {"dropzone_id": "historical_platform_attribution", "path": str(historical), "expected_files": "daily_returns.csv;transactions.csv;positions.csv;logs.txt;script_snapshot.py", "ready_for_user_files": historical.exists()},
        {"dropzone_id": "forward_clean_targets", "path": str(forward), "expected_files": "official_repaired_v57f_targets.csv;official_repaired_v57f_signal_log.txt", "ready_for_user_files": forward.exists()},
    ]


def _platform_attribution_plan() -> list[dict[str, Any]]:
    return [
        {"step": 1, "task": "file_intake", "description": "Confirm all required JoinQuant exports are present in the dropzone.", "joinquant_started_here": False},
        {"step": 2, "task": "encoding_and_schema_parse", "description": "Parse utf-8-sig/gb18030/gbk CSV exports and normalize date/code fields.", "joinquant_started_here": False},
        {"step": 3, "task": "platform_minute_frequency_audit", "description": "Confirm logs/script identify a JoinQuant minute-level platform backtest, not a local JQData minute-bar export.", "joinquant_started_here": False},
        {"step": 4, "task": "daily_nav_attribution", "description": "Compare JoinQuant minute-backtest daily return path against local model NAV through 2026-05-31.", "joinquant_started_here": False},
        {"step": 5, "task": "transaction_attribution", "description": "Compare platform minute fills against local orders; diagnose fill timing, costs, and missing orders.", "joinquant_started_here": False},
        {"step": 6, "task": "position_cash_attribution", "description": "Compare platform positions/cash against local holdings and cash path.", "joinquant_started_here": False},
        {"step": 7, "task": "pm_closeout", "description": "Classify platform differences; do not mark accepted/live approved from attribution alone.", "joinquant_started_here": False},
    ]


def _clean_target_preflight(clean_target_audit: list[dict[str, str]], forward: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in clean_target_audit:
        rows.append(
            {
                "source_id": row["source_id"],
                "rebalance_date": row["rebalance_date"],
                "audit_status": row["audit_status"],
                "clean_forward_usable": row["clean_forward_usable"],
                "use_for_paper_population_now": row["use_for_paper_population_now"],
                "historical_backtest_blocker": row["historical_backtest_blocker"],
                "current_action": "wait" if row["clean_forward_usable"] == "False" else "populate_forward_paper_targets",
                "reason": row["reason"],
            }
        )
    rows.append(
        {
            "source_id": "current_population_state",
            "rebalance_date": "",
            "audit_status": forward["target_population_status"],
            "clean_forward_usable": False,
            "use_for_paper_population_now": False,
            "historical_backtest_blocker": False,
            "current_action": "wait_for_clean_official_repaired_v57f_targets",
            "reason": "Forward target population is not ready yet.",
        }
    )
    return rows


def _quality_gates(
    robustness: dict[str, Any],
    robust_gate: dict[str, str],
    forward: dict[str, Any],
    paper_artifacts: dict[str, Any],
    handoff: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        _gate("robustness_packet_passed", robustness["pm_gate_decision"] == "robustness_packet_pass_continue_forward_paper_not_accepted", robustness["pm_gate_decision"]),
        _gate("primary_candidate_confirmed", robustness["primary_candidate"] == PRIMARY and robust_gate["primary_candidate"] == PRIMARY, robustness["primary_candidate"]),
        _gate("historical_scope_end_20260531", robustness["backtest_end"] == BACKTEST_END, robustness["backtest_end"]),
        _gate("forward_continuation_ready", forward["pm_gate_decision"] == "continue_internal_subsleeve_forward_paper_tracking_v5g01_sealed_secondary", forward["pm_gate_decision"]),
        _gate("paper_artifacts_ready", paper_artifacts["paper_artifact_decision"] == "paper_artifacts_ready_not_deployment_approved", paper_artifacts["paper_artifact_decision"]),
        _gate("handoff_template_exists", len(handoff) >= 1, len(handoff)),
        _gate("accepted_false", not robustness["accepted"] and robust_gate["accepted"] == "False", False),
        _gate("live_trading_approved_false", not robustness["live_trading_approved"] and robust_gate["live_trading_approved"] == "False", False),
        _gate("v57f_core_modified_false", not robustness["v57f_core_modified"] and robust_gate["v57f_core_modified"] == "False", False),
        _gate("threshold_scan_used_false", not robustness["threshold_scan_used"] and robust_gate["threshold_scan_used"] == "False", False),
        _gate("joinquant_not_started", not robustness["joinquant_started"], False),
    ]


def _gate(gate_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"gate_id": gate_id, "status": "pass" if ok else "fail", "detail": detail}


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "prepare_export_checklist", "allowed": True, "blocked": False},
        {"action": "create_local_export_dropzones", "allowed": True, "blocked": False},
        {"action": "run_platform_attribution_after_user_exports", "allowed": True, "blocked": False},
        {"action": "user_runs_joinquant_platform_minute_backtest_for_exports", "allowed": True, "blocked": False},
        {"action": "use_jqdata_sdk_minute_bars_as_local_5min_source", "allowed": False, "blocked": True},
        {"action": "start_joinquant_now", "allowed": False, "blocked": True},
        {"action": "use_202607_late_shadow_signal_as_clean_forward", "allowed": False, "blocked": True},
        {"action": "extend_historical_backtest_beyond_20260531", "allowed": False, "blocked": True},
        {"action": "mark_candidate_accepted", "allowed": False, "blocked": True},
        {"action": "approve_live_trading", "allowed": False, "blocked": True},
        {"action": "modify_v57f_core", "allowed": False, "blocked": True},
        {"action": "scan_momentum_or_mean_reversion_parameters", "allowed": False, "blocked": True},
    ]


def _pm_decision(quality_gates: list[dict[str, Any]], clean_preflight: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gates_ok = all(row["status"] == "pass" for row in quality_gates)
    clean_target_ready = any(row["clean_forward_usable"] in {True, "True"} for row in clean_preflight)
    decision = "joinquant_export_checklist_ready_wait_for_user_exports_not_started" if gates_ok else "blocked_by_checklist_quality_gate"
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": PRIMARY,
            "baseline_id": BASELINE,
            "historical_scope": f"{BACKTEST_START} to {BACKTEST_END}",
            "historical_platform_export_ready_for_user": gates_ok,
            "clean_forward_target_ready_now": clean_target_ready,
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "joinquant_started": False,
        }
    ]


def _next_agent_queue(decision: str, clean_preflight: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean_target_ready = any(row["clean_forward_usable"] in {True, "True"} for row in clean_preflight)
    return [
        {
            "priority": "P0",
            "next_task": "user_runs_joinquant_platform_minute_backtest_and_supplies_exports",
            "allowed_now": decision == "joinquant_export_checklist_ready_wait_for_user_exports_not_started",
            "requires_user_action": True,
            "requires_joinquant": True,
            "status": "waiting_for_user_export_files",
        },
        {
            "priority": "P1",
            "next_task": "run_platform_attribution_after_exports_present",
            "allowed_now": False,
            "requires_user_action": False,
            "requires_joinquant": False,
            "status": "blocked_until_export_files_present",
        },
        {
            "priority": "P2",
            "next_task": "populate_forward_paper_targets_after_clean_official_repaired_v57f_targets",
            "allowed_now": clean_target_ready,
            "requires_user_action": not clean_target_ready,
            "requires_joinquant": clean_target_ready,
            "status": "ready" if clean_target_ready else "waiting_for_clean_official_repaired_v57f_targets",
        },
        {
            "priority": "P3",
            "next_task": "keep_v5g01_secondary_observation_only",
            "allowed_now": True,
            "requires_user_action": False,
            "requires_joinquant": False,
            "status": "sealed_secondary",
        },
    ]


def _blockers(quality_gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in quality_gates if row["status"] != "pass"]
    if failed:
        return [
            {
                "blocker_id": row["gate_id"],
                "severity": "fatal",
                "status": "blocking",
                "description": row["detail"],
            }
            for row in failed
        ]
    return [
        {
            "blocker_id": "user_joinquant_exports_pending",
            "severity": "external_input",
            "status": "not_blocking_local_checklist",
            "description": "Checklist and dropzones are ready; attribution waits for user-supplied JoinQuant exports.",
        }
    ]


def _user_action_checklist(required_exports: list[dict[str, Any]], dropzone: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f JoinQuant Export Checklist",
            "",
            "晚点你能使用聚宽时，只需要导出这些文件并放进下面目录。这里不要求现在启动聚宽。",
            "",
            "## 放置目录",
            *[f"- `{row['dropzone_id']}`: `{row['path']}`" for row in dropzone],
            "",
            "## 必要导出",
            *[f"- `{row['export_id']}` `{row['file_name']}`: {row['content']}" for row in required_exports],
            "",
            "## 边界",
            "- 历史平台归因只覆盖 2021-05-01 到 2026-05-31。",
            "- 2026-05-31 之后只能作为 forward/paper，不进入历史回测。",
            "- late/shadow 2026-07 signal 不能作为 clean official forward target。",
            "- 归因结果不能直接 accepted，也不能 live approved。",
            "",
        ]
    )


def _report(
    robustness: dict[str, Any],
    required_exports: list[dict[str, Any]],
    clean_preflight: list[dict[str, Any]],
    quality_gates: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    historical = [row for row in required_exports if row["scope"] == "historical_platform_attribution"]
    forward = [row for row in required_exports if row["scope"] == "forward_clean_target_population"]
    return "\n".join(
        [
            "# V5f JoinQuant Export Checklist",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Candidate: `{PRIMARY}`",
            f"- Benchmark: `{BASELINE}`",
            f"- Historical scope: `{BACKTEST_START}` to `{BACKTEST_END}`.",
            "- Requested platform frequency: `minute`.",
            "- Local 5min bar source remains `BaoStock only`; JoinQuant platform output is attribution evidence, not a raw-bar source.",
            "- JoinQuant started here: `False`.",
            "- Accepted/live approved: `False`.",
            "",
            "## Why This Exists",
            f"- The robustness packet passed with +{float(robustness['delta_return_pct_points_vs_repaired_baseline']):.2f} pct points versus repaired baseline.",
            "- The next useful external step is JoinQuant platform minute-backtest attribution, but it requires user-supplied exports.",
            "",
            "## Historical Platform Exports",
            *[f"- `{row['file_name']}`: {row['why_needed']}" for row in historical],
            "",
            "## Forward Clean Target Exports",
            *[f"- `{row['file_name']}`: {row['why_needed']}" for row in forward],
            "",
            "## Clean Target Status",
            *[f"- `{row['source_id']}`: {row['audit_status']} | use now: `{row['use_for_paper_population_now']}`" for row in clean_preflight],
            "",
            "## Quality Gates",
            *[f"- `{row['gate_id']}`: {row['status']}" for row in quality_gates],
            "",
            "## Next",
            "- Wait for user-supplied JoinQuant minute-backtest exports, then run platform attribution.",
            "- Populate forward/paper targets only after clean official repaired V57f targets are available.",
            "",
        ]
    )


def _next_prompt(queue: list[dict[str, Any]]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f JoinQuant export intake and platform attribution

任务目标：
当用户把 JoinQuant 导出文件放入 `data\\joinquant_exports\\v5f_internal_subsleeve_mom12_70_30\\` 后，执行平台归因。只做归因和差异审计，不修改 V57f，不标记 accepted，不启动新的参数搜索。

必须先阅读：
- v5f_joinquant_export_checklist\\current\\v5f_joinquant_export_checklist_summary.json
- v5f_joinquant_export_checklist\\current\\v5f_joinquant_required_exports.csv
- v5f_joinquant_export_checklist\\current\\v5f_joinquant_export_field_schema.csv
- v5f_joinquant_export_checklist\\current\\v5f_joinquant_platform_attribution_plan.csv
- v5f_internal_subsleeve_robustness_packet\\current\\v5f_internal_subsleeve_robustness_summary.json

输入目录：
- `data\\joinquant_exports\\v5f_internal_subsleeve_mom12_70_30\\historical_platform_attribution\\`
- `data\\joinquant_exports\\v5f_internal_subsleeve_mom12_70_30\\forward_clean_targets\\`

执行边界：
1. 历史平台归因窗口固定为 2021-05-01 到 2026-05-31。
2. 2026-05-31 之后只允许 forward/paper。
3. late/shadow 2026-07 signal 不得作为 clean forward target。
4. 不得 accepted / live approved / deployment approved。
5. 不得修改 V57f core。
6. 不得扫描参数。

下一步队列：
{json.dumps(queue, ensure_ascii=False, indent=2)}
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f JoinQuant Export Checklist Rules",
            "",
            "- Prepare checklist and local intake paths only.",
            "- Do not start JoinQuant in this task.",
            "- User may run JoinQuant platform minute-level backtest and provide exports.",
            "- Local 5min bar source remains BaoStock only; do not use JQData SDK minute bars as local data.",
            "- Historical attribution ends at 2026-05-31.",
            "- Future clean targets are forward/paper only.",
            "- Do not use late/shadow 2026-07 signal as clean forward evidence.",
            "- Do not mark accepted, live approved, or deployment approved.",
            "- Do not modify V57f core or scan parameters.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    rows = []
    for rel in REQUIRED:
        path = root / rel
        rows.append(
            {
                "path": str(rel),
                "required": True,
                "exists": path.exists(),
                "file_size_bytes": path.stat().st_size if path.exists() else "",
            }
        )
    return rows


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_joinquant_export_checklist",
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
    print(json.dumps(run_v5f_joinquant_export_checklist(Path(".")), ensure_ascii=False, indent=2))
