from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.agent_loop_packet_runner import create_agent_loop_packet
from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.math_utils import to_float
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_STRATEGY_ID = "telecom_operators_cashflow_dividend_v55a"
DEFAULT_OVERLAY_ID = "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
DEFAULT_FORMAL_SUMMARY = Path("validation_formal_v55a_similar_sectors") / DEFAULT_STRATEGY_ID / "formal_validation_summary.json"
DEFAULT_OVERLAY_DAILY_SUMMARY = (
    Path("local_daily_backtests_v58_telecom_overlay_matched")
    / DEFAULT_OVERLAY_ID
    / DEFAULT_OVERLAY_ID
    / "summary.json"
)
DEFAULT_OVERLAY_FORMAL_SUMMARY = Path("validation_formal_v58_telecom_overlay_matched_basket") / DEFAULT_OVERLAY_ID / "basket_formal_validation_summary.json"
DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "low_volatility_factors_v58" / "telecom_operators" / DEFAULT_STRATEGY_ID / "panel_with_low_vol.csv"
DEFAULT_PRICE_CSV = DEFAULT_PROCESSED_DIR / "telecom_joinquant_joinquant_real_daily_prices.csv"
DEFAULT_DIVIDEND_CSV = DEFAULT_PROCESSED_DIR / "telecom_joinquant_joinquant_cash_dividends.csv"
DEFAULT_BENCHMARK_CSV = DEFAULT_PROCESSED_DIR / "telecom_joinquant_joinquant_real_benchmark_prices.csv"
DEFAULT_V57F_SUMMARY = (
    Path("local_daily_backtests_v57f_etf")
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
    / "summary.json"
)
DEFAULT_OUT_DIR = Path("telecom_engineering_readiness_v5") / "current"
DEFAULT_PACKET_DIR = Path("agent_loop_packets_v5a") / "telecom_engineering_readiness"

FLOW_FIELDS = ["step", "owner", "input", "action", "output", "gate", "status", "forbidden_action"]
CHECK_FIELDS = ["check", "status", "detail"]
QUEUE_FIELDS = ["queue_rank", "sector_id", "owner", "task", "input_artifacts", "output_artifacts", "gate", "blocked_actions"]


@dataclass(frozen=True)
class TelecomEngineeringReadinessResult:
    output_dir: Path
    flow_table_csv: Path
    health_check_csv: Path
    engineering_queue_csv: Path
    summary_json: Path
    report_md: Path
    agent_packet_json: Path
    status: str
    next_gate: str


def review_telecom_engineering_readiness(
    *,
    strategy_id: str = DEFAULT_STRATEGY_ID,
    overlay_id: str = DEFAULT_OVERLAY_ID,
    formal_summary: Path = DEFAULT_FORMAL_SUMMARY,
    overlay_daily_summary: Path = DEFAULT_OVERLAY_DAILY_SUMMARY,
    overlay_formal_summary: Path = DEFAULT_OVERLAY_FORMAL_SUMMARY,
    panel_csv: Path = DEFAULT_PANEL,
    price_csv: Path = DEFAULT_PRICE_CSV,
    dividend_csv: Path = DEFAULT_DIVIDEND_CSV,
    benchmark_csv: Path = DEFAULT_BENCHMARK_CSV,
    v57f_summary: Path = DEFAULT_V57F_SUMMARY,
    out_dir: Path = DEFAULT_OUT_DIR,
    agent_packet_dir: Path = DEFAULT_PACKET_DIR,
) -> TelecomEngineeringReadinessResult:
    formal = _read_json(formal_summary)
    overlay_daily = _read_json(overlay_daily_summary)
    overlay_formal = _read_json(overlay_formal_summary)
    v57f = _read_json(v57f_summary)
    data_health = _data_health(panel_csv, price_csv, dividend_csv, benchmark_csv)
    sample_policy = _sample_policy(formal)
    overlay_policy = _overlay_policy(overlay_daily, overlay_formal, v57f)
    checks = _checks(formal, overlay_daily, overlay_formal, data_health, sample_policy)
    status, next_gate = _status_and_gate(checks)
    flow_rows = _flow_rows(status)
    queue_rows = _queue_rows(strategy_id, overlay_id) if status == "engineering_observation_sleeve_ready" else []

    out_dir.mkdir(parents=True, exist_ok=True)
    flow_table_csv = out_dir / "telecom_engineering_readiness_flow_table.csv"
    health_check_csv = out_dir / "telecom_engineering_readiness_health_checks.csv"
    engineering_queue_csv = out_dir / "telecom_engineering_next_agent_queue.csv"
    summary_json = out_dir / "telecom_engineering_readiness_summary.json"
    report_md = out_dir / "telecom_engineering_readiness_report.md"

    write_csv_rows(flow_table_csv, FLOW_FIELDS, flow_rows, encoding="utf-8-sig")
    write_csv_rows(health_check_csv, CHECK_FIELDS, checks, encoding="utf-8-sig")
    write_csv_rows(engineering_queue_csv, QUEUE_FIELDS, queue_rows, encoding="utf-8-sig")

    payload = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "overlay_id": overlay_id,
        "sector_id": "telecom_operators",
        "label_en": "Telecom operators",
        "label_zh": "电信运营商",
        "experiment_layer": "pm_decision_gate",
        "status": status,
        "next_gate": next_gate,
        "inputs": {
            "formal_summary": str(formal_summary),
            "overlay_daily_summary": str(overlay_daily_summary),
            "overlay_formal_summary": str(overlay_formal_summary),
            "panel_csv": str(panel_csv),
            "price_csv": str(price_csv),
            "dividend_csv": str(dividend_csv),
            "benchmark_csv": str(benchmark_csv),
            "v57f_summary": str(v57f_summary),
        },
        "sample_policy": sample_policy,
        "overlay_policy": overlay_policy,
        "data_health": data_health,
        "standalone_evidence": _standalone_evidence(formal),
        "overlay_evidence": _overlay_evidence(overlay_daily, overlay_formal),
        "v57f_reference": _metrics(v57f),
        "pm_decision": {
            "can_enter_engineering": status == "engineering_observation_sleeve_ready",
            "engineering_scope": "capped_observation_sleeve_local_refresh_and_paper_tracking_only",
            "can_promote_standalone": False,
            "can_join_v57f_core": False,
            "can_enter_platform_replication": False,
            "can_write_joinquant_code": False,
        },
        "outputs": {
            "flow_table_csv": str(flow_table_csv),
            "health_check_csv": str(health_check_csv),
            "engineering_queue_csv": str(engineering_queue_csv),
            "report_md": str(report_md),
        },
        "pm_rules": [
            "Telecom has only three core A-share operators, so standalone promotion remains blocked.",
            "Engineering may refresh capped observation inputs and paper tracking only.",
            "Do not modify V57f factors, weights, sleeves, or rebalance rules.",
            "Do not rank telecom by historical return or use this review for tuning.",
            "Do not claim formal_strategy_candidate, platform_replication_passed, accepted_strategy, or live_trading_approved.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, payload)
    report_md.write_text(_report(payload, flow_rows, checks, queue_rows), encoding="utf-8")

    packet = create_agent_loop_packet(
        packet_type="checkpoint_packet",
        objective="telecom_operators_engineering_readiness_observation_sleeve",
        agent="Project Manager Agent",
        experiment_layer="pm_decision_gate",
        decision="return_to_engineering" if queue_rows else "return_to_research",
        next_owner="Engineering Agent" if queue_rows else "Research Agent",
        out_dir=agent_packet_dir,
        timebox_minutes=60,
        artifacts=[str(flow_table_csv), str(health_check_csv), str(engineering_queue_csv), str(summary_json), str(report_md)],
        evidence=[
            f"Standalone sample policy: {sample_policy['decision']}",
            f"Overlay policy: {overlay_policy['decision']}",
            f"Engineering readiness status: {status}",
        ],
        blockers=[] if queue_rows else ["Telecom engineering handoff is blocked by failed readiness checks."],
        allowed_next_action=next_gate,
        restart_condition="rerun after Engineering completes capped observation refresh or after Research repairs failed checks",
        loop_id="telecom_engineering_readiness_20260724",
    )
    payload["agent_packet"] = {"packet_path": str(packet.packet_path), "report_path": str(packet.report_path)}
    write_json_file(summary_json, payload)
    return TelecomEngineeringReadinessResult(
        output_dir=out_dir,
        flow_table_csv=flow_table_csv,
        health_check_csv=health_check_csv,
        engineering_queue_csv=engineering_queue_csv,
        summary_json=summary_json,
        report_md=report_md,
        agent_packet_json=packet.packet_path,
        status=status,
        next_gate=next_gate,
    )


def _sample_policy(formal: dict[str, Any]) -> dict[str, Any]:
    securities = _common_sample_securities(formal)
    return {
        "decision": "standalone_blocked_small_sample_capped_observation_only",
        "core_security_count": securities,
        "minimum_for_standalone": 8,
        "reason": "Only three core A-share telecom operators are available, so cross-sectional IC/RankIC is fragile.",
        "allowed": ["capped_observation_sleeve", "paper_tracking", "basket_sidecar_diagnostic"],
        "blocked": ["standalone_formal_candidate", "accepted_strategy", "v57f_core_inclusion"],
    }


def _overlay_policy(overlay_daily: dict[str, Any], overlay_formal: dict[str, Any], v57f: dict[str, Any]) -> dict[str, Any]:
    overlay_metrics = _metrics(overlay_daily)
    v57f_metrics = _metrics(v57f)
    return_delta = _delta(overlay_metrics.get("strategy_return"), v57f_metrics.get("strategy_return"))
    ir_delta = _delta(overlay_metrics.get("information_ratio"), v57f_metrics.get("information_ratio"))
    drawdown_delta = _delta(overlay_metrics.get("max_drawdown"), v57f_metrics.get("max_drawdown"))
    return {
        "decision": "overlay_diagnostic_completed_not_core_promotion",
        "reason": "Telecom overlay is useful as a defensive observation sleeve, but it does not beat V57f on return, excess return, or information ratio.",
        "return_delta_vs_v57f": return_delta,
        "information_ratio_delta_vs_v57f": ir_delta,
        "max_drawdown_delta_vs_v57f": drawdown_delta,
        "overlay_status": overlay_formal.get("status"),
        "allowed": ["refresh_observation_inputs", "paper_tracking_packet", "rebalance_order_health_review"],
        "blocked": ["replace_v57f", "join_v57f_core", "platform_replication"],
    }


def _checks(
    formal: dict[str, Any],
    overlay_daily: dict[str, Any],
    overlay_formal: dict[str, Any],
    data_health: dict[str, Any],
    sample_policy: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        _check("standalone_formal_validation_exists", formal.get("status") == "formal_validation_completed_not_acceptance", str(formal.get("status") or "")),
        _check("standalone_sample_size_policy_documented", sample_policy["core_security_count"] <= 3, f"core_security_count={sample_policy['core_security_count']}"),
        _check("standalone_promotion_blocked", "standalone_formal_candidate" in sample_policy["blocked"], sample_policy["decision"]),
        _check("overlay_local_daily_exists", bool(overlay_daily.get("metrics")), f"strategy_return={_pct(_metrics(overlay_daily).get('strategy_return'))}"),
        _check("overlay_formal_validation_exists", overlay_formal.get("status") == "formal_validation_completed_not_acceptance", str(overlay_formal.get("status") or "")),
        _check("panel_with_low_vol_exists", data_health["panel_exists"], f"rows={data_health['panel_row_count']} latest={data_health['latest_panel_trade_date']}"),
        _check("real_daily_prices_exist", data_health["price_exists"], f"rows={data_health['price_row_count']} latest={data_health['latest_price_date']}"),
        _check("real_cash_dividends_exist", data_health["dividend_exists"] and data_health["dividend_row_count"] > 0, f"rows={data_health['dividend_row_count']} latest={data_health['latest_dividend_pay_date']}"),
        _check("benchmark_prices_exist", data_health["benchmark_exists"], f"rows={data_health['benchmark_row_count']} latest={data_health['latest_benchmark_date']}"),
        _check("engineering_scope_is_observation_only", True, "local refresh + paper tracking + order health only"),
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


def _flow_rows(status: str) -> list[dict[str, str]]:
    handoff = "completed" if status == "engineering_observation_sleeve_ready" else "blocked"
    return [
        _flow("1", "Project Manager Agent", "V57f freeze state", "Confirm telecom cannot change V57f core", "scope lock", "no_core_inclusion", "completed", "modify V57f"),
        _flow("2", "Research Agent", "telecom industry universe", "Confirm only core operators are used", "small-sample policy", "sample_policy", "completed", "treat as ordinary cross-section"),
        _flow("3", "Quant Validation Agent", "standalone formal validation", "Review PIT, rolling, IC/RankIC, failure years", "standalone blocker evidence", "research_signal_only", "completed", "promote standalone"),
        _flow("4", "Engineering Agent", "real prices, dividends, low-vol panel", "Confirm observation inputs exist", "engineering data contract", "files_exist", "completed", "ignore missing dividends/order health"),
        _flow("5", "Project Manager Agent", "overlay daily + formal validation", "Classify overlay as diagnostic only", "overlay policy", "not_v57f_replacement", "completed", "rank by historical return"),
        _flow("6", "Project Manager Agent", "all checks", "Open capped observation Engineering handoff", "engineering queue", "local_refresh_only", handoff, "platform replication or JoinQuant code"),
    ]


def _queue_rows(strategy_id: str, overlay_id: str) -> list[dict[str, str]]:
    return [
        {
            "queue_rank": "1",
            "sector_id": "telecom_operators",
            "owner": "Engineering Agent",
            "task": "Refresh telecom capped observation sleeve inputs and build paper tracking readiness packet through 2026-05-31.",
            "input_artifacts": ";".join(
                [
                    str(DEFAULT_PANEL),
                    str(DEFAULT_PRICE_CSV),
                    str(DEFAULT_DIVIDEND_CSV),
                    str(DEFAULT_BENCHMARK_CSV),
                    str(DEFAULT_OVERLAY_DAILY_SUMMARY),
                    str(DEFAULT_OVERLAY_FORMAL_SUMMARY),
                ]
            ),
            "output_artifacts": ";".join(
                [
                    "telecom local daily refresh summary",
                    "telecom trades/cash/holdings/dividends",
                    "telecom rebalance_order_health",
                    "telecom paper tracking readiness packet",
                ]
            ),
            "gate": "engineering_observation_sleeve_only",
            "blocked_actions": ";".join(
                [
                    "do_not_modify_V57f",
                    "do_not_tune",
                    "do_not_promote_standalone",
                    "do_not_platform_replication",
                    "do_not_write_joinquant_code",
                ]
            ),
        }
    ]


def _standalone_evidence(formal: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": formal.get("status"),
        "row_count": formal.get("row_count"),
        "date_count": formal.get("date_count"),
        "core_security_count": _common_sample_securities(formal),
        "rolling_2026_return": _rolling_return(formal, "2026"),
        "baseline_tests": formal.get("baseline_tests", []),
        "factor_ic_rankic": formal.get("factor_ic_rankic", []),
        "governance": formal.get("governance"),
    }


def _overlay_evidence(overlay_daily: dict[str, Any], overlay_formal: dict[str, Any]) -> dict[str, Any]:
    return {
        "daily_metrics": _metrics(overlay_daily),
        "signal_count": overlay_daily.get("signal_count"),
        "trade_count": overlay_daily.get("trade_count"),
        "dividend_count": overlay_daily.get("dividend_count"),
        "formal_status": overlay_formal.get("status"),
        "sector_exposure": overlay_formal.get("sector_exposure", []),
        "weak_year_analysis": overlay_formal.get("weak_year_analysis", []),
    }


def _status_and_gate(checks: list[dict[str, str]]) -> tuple[str, str]:
    failed = [row for row in checks if row["status"] != "passed"]
    if failed:
        return "research_or_data_repair_required_before_engineering", "return_to_research_or_data_repair"
    return "engineering_observation_sleeve_ready", "engineering_refresh_capped_observation_and_paper_tracking"


def _report(payload: dict[str, Any], flow_rows: list[dict[str, str]], checks: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> str:
    lines = [
        "# Telecom Engineering Readiness Report",
        "",
        f"Created at UTC: `{payload['created_at_utc']}`",
        "",
        "## PM Decision",
        "",
        f"Status: `{payload['status']}`",
        f"Next gate: `{payload['next_gate']}`",
        "",
        "Telecom can enter Engineering only as a capped observation sleeve. Standalone promotion, V57f core inclusion, platform replication, and JoinQuant code remain blocked.",
        "",
        "## Detailed Flow Table",
        "",
        "| Step | Owner | Action | Gate | Status | Forbidden action |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for row in flow_rows:
        lines.append(f"| {row['step']} | {row['owner']} | {row['action']} | `{row['gate']}` | `{row['status']}` | {row['forbidden_action']} |")
    lines.extend(["", "## Health Checks", "", "| Check | Status | Detail |", "| --- | --- | --- |"])
    for row in checks:
        lines.append(f"| `{row['check']}` | `{row['status']}` | {row['detail']} |")
    lines.extend(
        [
            "",
            "## Evidence Snapshot",
            "",
            f"- Standalone PIT rows: `{payload['standalone_evidence']['row_count']}`; dates: `{payload['standalone_evidence']['date_count']}`; core securities: `{payload['standalone_evidence']['core_security_count']}`.",
            f"- Overlay return: `{_pct(payload['overlay_evidence']['daily_metrics'].get('strategy_return'))}`; drawdown: `{_pct(payload['overlay_evidence']['daily_metrics'].get('max_drawdown'))}`; IR: `{payload['overlay_evidence']['daily_metrics'].get('information_ratio')}`.",
            f"- V57f reference return: `{_pct(payload['v57f_reference'].get('strategy_return'))}`; drawdown: `{_pct(payload['v57f_reference'].get('max_drawdown'))}`; IR: `{payload['v57f_reference'].get('information_ratio')}`.",
            "",
            "## Engineering Queue",
            "",
            "| Rank | Owner | Task | Gate | Blocked actions |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for row in queue_rows:
        lines.append(f"| {row['queue_rank']} | {row['owner']} | {row['task']} | `{row['gate']}` | `{row['blocked_actions']}` |")
    if not queue_rows:
        lines.append("|  |  | No handoff until failed checks are repaired. |  |  |")
    lines.extend(["", "## PM Rules", ""])
    for rule in payload["pm_rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def _metrics(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload.get("metrics") if isinstance(payload, dict) else {}
    return metrics if isinstance(metrics, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {"check": name, "status": "passed" if passed else "failed", "detail": detail}


def _flow(step: str, owner: str, input_: str, action: str, output: str, gate: str, status: str, forbidden_action: str) -> dict[str, str]:
    return {
        "step": step,
        "owner": owner,
        "input": input_,
        "action": action,
        "output": output,
        "gate": gate,
        "status": status,
        "forbidden_action": forbidden_action,
    }


def _common_sample_securities(formal: dict[str, Any]) -> int:
    for row in formal.get("common_sample_interaction_tests", []) or []:
        value = row.get("common_sample_securities")
        parsed = to_float(value)
        if parsed is not None:
            return int(parsed)
    return 0


def _rolling_return(formal: dict[str, Any], year: str) -> Any:
    for row in formal.get("rolling_validation", []) or []:
        if str(row.get("window")) == year:
            return row.get("cum_return")
    return None


def _latest_date(rows: list[dict[str, str]], field: str) -> str:
    values = [str(row.get(field) or "")[:10] for row in rows if row.get(field)]
    return max(values) if values else ""


def _delta(value: Any, base: Any) -> float | None:
    parsed = to_float(value)
    parsed_base = to_float(base)
    if parsed is None or parsed_base is None:
        return None
    return parsed - parsed_base


def _pct(value: Any) -> str:
    parsed = to_float(value)
    return "" if parsed is None else f"{parsed * 100:.2f}%"
