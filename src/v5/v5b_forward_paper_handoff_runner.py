from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file


DEFAULT_STATUS_REGISTRY = Path("docs/governance/status_registry.json")
DEFAULT_V5_SCOPE_SUMMARY = Path("v5_scope_closeout/current/v5_scope_closeout_summary.json")
DEFAULT_V5_FINAL_STATUS = Path("v5_scope_closeout/current/v5_final_candidate_status.csv")
DEFAULT_V5_SCOPE_QUEUE = Path("v5_scope_closeout/current/v5_scope_next_queue.csv")
DEFAULT_GOVERNANCE_SUMMARY = Path("enhanced_etf_governance_v5/current/enhanced_etf_governance_summary.json")
DEFAULT_GOVERNANCE_REPORT = Path("enhanced_etf_governance_v5/current/enhanced_etf_governance_report.md")
DEFAULT_PRODUCTION_SUMMARY = Path("enhanced_etf_production_lines_v5/current/production_line_summary.json")
DEFAULT_PROMOTION_SUMMARY = Path("enhanced_etf_production_lines_v5/current/sleeve_promotion_summary.json")
DEFAULT_PROMOTION_QUEUE = Path("enhanced_etf_production_lines_v5/current/sleeve_promotion_queue.csv")
DEFAULT_ALL_CANDIDATES_SUMMARY = Path("sector_extension_all_candidates_v5/current/all_candidates_execution_summary.json")
DEFAULT_ALL_CANDIDATES_STATUS = Path("sector_extension_all_candidates_v5/current/all_candidates_status_matrix.csv")
DEFAULT_EXECUTION_ROBUSTNESS = Path("execution_robustness_v57f/current/execution_robustness_summary.json")
DEFAULT_OUT_DIR = Path("v5b_forward_paper_handoff/current")

SCOPE_FIELDS = ["scope_id", "scope_area", "allowed_actions", "forbidden_actions", "owner", "gate", "evidence"]
PRIORITY_FIELDS = [
    "priority",
    "sector_id",
    "v5_final_status",
    "v5b_lane",
    "allowed_v5b_action",
    "blocked_action",
    "required_before_progress",
    "can_join_v57f_core",
    "can_change_v57f",
    "evidence_primary",
]
BLOCKED_FIELDS = ["blocked_action_id", "scope", "blocked_action", "reason", "trigger_to_reconsider"]
INPUT_FIELDS = ["input_id", "required_for", "input_name", "required_files_or_fields", "provided_by", "blocks_until_supplied"]


@dataclass(frozen=True)
class V5bForwardPaperHandoffResult:
    output_dir: Path
    summary_json: Path
    report_md: Path
    scope_table_csv: Path
    candidate_priority_queue_csv: Path
    blocked_actions_csv: Path
    required_external_inputs_csv: Path
    agent_execution_rules_md: Path
    status: str


def build_v5b_forward_paper_handoff(
    *,
    status_registry: Path = DEFAULT_STATUS_REGISTRY,
    v5_scope_summary: Path = DEFAULT_V5_SCOPE_SUMMARY,
    v5_final_status: Path = DEFAULT_V5_FINAL_STATUS,
    v5_scope_queue: Path = DEFAULT_V5_SCOPE_QUEUE,
    governance_summary: Path = DEFAULT_GOVERNANCE_SUMMARY,
    governance_report: Path = DEFAULT_GOVERNANCE_REPORT,
    production_summary: Path = DEFAULT_PRODUCTION_SUMMARY,
    promotion_summary: Path = DEFAULT_PROMOTION_SUMMARY,
    promotion_queue: Path = DEFAULT_PROMOTION_QUEUE,
    all_candidates_summary: Path = DEFAULT_ALL_CANDIDATES_SUMMARY,
    all_candidates_status: Path = DEFAULT_ALL_CANDIDATES_STATUS,
    execution_robustness: Path = DEFAULT_EXECUTION_ROBUSTNESS,
    out_dir: Path = DEFAULT_OUT_DIR,
    as_of_date: str = "2026-07-25",
) -> V5bForwardPaperHandoffResult:
    required_paths = [
        status_registry,
        v5_scope_summary,
        v5_final_status,
        v5_scope_queue,
        governance_summary,
        governance_report,
        production_summary,
        promotion_summary,
        promotion_queue,
        all_candidates_summary,
        all_candidates_status,
        execution_robustness,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required handoff inputs: " + "; ".join(missing))

    status_payload = _read_json(status_registry)
    scope_payload = _read_json(v5_scope_summary)
    governance_payload = _read_json(governance_summary)
    production_payload = _read_json(production_summary)
    promotion_payload = _read_json(promotion_summary)
    all_candidates_payload = _read_json(all_candidates_summary)
    robustness_payload = _read_json(execution_robustness)
    final_rows = read_csv_rows_if_exists(v5_final_status)
    promotion_rows = read_csv_rows_if_exists(promotion_queue)
    candidate_rows = read_csv_rows_if_exists(all_candidates_status)
    scope_queue_rows = read_csv_rows_if_exists(v5_scope_queue)
    governance_report_text = governance_report.read_text(encoding="utf-8-sig")

    v57f = _v57f_summary(production_payload, scope_payload, robustness_payload)
    scope_rows = _scope_rows(
        v57f=v57f,
        scope_payload=scope_payload,
        governance_payload=governance_payload,
        robustness_payload=robustness_payload,
        production_summary=production_summary,
        execution_robustness=execution_robustness,
    )
    priority_rows = _priority_rows(final_rows, promotion_rows, candidate_rows)
    blocked_rows = _blocked_rows()
    required_inputs = _required_external_inputs()
    status = "v5_frozen_handoff_v5b_forward_paper_scope_ready"

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "v5b_forward_paper_handoff_summary.json"
    report_md = out_dir / "v5b_forward_paper_handoff_report.md"
    scope_table_csv = out_dir / "v5b_forward_scope_table.csv"
    candidate_priority_queue_csv = out_dir / "v5b_candidate_priority_queue.csv"
    blocked_actions_csv = out_dir / "v5b_blocked_actions.csv"
    required_external_inputs_csv = out_dir / "v5b_required_external_inputs.csv"
    agent_execution_rules_md = out_dir / "v5b_agent_execution_rules.md"

    write_csv_rows(scope_table_csv, SCOPE_FIELDS, scope_rows, encoding="utf-8-sig")
    write_csv_rows(candidate_priority_queue_csv, PRIORITY_FIELDS, priority_rows, encoding="utf-8-sig")
    write_csv_rows(blocked_actions_csv, BLOCKED_FIELDS, blocked_rows, encoding="utf-8-sig")
    write_csv_rows(required_external_inputs_csv, INPUT_FIELDS, required_inputs, encoding="utf-8-sig")
    agent_execution_rules_md.write_text(_agent_rules_md(), encoding="utf-8")

    summary = {
        "schema_version": 1,
        "project": "v5b_forward_paper_handoff",
        "experiment_layer": "handoff_scope",
        "status": status,
        "as_of_date": as_of_date,
        "v5_final_state": {
            "status": scope_payload.get("status"),
            "scope_end_date": scope_payload.get("scope_end_date"),
            "scope_rule": scope_payload.get("scope_rule"),
            "future_signal_policy": "future/paper signals belong to V5b, not frozen V5",
        },
        "v57f": v57f,
        "v5b_first_priority": {
            "sector_id": "gas_water_operators",
            "action": "paper tracking / sidecar evidence only; do not add to V57f",
        },
        "highest_value_next_action": "JoinQuant platform attribution after user supplies daily returns, transactions, positions and logs.",
        "execution_timing_decision": {
            "status": robustness_payload.get("status"),
            "decision": robustness_payload.get("decision"),
            "variant_count": robustness_payload.get("variant_count"),
            "stable_positive_excess_variant_count": robustness_payload.get("stable_positive_excess_variant_count"),
            "pm_interpretation": "Execution timing robustness is complete; do not continue minute-level timing optimization.",
        },
        "counts": {
            "status_registry_strategy_count": len(status_payload.get("strategies", [])),
            "candidate_priority_count": len(priority_rows),
            "blocked_action_count": len(blocked_rows),
            "required_external_input_count": len(required_inputs),
            "scope_queue_rows": len(scope_queue_rows),
            "governance_report_chars": len(governance_report_text),
            "all_candidates_count": all_candidates_payload.get("candidate_count"),
            "promotion_candidate_count": promotion_payload.get("candidate_count"),
        },
        "outputs": {
            "report_md": str(report_md),
            "scope_table_csv": str(scope_table_csv),
            "candidate_priority_queue_csv": str(candidate_priority_queue_csv),
            "blocked_actions_csv": str(blocked_actions_csv),
            "required_external_inputs_csv": str(required_external_inputs_csv),
            "agent_execution_rules_md": str(agent_execution_rules_md),
        },
        "input_paths": {name: str(path) for name, path in {
            "status_registry": status_registry,
            "v5_scope_summary": v5_scope_summary,
            "v5_final_status": v5_final_status,
            "v5_scope_queue": v5_scope_queue,
            "governance_summary": governance_summary,
            "governance_report": governance_report,
            "production_summary": production_summary,
            "promotion_summary": promotion_summary,
            "promotion_queue": promotion_queue,
            "all_candidates_summary": all_candidates_summary,
            "all_candidates_status": all_candidates_status,
            "execution_robustness": execution_robustness,
        }.items()},
        "pm_rules": [
            "V57f remains frozen and cannot be modified by V5b.",
            "V5b may track future paper / forward / sidecar evidence only.",
            "Observation sleeves cannot enter V57f without a separate PM stage gate.",
            "Historical return alone cannot promote any sleeve.",
            "JoinQuant platform replication waits for user-supplied exports.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, summary)
    report_md.write_text(_report_md(summary, scope_rows, priority_rows, required_inputs), encoding="utf-8")

    return V5bForwardPaperHandoffResult(
        output_dir=out_dir,
        summary_json=summary_json,
        report_md=report_md,
        scope_table_csv=scope_table_csv,
        candidate_priority_queue_csv=candidate_priority_queue_csv,
        blocked_actions_csv=blocked_actions_csv,
        required_external_inputs_csv=required_external_inputs_csv,
        agent_execution_rules_md=agent_execution_rules_md,
        status=status,
    )


def _v57f_summary(production: dict[str, Any], scope: dict[str, Any], robustness: dict[str, Any]) -> dict[str, Any]:
    daily = production.get("evidence", {}).get("daily_summary", {})
    metrics = daily.get("metrics", {})
    order = daily.get("rebalance_order_health", {})
    return {
        "strategy_id": production.get("strategy_id", "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"),
        "status": "formal ETF candidate / frozen mainline",
        "not_status": ["accepted_strategy", "live_trading_approved", "platform_replication_passed"],
        "active_core_sleeves": production.get("active_sleeves", []),
        "local_engineering_window_end": scope.get("scope_end_date", "2026-05-31"),
        "metrics": {
            "strategy_return": metrics.get("strategy_return"),
            "annualized_return": metrics.get("annualized_return"),
            "benchmark_return": metrics.get("benchmark_return"),
            "excess_return": metrics.get("excess_return"),
            "max_drawdown": metrics.get("max_drawdown"),
            "sharpe": metrics.get("sharpe"),
            "information_ratio": metrics.get("information_ratio"),
            "strategy_volatility": metrics.get("strategy_volatility"),
        },
        "rebalance_order_health": order,
        "execution_robustness": {
            "status": robustness.get("status"),
            "decision": robustness.get("decision"),
            "stable_positive_excess_variant_count": robustness.get("stable_positive_excess_variant_count"),
            "variant_count": robustness.get("variant_count"),
        },
    }


def _scope_rows(
    *,
    v57f: dict[str, Any],
    scope_payload: dict[str, Any],
    governance_payload: dict[str, Any],
    robustness_payload: dict[str, Any],
    production_summary: Path,
    execution_robustness: Path,
) -> list[dict[str, str]]:
    return [
        _scope("v5_frozen_allowed", "V5 frozen mainline allowed", "Read evidence; generate handoff packets; prepare JoinQuant attribution intake checklist", "Change V57f sleeves, weights, factors, rebalance logic, timing, or tune historical returns", "PM / Engineering", "scope_closed_2026_05_31", str(production_summary)),
        _scope("v5_frozen_forbidden", "V5 frozen mainline forbidden", "None beyond evidence refresh / attribution preparation", "Wait for or generate 2026-10 signal inside V5; mark accepted; mark live approved; add observation sleeves", "All agents", "hard_block", str(scope_payload.get("outputs", {}).get("final_status_csv", ""))),
        _scope("v5b_allowed", "V5b forward / paper / sidecar allowed", "Track future paper records; collect sidecar evidence; monitor observation sleeves; build non-mutating reports", "Rewrite V5 freeze; alter V57f core; promote by return alone", "V5b PM / Research / Engineering", "v5b_scope_only", "v5b_forward_paper_handoff/current/v5b_forward_scope_table.csv"),
        _scope("external_inputs_required", "External-input actions", "Run JoinQuant platform attribution after user supplies exports", "Invent platform data or infer missing transaction/position/log files", "User + Engineering", "wait_for_user_exports", "v5b_forward_paper_handoff/current/v5b_required_external_inputs.csv"),
        _scope("execution_timing", "Execution timing policy", "Use robustness packet as evidence that timing is not fragile", "Continue minute-level timing optimization or choose a variant by historical return", "Engineering", "completed_not_tuning", str(execution_robustness)),
        _scope("v57f_current_state", "V57f frozen status", f"Keep core sleeves {','.join(v57f.get('active_core_sleeves', []))}; formal candidate only", "Accepted strategy / live trading approved / platform replication passed claims", "PM", "formal_candidate_not_accepted", str(production_summary)),
        _scope("paper_runner_scope", "Paper runner scope", str(governance_payload.get("paper_runner_note", "Future paper belongs to separate workflow.")), "Treat paper runner as V5 frozen-mainline next step", "V5b agents", "outside_v5_inside_v5b", str(DEFAULT_GOVERNANCE_SUMMARY)),
    ]


def _priority_rows(final_rows: list[dict[str, str]], promotion_rows: list[dict[str, str]], candidate_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    final_by_id = {row.get("candidate_id", ""): row for row in final_rows}
    promo_by_id = {row.get("sector_id", ""): row for row in promotion_rows}
    candidate_by_id = {row.get("sector_id", ""): row for row in candidate_rows}
    order = [
        ("1", "gas_water_operators", "paper_tracking_sidecar", "Paper tracking / sidecar evidence only; do not add to V57f.", "none beyond V5b scope setup"),
        ("2", "home_appliances", "observation_drawdown_review", "Observation only; review drawdown and state risk.", "drawdown review / no core promotion"),
        ("3", "telecom_operators", "capped_specialist_observation", "Capped / specialist observation; small-sample policy.", "small sample policy"),
        ("4", "oil_gas_pipeline_integrated", "data_gate_repair", "Repair inventory/demand and pipeline-policy state data before Engineering.", "cycle/state data gate"),
        ("5", "insurance", "specialist_order_health", "Standardize order-health and specialist policy before any paper route.", "specialist policy and order-health"),
        ("6", "consumer_staples_cashflow", "research_repair", "Repair source/PIT contract and convert research signal to Quant-ready hypothesis.", "research source contract"),
        ("7", "food_beverage", "archived_in_v5", "Archived / paused inside V5; restart only with new hypothesis and repaired 2021 PIT.", "V5 PM tradability decision failed"),
        ("8", "coal", "archived_or_paused", "Archived / paused; do not reopen without official cycle data gate repair.", "cycle data gate failed"),
    ]
    rows: list[dict[str, str]] = []
    for priority, sector, lane, action, requirement in order:
        final = final_by_id.get(sector, {})
        promo = promo_by_id.get(sector, {})
        candidate = candidate_by_id.get(sector, {})
        rows.append(
            {
                "priority": priority,
                "sector_id": sector,
                "v5_final_status": final.get("v5_final_status", "archived_or_not_in_final_status"),
                "v5b_lane": lane,
                "allowed_v5b_action": action,
                "blocked_action": "modify_V57f;promote_by_historical_return;start_joinquant_without_user_exports;tune_historical_parameters",
                "required_before_progress": requirement,
                "can_join_v57f_core": "no",
                "can_change_v57f": "no",
                "evidence_primary": final.get("evidence_primary") or candidate.get("primary_evidence") or promo.get("pm_note", ""),
            }
        )
    return rows


def _blocked_rows() -> list[dict[str, str]]:
    return [
        _blocked("B01", "V57f", "Modify core sleeves, weights, factors, rebalance logic or trade timing.", "Frozen formal ETF candidate; changes would create a new strategy.", "Separate PM-approved new strategy fork."),
        _blocked("B02", "V5", "Wait for or generate 2026-10 signal inside frozen V5.", "V5 evidence window ends 2026-05-31; future signals belong to V5b.", "Run V5b paper workflow only."),
        _blocked("B03", "V5b", "Add observation sleeves to V57f core silently.", "Observation evidence cannot rewrite frozen mainline.", "Separate PM stage gate plus non-return evidence."),
        _blocked("B04", "V5/V5b", "Tune by 2021-2026 historical return.", "Historical return alone is not acceptance evidence.", "New ex-ante hypothesis and validation contract."),
        _blocked("B05", "Platform", "Claim platform_replication_passed without JoinQuant exports.", "Platform attribution requires daily returns, trades, positions and logs.", "User supplies all required exports."),
        _blocked("B06", "Execution", "Continue minute-level timing optimization.", "Execution robustness completed; timing not fragile.", "Only revisit if real platform attribution shows timing-specific mismatch."),
        _blocked("B07", "Status", "Mark accepted_strategy or live_trading_approved.", "Forward/platform evidence is incomplete.", "Separate acceptance and live approval gates."),
    ]


def _required_external_inputs() -> list[dict[str, str]]:
    return [
        _input("E01", "JoinQuant platform attribution", "Daily return export", "result CSV with daily strategy and benchmark returns through the tested window", "User", "platform_replication"),
        _input("E02", "JoinQuant platform attribution", "Transaction export", "transaction.csv with order fills, price, amount, side, commission / tax if available", "User", "platform_replication"),
        _input("E03", "JoinQuant platform attribution", "Position export", "position.csv with daily holdings, cash / market value if available", "User", "platform_replication"),
        _input("E04", "JoinQuant platform attribution", "Log export", "log.txt with rebalance selections, blocked trades, guard messages and script version", "User", "platform_replication"),
        _input("E05", "Live / real trading approval", "Explicit user approval and account/trading constraints", "capital, risk limits, execution venue, compliance constraints", "User", "live_trading_approved"),
        _input("E06", "External data repair", "Supplier/manual research data", "Only when repairing oil/gas inventory/pipeline policy or insurance specialist fields", "User / Research", "data_gate_repair"),
    ]


def _agent_rules_md() -> str:
    return """# V5b Agent Execution Rules

## Operating Mode

Agents should run by stage gate, not by ordinary-step approval. Do not ask the user after a normal read, validation, report generation, or non-mutating refresh.

## V5 Boundary

- V5 is frozen at local Engineering / JoinQuant-aligned evidence through 2026-05-31.
- V5b may track future paper, forward, and sidecar evidence.
- V5b cannot modify V57f or promote observation sleeves into V57f core.

## Allowed Without Asking

- Read current governance packets.
- Generate non-mutating reports, dashboards, status tables, and sidecar diagnostics.
- Validate whether required external files exist.
- Classify blockers according to existing PM rules.

## Must Ask User

- JoinQuant daily return, transaction, position, or log exports are required.
- Any action would modify V57f core sleeves, weights, factors, rebalance logic, or execution timing.
- Any action would start live trading, platform trading, or external network data acquisition.
- Local files materially contradict the governance conclusion that V57f is frozen, not accepted, and not live approved.

## Stop Rules

- Stop and produce a blocker packet if the same required external input is missing.
- Stop if an agent would need to tune historical returns to proceed.
- Stop if a sleeve would be promoted based only on historical performance.

## Preferred Next Work

The highest-value V5b action is JoinQuant platform attribution once user exports are supplied. Until then, keep observation sleeves in sidecar / paper scope only.
"""


def _report_md(summary: dict[str, Any], scope_rows: list[dict[str, str]], priority_rows: list[dict[str, str]], required_inputs: list[dict[str, str]]) -> str:
    v57f = summary["v57f"]
    metrics = v57f["metrics"]
    lines = [
        "# V5 Frozen Handoff + V5b Forward / Paper Scope",
        "",
        f"- Status: `{summary['status']}`",
        f"- V5 scope end: `{summary['v5_final_state']['scope_end_date']}`",
        f"- V5 final rule: {summary['v5_final_state']['scope_rule']}",
        f"- V57f status: `{v57f['status']}`",
        f"- V57f not status: `{';'.join(v57f['not_status'])}`",
        f"- Core sleeves: `{';'.join(v57f['active_core_sleeves'])}`",
        f"- Strategy return: `{metrics.get('strategy_return')}`",
        f"- Max drawdown: `{metrics.get('max_drawdown')}`",
        f"- Information ratio: `{metrics.get('information_ratio')}`",
        "",
        "## Main Decision",
        "",
        "V57f remains the frozen formal ETF candidate. It is not an accepted strategy, not live-trading approved, and not platform-replication passed. V5b is a new forward / paper / sidecar scope that may collect future evidence without changing V57f.",
        "",
        "The highest-value next action is JoinQuant platform attribution after user exports are supplied. It is higher value than continuing to expand industries.",
        "",
        "Execution timing robustness is already complete; minute-level timing optimization should not continue unless platform attribution reveals a timing-specific mismatch.",
        "",
        "## Scope Table",
        "",
        "| Scope | Area | Allowed | Forbidden | Gate |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in scope_rows:
        lines.append(f"| `{row['scope_id']}` | {row['scope_area']} | {row['allowed_actions']} | {row['forbidden_actions']} | `{row['gate']}` |")
    lines.extend(["", "## V5b Candidate Priority Queue", "", "| Priority | Sector | Lane | Allowed V5b Action | Required Before Progress |", "| ---: | --- | --- | --- | --- |"])
    for row in priority_rows:
        lines.append(f"| {row['priority']} | `{row['sector_id']}` | `{row['v5b_lane']}` | {row['allowed_v5b_action']} | {row['required_before_progress']} |")
    lines.extend(["", "## Required External Inputs", "", "| Input | Required For | Blocks |", "| --- | --- | --- |"])
    for row in required_inputs:
        lines.append(f"| {row['input_name']} | {row['required_for']} | `{row['blocks_until_supplied']}` |")
    lines.extend(["", "## Agent Rule Summary", "", "- Do not ask after ordinary steps.", "- Ask only for JoinQuant exports, V57f core changes, live/platform trading, external network acquisition, or material governance conflicts.", "- Never promote by historical return alone.", "- Never modify V57f from V5b."])
    return "\n".join(lines) + "\n"


def _scope(scope_id: str, area: str, allowed: str, forbidden: str, owner: str, gate: str, evidence: str) -> dict[str, str]:
    return {
        "scope_id": scope_id,
        "scope_area": area,
        "allowed_actions": allowed,
        "forbidden_actions": forbidden,
        "owner": owner,
        "gate": gate,
        "evidence": evidence,
    }


def _blocked(blocked_id: str, scope: str, action: str, reason: str, trigger: str) -> dict[str, str]:
    return {
        "blocked_action_id": blocked_id,
        "scope": scope,
        "blocked_action": action,
        "reason": reason,
        "trigger_to_reconsider": trigger,
    }


def _input(input_id: str, required_for: str, name: str, fields: str, provider: str, blocks: str) -> dict[str, str]:
    return {
        "input_id": input_id,
        "required_for": required_for,
        "input_name": name,
        "required_files_or_fields": fields,
        "provided_by": provider,
        "blocks_until_supplied": blocks,
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}
