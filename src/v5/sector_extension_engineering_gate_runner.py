from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file


DEFAULT_PROMOTION_QUEUE = Path("enhanced_etf_production_lines_v5") / "current" / "sleeve_promotion_queue.csv"
DEFAULT_SELECTED_QUEUE = (
    Path("enhanced_etf_production_lines_v5")
    / "current"
    / "promotion_agent_queues"
    / "selected_candidate_agent_queue.csv"
)
DEFAULT_GAS_WATER_LOCAL_DAILY = (
    Path("local_daily_backtests_v59b_gas_water_state_guard_repaired_2021_07")
    / "gas_water_v57b_text_debt_state_guard_v59b"
)
DEFAULT_OUT_DIR = Path("sector_extension_engineering_gates_v5") / "current"

FLOW_FIELDS = [
    "step",
    "stage",
    "owner",
    "input",
    "action",
    "output",
    "gate",
    "status",
    "forbidden_action",
]
CHECK_FIELDS = ["check", "status", "detail"]
QUEUE_FIELDS = ["queue_rank", "owner", "task", "input_artifacts", "output_artifacts", "gate", "blocked_actions"]


@dataclass(frozen=True)
class SectorExtensionEngineeringGateResult:
    output_dir: Path
    flow_table_csv: Path
    candidate_snapshot_csv: Path
    engineering_checks_csv: Path
    summary_json: Path
    report_md: Path
    next_agent_queue_csv: Path
    status: str
    selected_sector_id: str


def run_sector_extension_engineering_gate(
    *,
    promotion_queue: Path = DEFAULT_PROMOTION_QUEUE,
    selected_queue: Path = DEFAULT_SELECTED_QUEUE,
    gas_water_local_daily: Path = DEFAULT_GAS_WATER_LOCAL_DAILY,
    out_dir: Path = DEFAULT_OUT_DIR,
    as_of_date: str = "2026-07-24",
) -> SectorExtensionEngineeringGateResult:
    promotion_rows = read_csv_rows_if_exists(promotion_queue)
    selected_rows = read_csv_rows_if_exists(selected_queue)
    selected_sector = _selected_sector(promotion_rows, selected_rows)
    local_daily_dir = _local_daily_dir_for(selected_sector, gas_water_local_daily)
    local_summary = _read_json_if_exists(local_daily_dir / "summary.json")

    engineering_checks = _engineering_checks(
        selected_sector=selected_sector,
        selected_rows=selected_rows,
        local_daily_dir=local_daily_dir,
        local_summary=local_summary,
    )
    status = "engineering_test_passed" if all(row["status"] == "passed" for row in engineering_checks) else "engineering_test_needs_review"
    flow_rows = _flow_rows(status, selected_sector)
    candidate_snapshot = _candidate_snapshot_rows(promotion_rows, selected_sector, status)
    next_queue = _next_queue(status, selected_sector, local_daily_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    flow_table_csv = out_dir / "sector_extension_123_flow_table.csv"
    candidate_snapshot_csv = out_dir / "sector_extension_candidate_snapshot.csv"
    engineering_checks_csv = out_dir / "sector_extension_engineering_checks.csv"
    summary_json = out_dir / "sector_extension_engineering_gate_summary.json"
    report_md = out_dir / "sector_extension_engineering_gate_report.md"
    next_agent_queue_csv = out_dir / "sector_extension_next_agent_queue.csv"

    write_csv_rows(flow_table_csv, FLOW_FIELDS, flow_rows, encoding="utf-8-sig")
    write_csv_rows(candidate_snapshot_csv, _candidate_fields(promotion_rows), candidate_snapshot, encoding="utf-8-sig")
    write_csv_rows(engineering_checks_csv, CHECK_FIELDS, engineering_checks, encoding="utf-8-sig")
    write_csv_rows(next_agent_queue_csv, QUEUE_FIELDS, next_queue, encoding="utf-8-sig")

    payload = {
        "schema_version": 1,
        "project": "v5_sector_extension_engineering_gate",
        "experiment_layer": "pm_engineering_gate",
        "status": status,
        "as_of_date": as_of_date,
        "selected_sector_id": selected_sector,
        "selected_rule": "rank1_only_by_min_completion_cost_plus_cashflow_dividend_low_vol_fit_not_returns",
        "selected_local_daily_dir": str(local_daily_dir),
        "local_daily_summary": _local_summary_payload(local_summary, local_daily_dir),
        "outputs": {
            "flow_table_csv": str(flow_table_csv),
            "candidate_snapshot_csv": str(candidate_snapshot_csv),
            "engineering_checks_csv": str(engineering_checks_csv),
            "next_agent_queue_csv": str(next_agent_queue_csv),
            "report_md": str(report_md),
        },
        "inputs": {
            "promotion_queue": str(promotion_queue),
            "selected_queue": str(selected_queue),
            "gas_water_local_daily": str(gas_water_local_daily),
        },
        "pm_rules": [
            "Do not modify frozen V57f core sleeves, weights, factors, rebalance rules or timing.",
            "Do not rank or promote candidates by historical return.",
            "Only the rank-1 candidate may enter this engineering gate.",
            "Engineering gate means local daily simulation, real dividends, trades, holdings and rebalance_order_health.",
            "Do not start JoinQuant platform replication or generate the 2026-10 paper runner in this task.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, payload)
    report_md.write_text(_report(payload, flow_rows, engineering_checks, next_queue), encoding="utf-8")

    return SectorExtensionEngineeringGateResult(
        output_dir=out_dir,
        flow_table_csv=flow_table_csv,
        candidate_snapshot_csv=candidate_snapshot_csv,
        engineering_checks_csv=engineering_checks_csv,
        summary_json=summary_json,
        report_md=report_md,
        next_agent_queue_csv=next_agent_queue_csv,
        status=status,
        selected_sector_id=selected_sector,
    )


def _engineering_checks(
    *,
    selected_sector: str,
    selected_rows: list[dict[str, str]],
    local_daily_dir: Path,
    local_summary: dict[str, Any],
) -> list[dict[str, str]]:
    order = local_summary.get("rebalance_order_health", {}) if isinstance(local_summary, dict) else {}
    outputs = local_summary.get("outputs", {}) if isinstance(local_summary, dict) else {}
    trade_rows = _file_row_count(local_daily_dir / "trades.csv")
    dividend_rows = _file_row_count(local_daily_dir / "dividends.csv")
    checks = [
        _check("selected_queue_exists", bool(selected_rows), f"rows={len(selected_rows)}"),
        _check("rank1_candidate_supported", selected_sector == "gas_water_operators", selected_sector),
        _check("local_daily_summary_exists", bool(local_summary), str(local_daily_dir / "summary.json")),
        _check("local_daily_status_passed", "passed" in str(local_summary.get("status") or ""), str(local_summary.get("status") or "")),
        _check("window_end_locked_2026_05_31", str(local_summary.get("window", {}).get("end_date")) == "2026-05-31", json.dumps(local_summary.get("window", {}), ensure_ascii=False)),
        _check("rebalance_signal_count_positive", int(local_summary.get("signal_count") or 0) > 0, f"signal_count={local_summary.get('signal_count')}"),
        _check("daily_rows_positive", int(local_summary.get("daily_count") or 0) > 0, f"daily_count={local_summary.get('daily_count')}"),
        _check("trades_exist", int(local_summary.get("trade_count") or 0) > 0 or trade_rows > 0, f"trade_count={local_summary.get('trade_count')} file_rows={trade_rows}"),
        _check("holdings_exist", (local_daily_dir / "holdings.csv").exists() or bool(outputs.get("holdings")), str(local_daily_dir / "holdings.csv")),
        _check("real_dividends_exist", int(local_summary.get("dividend_count") or 0) > 0 or dividend_rows > 0, f"dividend_count={local_summary.get('dividend_count')} file_rows={dividend_rows}"),
        _check("rebalance_order_health_output_exists", (local_daily_dir / "rebalance_order_health.csv").exists() or bool(outputs.get("rebalance_order_health")), str(local_daily_dir / "rebalance_order_health.csv")),
        _check("rebalance_order_health_passed", not bool(order.get("needs_review")) and int(order.get("unexpected_rebalance_issue_count") or 0) == 0, json.dumps(order, ensure_ascii=False)),
        _check("no_leading_no_position_gap", int(order.get("leading_no_order_no_position_count") or 0) == 0, json.dumps(order, ensure_ascii=False)),
        _check("coverage_no_missing_rebalance", int(order.get("missing_daily_rebalance_count") or 0) == 0, json.dumps(order, ensure_ascii=False)),
    ]
    return checks


def _flow_rows(status: str, selected_sector: str) -> list[dict[str, str]]:
    engineering_status = "completed" if status == "engineering_test_passed" else "needs_review"
    return [
        _flow("1", "Candidate screening", "Project Manager Agent", "sleeve_registry + status_registry", "Generate candidate queue by data readiness, mandate fit and completion cost", "sleeve_promotion_queue.csv", "rank_by_cost_and_fit_not_return", "completed", "rank_by_historical_return"),
        _flow("2", "Gap checklist", "Project Manager Agent", "candidate queue", "Check PIT, real dividends, low-vol factors, state variables, sample risk, local daily and order-health gaps", "candidate_snapshot.csv", "every_gap_is_a_gate", "completed", "treat_missing_evidence_as_passed"),
        _flow("3", "PM selection", "Project Manager Agent", "ranked queue", f"Select only rank-1 candidate: {selected_sector}", "selected_candidate_agent_queue.csv", "rank1_only", "completed", "advance_multiple_candidates_at_once"),
        _flow("4", "Engineering scope lock", "Engineering Agent", selected_sector, "Confirm local daily test only; no V57f change, no tuning, no JoinQuant", "scope lock", "no_strategy_change", "completed", "modify_V57f_or_write_joinquant_code"),
        _flow("5", "Local daily simulation audit", "Engineering Agent", "summary/daily/trades/holdings/dividends", "Verify local daily simulation outputs and 2026-05-31 window", "engineering_checks.csv", "daily_outputs_exist", engineering_status, "ignore_missing_trade_or_dividend_outputs"),
        _flow("6", "Order-health audit", "Engineering Agent", "rebalance_order_health.csv", "Verify all rebalance dates either trade, hold existing positions, or intentionally hold cash by guard", "engineering_checks.csv", "unexpected_issue_count_zero", engineering_status, "ignore_no_order_rebalance_dates"),
        _flow("7", "PM closeout", "Project Manager Agent", "engineering checks", "Classify selected sleeve as engineering test passed or route repair", "summary/report/next_queue", "single_next_queue", engineering_status, "promote_to_V57f_core_or_accepted_strategy"),
    ]


def _candidate_snapshot_rows(rows: list[dict[str, str]], selected_sector: str, engineering_status: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        copied["selected_for_this_gate"] = "yes" if row.get("sector_id") == selected_sector else "no"
        copied["engineering_gate_status"] = engineering_status if row.get("sector_id") == selected_sector else "not_run_rank1_only"
        copied["blocked_action"] = "do_not_modify_V57f;do_not_tune;do_not_start_joinquant_test"
        result.append(copied)
    return result


def _next_queue(status: str, selected_sector: str, local_daily_dir: Path) -> list[dict[str, str]]:
    if status == "engineering_test_passed":
        return [
            {
                "queue_rank": "1",
                "owner": "Project Manager Agent",
                "task": f"Keep {selected_sector} as observation sleeve with engineering test passed; wait for clean future paper evidence or separate PM stage gate.",
                "input_artifacts": str(local_daily_dir),
                "output_artifacts": "observation_sleeve_checkpoint",
                "gate": "observation_wait_no_core_inclusion",
                "blocked_actions": "do_not_modify_V57f;do_not_tune;do_not_start_joinquant_test;do_not_claim_platform_replication",
            }
        ]
    return [
        {
            "queue_rank": "1",
            "owner": "Engineering Agent",
            "task": f"Repair failed local daily or rebalance_order_health checks for {selected_sector}.",
            "input_artifacts": "sector_extension_engineering_checks.csv",
            "output_artifacts": "repaired_engineering_gate_packet",
            "gate": "engineering_repair",
            "blocked_actions": "do_not_modify_V57f;do_not_tune;do_not_start_joinquant_test",
        }
    ]


def _local_summary_payload(summary: dict[str, Any], local_daily_dir: Path) -> dict[str, Any]:
    return {
        "status": summary.get("status"),
        "strategy_id": summary.get("strategy_id"),
        "window": summary.get("window", {}),
        "signal_count": summary.get("signal_count"),
        "daily_count": summary.get("daily_count"),
        "trade_count": summary.get("trade_count"),
        "dividend_count": summary.get("dividend_count"),
        "trade_file_rows": _file_row_count(local_daily_dir / "trades.csv"),
        "dividend_file_rows": _file_row_count(local_daily_dir / "dividends.csv"),
        "rebalance_order_health": summary.get("rebalance_order_health", {}),
        "metrics": summary.get("metrics", {}),
    }


def _report(
    payload: dict[str, Any],
    flow_rows: list[dict[str, str]],
    checks: list[dict[str, str]],
    next_queue: list[dict[str, str]],
) -> str:
    metrics = payload.get("local_daily_summary", {}).get("metrics", {})
    lines = [
        "# Sector Extension 1/2/3 Engineering Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Selected sector: `{payload['selected_sector_id']}`",
        f"- Rule: `{payload['selected_rule']}`",
        f"- Strategy return: `{metrics.get('strategy_return', '')}`",
        f"- Max drawdown: `{metrics.get('max_drawdown', '')}`",
        f"- Information ratio: `{metrics.get('information_ratio', '')}`",
        "",
        "## Detailed Flow Table",
        "",
        "| Step | Stage | Owner | Input | Action | Output | Gate | Status | Forbidden Action |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in flow_rows:
        lines.append(
            f"| {row['step']} | {row['stage']} | {row['owner']} | `{row['input']}` | {row['action']} | `{row['output']}` | `{row['gate']}` | `{row['status']}` | `{row['forbidden_action']}` |"
        )
    lines.extend(["", "## Engineering Checks", "", "| Check | Status | Detail |", "| --- | --- | --- |"])
    for row in checks:
        detail = row["detail"].replace("|", "/")
        lines.append(f"| `{row['check']}` | `{row['status']}` | {detail} |")
    lines.extend(["", "## Next Queue", "", "| Rank | Owner | Task | Gate |", "| ---: | --- | --- | --- |"])
    for row in next_queue:
        lines.append(f"| {row['queue_rank']} | {row['owner']} | {row['task']} | `{row['gate']}` |")
    lines.extend(
        [
            "",
            "## PM Rules",
            "",
            "- V57f remains frozen.",
            "- This gate does not promote the sleeve into V57f.",
            "- This gate does not start JoinQuant replication or the October paper runner.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_fields(rows: list[dict[str, str]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    for extra in ["selected_for_this_gate", "engineering_gate_status", "blocked_action"]:
        if extra not in fields:
            fields.append(extra)
    return fields


def _selected_sector(promotion_rows: list[dict[str, str]], selected_rows: list[dict[str, str]]) -> str:
    if selected_rows:
        return str(selected_rows[0].get("sector_id") or "")
    ranked = sorted(promotion_rows, key=lambda row: int(row.get("rank") or 9999))
    return str(ranked[0].get("sector_id") or "") if ranked else ""


def _local_daily_dir_for(selected_sector: str, gas_water_local_daily: Path) -> Path:
    if selected_sector == "gas_water_operators":
        return gas_water_local_daily
    return Path("__unsupported_selected_sector__") / selected_sector


def _check(check: str, ok: bool, detail: str) -> dict[str, str]:
    return {"check": check, "status": "passed" if ok else "needs_review", "detail": detail}


def _flow(
    step: str,
    stage: str,
    owner: str,
    input_path: str,
    action: str,
    output: str,
    gate: str,
    status: str,
    forbidden_action: str,
) -> dict[str, str]:
    return {
        "step": step,
        "stage": stage,
        "owner": owner,
        "input": input_path,
        "action": action,
        "output": output,
        "gate": gate,
        "status": status,
        "forbidden_action": forbidden_action,
    }


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        return {}
    return payload


def _file_row_count(path: Path) -> int:
    return len(read_csv_rows_if_exists(path))
