from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.agent_loop_packet_runner import create_agent_loop_packet
from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_STRATEGY_ID = "home_appliances_ocf_quality_v5a5c"
DEFAULT_FORMAL_SUMMARY = (
    Path("validation_formal_v5a5d_home_appliances_true_state")
    / DEFAULT_STRATEGY_ID
    / "formal_validation_summary.json"
)
DEFAULT_STATE_DIAGNOSTIC = (
    Path("validation_state_v5a5d_home_appliances")
    / "home_appliances_ocf_quality_v5a5d"
    / "state_diagnostic_summary.json"
)
DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "home_appliances_state_gate_v5a5d" / "panel_with_home_appliances_state_gate.csv"
DEFAULT_PRICE_CSV = DEFAULT_PROCESSED_DIR / "home_appliances_v5a5_joinquant_real_daily_prices.csv"
DEFAULT_DIVIDEND_CSV = DEFAULT_PROCESSED_DIR / "home_appliances_v5a5_joinquant_cash_dividends.csv"
DEFAULT_BENCHMARK_CSV = DEFAULT_PROCESSED_DIR / "home_appliances_v5a5_joinquant_real_benchmark_prices.csv"
DEFAULT_OUT_DIR = Path("home_appliances_engineering_gates_v5a5e")
DEFAULT_PACKET_DIR = Path("agent_loop_packets_v5a5") / "home_appliances_engineering_gate"

FLOW_FIELDS = ["stage", "owner", "input", "action", "output", "gate", "status"]
CHECK_FIELDS = ["check", "status", "detail"]
QUEUE_FIELDS = ["queue_rank", "sector_id", "owner", "task", "input_artifacts", "output_artifacts", "gate", "blocked_actions"]


@dataclass(frozen=True)
class HomeAppliancesEngineeringGateResult:
    output_dir: Path
    flow_table_csv: Path
    health_check_csv: Path
    engineering_queue_csv: Path
    summary_json: Path
    report_path: Path
    agent_packet_json: Path
    status: str
    next_gate: str


def build_home_appliances_engineering_gate(
    *,
    strategy_id: str = DEFAULT_STRATEGY_ID,
    formal_summary: Path = DEFAULT_FORMAL_SUMMARY,
    state_diagnostic: Path = DEFAULT_STATE_DIAGNOSTIC,
    panel_csv: Path = DEFAULT_PANEL,
    price_csv: Path = DEFAULT_PRICE_CSV,
    dividend_csv: Path = DEFAULT_DIVIDEND_CSV,
    benchmark_csv: Path = DEFAULT_BENCHMARK_CSV,
    out_dir: Path = DEFAULT_OUT_DIR,
    agent_packet_dir: Path = DEFAULT_PACKET_DIR,
) -> HomeAppliancesEngineeringGateResult:
    formal = _read_json(formal_summary)
    state = _read_json(state_diagnostic)
    data_health = _data_health(panel_csv, price_csv, dividend_csv, benchmark_csv)
    policy = _state_policy(formal, state)
    checks = _build_checks(formal, state, data_health, policy)
    status, next_gate = _status_and_gate(checks)
    flow_rows = _flow_rows(strategy_id, status)
    queue_rows = _engineering_queue(strategy_id) if status == "engineering_handoff_ready_local_daily_only" else []

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    flow_table_csv = out / "home_appliances_engineering_gate_flow_table.csv"
    health_check_csv = out / "home_appliances_engineering_gate_health_check.csv"
    engineering_queue_csv = out / "home_appliances_engineering_queue.csv"
    summary_json = out / "home_appliances_engineering_gate_summary.json"
    report_path = out / "home_appliances_engineering_gate_report.md"

    write_csv_rows(flow_table_csv, FLOW_FIELDS, flow_rows)
    write_csv_rows(health_check_csv, CHECK_FIELDS, checks)
    write_csv_rows(engineering_queue_csv, QUEUE_FIELDS, queue_rows)

    payload = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "sector_id": "home_appliances",
        "experiment_layer": "pm_decision_gate",
        "status": status,
        "next_gate": next_gate,
        "state_policy": policy,
        "inputs": {
            "formal_summary": str(formal_summary),
            "state_diagnostic": str(state_diagnostic),
            "panel_csv": str(panel_csv),
            "price_csv": str(price_csv),
            "dividend_csv": str(dividend_csv),
            "benchmark_csv": str(benchmark_csv),
        },
        "data_health": data_health,
        "formal_evidence": _formal_evidence(formal),
        "state_evidence": _state_evidence(state),
        "outputs": {
            "flow_table_csv": str(flow_table_csv),
            "health_check_csv": str(health_check_csv),
            "engineering_queue_csv": str(engineering_queue_csv),
            "report_path": str(report_path),
        },
        "pm_rules": [
            "This gate resolves Research/Quant state policy; it does not tune V5a.5c.",
            "External macro state variables are diagnostic only and cannot be positive scoring factors or guards in this handoff.",
            "Engineering may run local daily simulation only with frozen OCF yield + OCF-to-net-profit scoring.",
            "Engineering must output real dividends, trades, cash, holdings and rebalance_order_health.",
            "No V57f sleeve inclusion, JoinQuant platform claim or accepted-strategy status is allowed here.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, payload)
    report_path.write_text(_report(payload, flow_rows, checks, queue_rows), encoding="utf-8")

    packet = create_agent_loop_packet(
        packet_type="checkpoint_packet",
        objective="home_appliances_no_state_policy_engineering_gate",
        agent="Project Manager Agent",
        experiment_layer="pm_decision_gate",
        decision="return_to_engineering" if queue_rows else "return_to_research",
        next_owner="Engineering Agent" if queue_rows else "Research Agent",
        out_dir=agent_packet_dir,
        timebox_minutes=60,
        artifacts=[str(flow_table_csv), str(health_check_csv), str(engineering_queue_csv), str(summary_json), str(report_path)],
        evidence=[
            f"Formal status: {formal.get('status')}",
            f"State diagnostic status: {state.get('status')}",
            f"State policy: {policy['decision']}",
            f"Engineering gate status: {status}",
        ],
        blockers=[] if queue_rows else ["Engineering handoff is blocked by failed PM gate checks."],
        allowed_next_action=next_gate,
        restart_condition="rerun after Engineering local daily simulation or after Research repairs failed checks",
        loop_id="home_appliances_engineering_gate_20260722",
    )
    payload["agent_packet"] = {"packet_path": str(packet.packet_path), "report_path": str(packet.report_path)}
    write_json_file(summary_json, payload)

    return HomeAppliancesEngineeringGateResult(
        output_dir=out,
        flow_table_csv=flow_table_csv,
        health_check_csv=health_check_csv,
        engineering_queue_csv=engineering_queue_csv,
        summary_json=summary_json,
        report_path=report_path,
        agent_packet_json=packet.packet_path,
        status=status,
        next_gate=next_gate,
    )


def _state_policy(formal: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "no_state_scoring_or_guard_policy_accepted_for_engineering_smoke_test",
        "reason": (
            "True inventory, receivables, working-capital and export exposure fields have been repaired, "
            "but state diagnostics do not justify a stable ex-ante scoring or guard rule. "
            "External real-estate, export and commodity proxies remain diagnostic risk context only."
        ),
        "allowed_in_engineering": [
            "log_state_fields_for_attribution",
            "use_state_fields_for_post_trade_failure_diagnosis",
        ],
        "blocked_in_engineering": [
            "positive_scoring_factor",
            "defensive_guard",
            "rebalance_timing_rule",
            "selection_count_or_weight_tuning",
        ],
        "formal_status": formal.get("status"),
        "state_status": state.get("status"),
    }


def _build_checks(formal: dict[str, Any], state: dict[str, Any], data_health: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, str]]:
    audit = formal.get("notice_date_leakage_audit") or []
    leakage_passed = bool(audit) and all(str(item.get("status")) == "pass" for item in audit)
    rolling = formal.get("rolling_validation") or []
    completed_rolling = [item for item in rolling if str(item.get("status")) == "completed"]
    ic_rows = formal.get("factor_ic_rankic") or []
    return [
        _check("formal_validation_completed", str(formal.get("status")) == "formal_validation_completed_not_acceptance", str(formal.get("status") or "")),
        _check("notice_date_leakage_audit_passed", leakage_passed, f"checks={len(audit)}"),
        _check("rolling_validation_completed", len(completed_rolling) >= 4, f"completed_windows={len(completed_rolling)}"),
        _check("factor_ic_rankic_available", len(ic_rows) >= 2, f"factor_rows={len(ic_rows)}"),
        _check("state_diagnostic_completed", str(state.get("status")) == "state_diagnostic_completed_not_engineering_handoff", str(state.get("status") or "")),
        _check("no_state_policy_documented", bool(policy.get("decision")), str(policy.get("decision") or "")),
        _check("panel_exists", bool(data_health["panel_exists"]), f"rows={data_health['panel_row_count']} latest={data_health['latest_panel_trade_date']}"),
        _check("real_daily_prices_exist", bool(data_health["price_exists"]), f"rows={data_health['price_row_count']} latest={data_health['latest_price_date']}"),
        _check("real_dividends_exist", bool(data_health["dividend_exists"]), f"rows={data_health['dividend_row_count']} latest={data_health['latest_dividend_pay_date']}"),
        _check("benchmark_prices_exist", bool(data_health["benchmark_exists"]), f"rows={data_health['benchmark_row_count']} latest={data_health['latest_benchmark_date']}"),
    ]


def _data_health(panel_csv: Path, price_csv: Path, dividend_csv: Path, benchmark_csv: Path) -> dict[str, Any]:
    panel_rows = read_csv_rows_if_exists(panel_csv)
    price_rows = read_csv_rows_if_exists(price_csv)
    dividend_rows = read_csv_rows_if_exists(dividend_csv)
    benchmark_rows = read_csv_rows_if_exists(benchmark_csv)
    return {
        "panel_exists": panel_csv.exists(),
        "price_exists": price_csv.exists(),
        "dividend_exists": dividend_csv.exists(),
        "benchmark_exists": benchmark_csv.exists(),
        "panel_row_count": len(panel_rows),
        "price_row_count": len(price_rows),
        "dividend_row_count": len(dividend_rows),
        "benchmark_row_count": len(benchmark_rows),
        "latest_panel_trade_date": _latest_date(panel_rows, "trade_date"),
        "latest_price_date": _latest_date(price_rows, "date"),
        "latest_dividend_pay_date": _latest_date(dividend_rows, "pay_date"),
        "latest_benchmark_date": _latest_date(benchmark_rows, "date"),
    }


def _formal_evidence(formal: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_count": formal.get("row_count"),
        "date_count": formal.get("date_count"),
        "status": formal.get("status"),
        "rolling_validation": formal.get("rolling_validation"),
        "factor_ic_rankic": formal.get("factor_ic_rankic"),
        "governance": formal.get("governance"),
    }


def _state_evidence(state: dict[str, Any]) -> dict[str, Any]:
    rows = state.get("bucket_rows") or []
    return {
        "status": state.get("status"),
        "bucket_row_count": len(rows),
        "metrics": sorted({str(row.get("metric") or "") for row in rows if row.get("metric")}),
        "governance": state.get("governance"),
    }


def _status_and_gate(checks: list[dict[str, str]]) -> tuple[str, str]:
    failed = [row for row in checks if row["status"] != "passed"]
    if failed:
        return "research_repair_required_before_engineering", "return_to_research_for_failed_gate_checks"
    return "engineering_handoff_ready_local_daily_only", "engineering_run_local_daily_simulation_with_order_health"


def _flow_rows(strategy_id: str, status: str) -> list[dict[str, str]]:
    handoff_status = "completed" if status == "engineering_handoff_ready_local_daily_only" else "blocked"
    return [
        _flow("1", "Project Manager Agent", "sleeve_promotion_queue.csv", "Confirm home_appliances is rank-2 repair candidate, not V57f sleeve", "PM scoped task", "no_core_inclusion", "completed"),
        _flow("2", "Research Agent", "V5a.5d PM decision + state diagnostics", "Decide whether external state is hard gate or diagnostic only", "no-state policy", "no_return_tuning", "completed"),
        _flow("3", "Quant Validation Agent", strategy_id, "Review formal validation, PIT leakage, rolling, IC/RankIC, ablation and robustness evidence", "validation evidence contract", "research_pit_validation", "completed"),
        _flow("4", "Project Manager Agent", "panel / real prices / dividends / benchmark", "Check engineering input files exist", "engineering data contract", "files_exist", "completed"),
        _flow("5", "Project Manager Agent", "policy + validation + data checks", "Open or block Engineering handoff", "engineering queue", "local_daily_only", handoff_status),
        _flow("6", "Engineering Agent", "engineering queue", "Run local daily simulation with real dividends, trades, cash, holdings and rebalance_order_health", "local daily packet", "no_tuning", "pending"),
    ]


def _engineering_queue(strategy_id: str) -> list[dict[str, str]]:
    return [
        {
            "queue_rank": "1",
            "sector_id": "home_appliances",
            "owner": "Engineering Agent",
            "task": "Run local daily simulation only for frozen home_appliances_ocf_quality_v5a5c; include real dividends, trades, cash, holdings and rebalance_order_health.",
            "input_artifacts": "home_appliances_engineering_gate_summary.json; examples/home_appliances_ocf_quality_v5a5c_strategy.json; panel_with_home_appliances_state_gate.csv; real_daily_prices.csv; cash_dividends.csv",
            "output_artifacts": "local_daily_summary.json; daily_returns.csv; holdings.csv; trades.csv; dividends.csv; rebalance_order_health.csv",
            "gate": "engineering_local_daily_simulation_only",
            "blocked_actions": "do_not_tune; do_not_add_to_V57f; do_not_start_joinquant; do_not_claim_platform_replication; do_not_accept_strategy",
        }
    ]


def _check(check: str, ok: bool, detail: str) -> dict[str, str]:
    return {"check": check, "status": "passed" if ok else "needs_review", "detail": detail}


def _flow(stage: str, owner: str, input_path: str, action: str, output: str, gate: str, status: str) -> dict[str, str]:
    return {
        "stage": stage,
        "owner": owner,
        "input": input_path,
        "action": action,
        "output": output,
        "gate": gate,
        "status": status,
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _latest_date(rows: list[dict[str, str]], field: str) -> str:
    dates = sorted({_row_date(row, field) for row in rows if _row_date(row, field)})
    return dates[-1] if dates else ""


def _row_date(row: dict[str, str], field: str) -> str:
    return str(row.get(field) or "")[:10]


def _report(payload: dict[str, Any], flow_rows: list[dict[str, str]], checks: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> str:
    lines = [
        f"# Home Appliances Engineering Gate: {payload['strategy_id']}",
        "",
        f"- Status: `{payload['status']}`",
        f"- Next gate: `{payload['next_gate']}`",
        f"- State policy: `{payload['state_policy']['decision']}`",
        "",
        "## Detailed Flow Table",
        "",
        "| Stage | Owner | Input | Action | Output | Gate | Status |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in flow_rows:
        lines.append(
            f"| {row['stage']} | {row['owner']} | `{row['input']}` | {row['action']} | `{row['output']}` | `{row['gate']}` | `{row['status']}` |"
        )
    lines.extend(["", "## Gate Checks", "", "| Check | Status | Detail |", "| --- | --- | --- |"])
    for row in checks:
        lines.append(f"| `{row['check']}` | `{row['status']}` | {row['detail']} |")
    lines.extend(["", "## Engineering Queue", "", "| Rank | Sector | Owner | Task | Gate |", "| ---: | --- | --- | --- | --- |"])
    for row in queue_rows:
        lines.append(f"| {row['queue_rank']} | {row['sector_id']} | {row['owner']} | {row['task']} | `{row['gate']}` |")
    if not queue_rows:
        lines.append("|  |  |  | No Engineering handoff until failed checks are repaired. |  |")
    lines.extend(["", "## PM Rules", ""])
    for item in payload["pm_rules"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"
