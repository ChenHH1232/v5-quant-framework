from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.math_utils import to_float


DEFAULT_OUT_DIR = Path("new_sleeve_execution_v5") / "current"
DEFAULT_V57F_CONFIG = Path("config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json")
DEFAULT_V57F_SUMMARY = (
    Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "summary.json"
)
DEFAULT_SLEEVE_REGISTRY = Path("enhanced_etf_production_lines_v5") / "current" / "sleeve_registry.csv"
DEFAULT_STATUS_REGISTRY = Path("docs/governance/status_registry.json")

ROUTE_FIELDS = [
    "sector_id",
    "label_en",
    "label_zh",
    "route_status",
    "pm_gate",
    "next_owner",
    "allowed_next_action",
    "blocked_action",
    "pit_panel_status",
    "price_status",
    "dividend_status",
    "low_vol_status",
    "external_state_status",
    "local_daily_status",
    "order_health_status",
    "paper_tracking_status",
    "sample_size_policy",
    "strategy_return",
    "benchmark_return",
    "excess_return",
    "max_drawdown",
    "sharpe",
    "trade_count",
    "dividend_count",
    "data_gate_conclusion",
    "pm_decision_packet",
]

SIDECAR_FIELDS = [
    "sidecar_id",
    "sector_id",
    "label_en",
    "label_zh",
    "sidecar_status",
    "strategy_return",
    "benchmark_return",
    "excess_return",
    "max_drawdown",
    "information_ratio",
    "strategy_volatility",
    "order_health_status",
    "comparison_to_v57f",
    "allowed_conclusion",
    "blocked_conclusion",
    "source_summary_path",
]

QUEUE_FIELDS = [
    "queue_rank",
    "sector_id",
    "owner",
    "task",
    "input_artifacts",
    "output_artifacts",
    "gate",
    "blocked_actions",
]


@dataclass(frozen=True)
class Candidate:
    sector_id: str
    label_en: str
    label_zh: str
    local_summary: Path | None
    paper_summary: Path | None
    sidecar_summary: Path | None
    route_hint: str
    sample_policy: str


@dataclass(frozen=True)
class NewSleeveObservationExecutionResult:
    output_dir: Path
    master_summary_json: Path
    master_report_md: Path
    route_table_csv: Path
    sidecar_comparison_csv: Path
    next_agent_queue_csv: Path
    packet_count: int


DEFAULT_CANDIDATES = [
    Candidate(
        "gas_water_operators",
        "Gas / water operators",
        "燃气/水务运营",
        Path("local_daily_backtests_v59b_gas_water_state_guard_repaired_2021_07")
        / "gas_water_v57b_text_debt_state_guard_v59b"
        / "summary.json",
        Path("paper_trading_signals")
        / "gas_water_v59b_promotion_queue"
        / "gas_water_v57b_text_debt_state_guard_v59b"
        / "gas_water_paper_tracking_summary.json",
        Path("local_daily_backtests_v57g_gas_water_observation_etf")
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation"
        / "summary.json",
        "first_observation",
        "normal_observation",
    ),
    Candidate(
        "home_appliances",
        "Home appliances",
        "家电",
        Path("local_daily_backtests_home_appliances_v5a5e") / "home_appliances_ocf_quality_v5a5c" / "summary.json",
        Path("paper_trading_signals")
        / "home_appliances_v5a5e_promotion_queue"
        / "home_appliances_ocf_quality_v5a5c"
        / "home_appliances_paper_tracking_summary.json",
        None,
        "second_observation",
        "normal_observation_high_drawdown_review",
    ),
    Candidate(
        "oil_gas_pipeline_integrated",
        "Oil / gas pipeline and integrated energy",
        "油气管道/综合能源",
        Path("validation_daily_v58h_oil_gas_sector_benchmark") / "oil_gas_state_conditioned_ocf_v58g" / "summary.json",
        None,
        None,
        "external_event_wait",
        "cycle_state_observation",
    ),
    Candidate(
        "food_beverage",
        "Food / beverage",
        "食品饮料",
        Path("local_daily_backtests_food_beverage_v5a9") / "food_beverage_packaged_food_ocf_quality_v5a9a" / "summary.json",
        None,
        None,
        "engineering_review_blocked",
        "engineering_needs_review",
    ),
    Candidate(
        "insurance",
        "Insurance",
        "保险",
        Path("local_daily_backtests_insurance_v53g") / "insurance_pev_value_v53g" / "summary.json",
        None,
        None,
        "specialist_observation",
        "small_sample_specialist",
    ),
    Candidate(
        "telecom_operators",
        "Telecom operators",
        "电信运营商",
        Path("local_daily_backtests_v58_telecom_overlay_matched")
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
        / "summary.json",
        None,
        Path("local_daily_backtests_v58_telecom_overlay_matched")
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
        / "summary.json",
        "small_sample_diagnostic",
        "small_sample_capped_observation",
    ),
    Candidate(
        "coal",
        "Coal",
        "煤炭",
        Path("local_daily_backtests_coal_v52b") / "coal_cashflow_cycle_value_v52b_capex_policy" / "summary.json",
        None,
        None,
        "failed_data_gate",
        "cyclical_data_gate_failed",
    ),
]


def run_new_sleeve_observation_execution(
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    v57f_config: Path = DEFAULT_V57F_CONFIG,
    v57f_summary: Path = DEFAULT_V57F_SUMMARY,
    sleeve_registry: Path = DEFAULT_SLEEVE_REGISTRY,
    status_registry: Path = DEFAULT_STATUS_REGISTRY,
    candidates: list[Candidate] | None = None,
) -> NewSleeveObservationExecutionResult:
    items = candidates or DEFAULT_CANDIDATES
    config = _read_json_if_exists(v57f_config)
    v57f = _read_json_if_exists(v57f_summary)
    sleeves = {str(row.get("sector_id") or ""): row for row in read_csv_rows_if_exists(sleeve_registry)}
    registry = _read_json_if_exists(status_registry)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet_dir = out_dir / "pm_decision_packets"
    packet_dir.mkdir(parents=True, exist_ok=True)

    freeze = _freeze_packet(config, v57f, v57f_config, v57f_summary)
    route_rows: list[dict[str, Any]] = []
    sidecar_rows: list[dict[str, Any]] = []
    packet_paths: list[str] = []

    for candidate in items:
        evidence = _candidate_evidence(candidate, sleeves.get(candidate.sector_id, {}), registry)
        route = _route_candidate(candidate, evidence)
        packet_json = packet_dir / f"{candidate.sector_id}_pm_decision_packet.json"
        packet_md = packet_dir / f"{candidate.sector_id}_pm_decision_packet.md"
        route["pm_decision_packet"] = str(packet_md)
        write_json_file(packet_json, _packet_payload(candidate, route, evidence))
        packet_md.write_text(_packet_markdown(candidate, route, evidence), encoding="utf-8")
        packet_paths.append(str(packet_md))
        route_rows.append(route)
        sidecar_rows.append(_sidecar_row(candidate, evidence, v57f))

    next_queue = _next_agent_queue(route_rows)
    route_table_csv = out_dir / "candidate_route_table.csv"
    sidecar_comparison_csv = out_dir / "sidecar_basket_comparison.csv"
    next_agent_queue_csv = out_dir / "next_agent_queue.csv"
    master_summary_json = out_dir / "new_sleeve_execution_master_summary.json"
    master_report_md = out_dir / "new_sleeve_execution_master_report.md"

    write_csv_rows(route_table_csv, ROUTE_FIELDS, route_rows, encoding="utf-8-sig")
    write_csv_rows(sidecar_comparison_csv, SIDECAR_FIELDS, sidecar_rows, encoding="utf-8-sig")
    write_csv_rows(next_agent_queue_csv, QUEUE_FIELDS, next_queue, encoding="utf-8-sig")

    summary = _master_summary(freeze, route_rows, sidecar_rows, next_queue, packet_paths)
    write_json_file(master_summary_json, summary)
    master_report_md.write_text(_master_report(summary, route_rows, sidecar_rows, next_queue), encoding="utf-8")

    return NewSleeveObservationExecutionResult(
        output_dir=out_dir,
        master_summary_json=master_summary_json,
        master_report_md=master_report_md,
        route_table_csv=route_table_csv,
        sidecar_comparison_csv=sidecar_comparison_csv,
        next_agent_queue_csv=next_agent_queue_csv,
        packet_count=len(packet_paths),
    )


def _freeze_packet(config: dict[str, Any], v57f: dict[str, Any], config_path: Path, summary_path: Path) -> dict[str, Any]:
    sleeves = [str(row.get("sector_id") or "") for row in config.get("sectors", [])]
    expected = ["bank", "utilities_electricity", "highway_infrastructure", "port_rail_infrastructure"]
    health = v57f.get("rebalance_order_health", {}) if isinstance(v57f, dict) else {}
    metrics = v57f.get("metrics", {}) if isinstance(v57f, dict) else {}
    return {
        "freeze_status": "pass" if sleeves == expected else "needs_review",
        "core_sleeves": sleeves,
        "expected_core_sleeves": expected,
        "config_path": str(config_path),
        "summary_path": str(summary_path),
        "locked_metrics": {
            "strategy_return": metrics.get("strategy_return"),
            "benchmark_return": metrics.get("benchmark_return"),
            "excess_return": metrics.get("excess_return"),
            "max_drawdown": metrics.get("max_drawdown"),
            "sharpe": metrics.get("sharpe"),
            "trade_count": v57f.get("trade_count"),
            "dividend_count": v57f.get("dividend_count"),
            "rebalance_signal_count": health.get("rebalance_signal_count"),
            "order_health": "needs_review" if health.get("needs_review") else "pass" if health else "unknown",
        },
        "blocked_actions": [
            "do_not_modify_V57f_factors",
            "do_not_modify_V57f_weights",
            "do_not_add_observation_sleeves_to_V57f",
            "do_not_claim_accepted_or_platform_replication_passed",
        ],
    }


def _candidate_evidence(candidate: Candidate, sleeve: dict[str, str], registry: dict[str, Any]) -> dict[str, Any]:
    local = _read_json_if_exists(candidate.local_summary) if candidate.local_summary else {}
    paper = _read_json_if_exists(candidate.paper_summary) if candidate.paper_summary else {}
    sidecar = _read_json_if_exists(candidate.sidecar_summary) if candidate.sidecar_summary else {}
    corpus = _registry_corpus(registry, candidate.sector_id)
    health = local.get("rebalance_order_health", {}) if isinstance(local, dict) else {}
    metrics = local.get("metrics", {}) if isinstance(local, dict) else {}
    summary_dir = candidate.local_summary.parent if candidate.local_summary else None
    trade_count = local.get("trade_count")
    if trade_count is None:
        trade_count = _count_csv_rows(summary_dir / "trades.csv") if summary_dir else None
    dividend_count = local.get("dividend_count")
    if dividend_count is None:
        dividend_count = _sum_dividend_counts(local)
    if dividend_count is None:
        dividend_count = _count_csv_rows(summary_dir / "dividends.csv") if summary_dir else None
    return {
        "sleeve": sleeve,
        "local": local,
        "paper": paper,
        "sidecar": sidecar,
        "corpus": corpus,
        "pit_panel_status": _status_from_bool(_yes(sleeve.get("panel_exists")) or _contains(corpus, ["panel.csv", "pit_panel", "panel_with", "panel"])),
        "price_status": _status_from_bool(_yes(sleeve.get("price_exists")) or bool(local)),
        "dividend_status": _dividend_status(dividend_count, candidate),
        "low_vol_status": _status_from_bool(_contains(corpus, ["low_vol", "volatility_120d"]) or "volatility" in json.dumps(local).lower()),
        "external_state_status": _external_state_status(candidate, corpus),
        "local_daily_status": "pass" if local else "missing",
        "order_health_status": _order_health_status(health, candidate),
        "paper_tracking_status": "ready" if paper else _paper_default(candidate),
        "metrics": metrics,
        "trade_count": trade_count if trade_count is not None else "",
        "dividend_count": dividend_count if dividend_count is not None else "",
    }


def _route_candidate(candidate: Candidate, evidence: dict[str, Any]) -> dict[str, Any]:
    metrics = evidence["metrics"]
    route_status, gate, owner, allowed, blocked = _route_policy(candidate, evidence)
    return {
        "sector_id": candidate.sector_id,
        "label_en": candidate.label_en,
        "label_zh": candidate.label_zh,
        "route_status": route_status,
        "pm_gate": gate,
        "next_owner": owner,
        "allowed_next_action": allowed,
        "blocked_action": blocked,
        "pit_panel_status": evidence["pit_panel_status"],
        "price_status": evidence["price_status"],
        "dividend_status": evidence["dividend_status"],
        "low_vol_status": evidence["low_vol_status"],
        "external_state_status": evidence["external_state_status"],
        "local_daily_status": evidence["local_daily_status"],
        "order_health_status": evidence["order_health_status"],
        "paper_tracking_status": evidence["paper_tracking_status"],
        "sample_size_policy": candidate.sample_policy,
        "strategy_return": _num(metrics.get("strategy_return")),
        "benchmark_return": _num(metrics.get("benchmark_return")),
        "excess_return": _num(metrics.get("excess_return")),
        "max_drawdown": _num(metrics.get("max_drawdown")),
        "sharpe": _num(metrics.get("sharpe")),
        "trade_count": evidence["trade_count"],
        "dividend_count": evidence["dividend_count"],
        "data_gate_conclusion": _data_gate_conclusion(evidence),
        "pm_decision_packet": "",
    }


def _route_policy(candidate: Candidate, evidence: dict[str, Any]) -> tuple[str, str, str, str, str]:
    order = evidence["order_health_status"]
    local = evidence["local_daily_status"]
    paper = evidence["paper_tracking_status"]
    if candidate.sector_id == "gas_water_operators":
        return (
            "observation_paper_tracking",
            "sidecar_diagnostic_complete_wait_forward",
            "Engineering Agent",
            "Refresh gas/water observation paper tracking when the next clean signal window arrives.",
            "Do not add gas/water to frozen V57f.",
        )
    if candidate.sector_id == "home_appliances":
        return (
            "observation_paper_tracking",
            "drawdown_and_state_review_continue_paper",
            "Engineering Agent",
            "Keep home appliances in paper tracking and monitor drawdown/state explanations.",
            "Do not upgrade by high historical return.",
        )
    if candidate.sector_id == "oil_gas_pipeline_integrated":
        return (
            "external_event_wait",
            "wait_for_platform_or_forward_event",
            "Project Manager Agent",
            "Park oil/gas until external event, platform export, or forward window appears.",
            "Do not rerun parameters for returns.",
        )
    if candidate.sector_id == "food_beverage":
        if order == "needs_review" or local == "pass":
            return (
                "engineering_needs_review",
                "rebalance_order_health_and_dividend_review",
                "Engineering Agent",
                "Repair or explain order-health, skipped-order and dividend issues.",
                "Do not ignore order-health or promote before repair.",
            )
        return (
            "research_data_gate_repair",
            "research_repair_before_engineering",
            "Research Agent",
            "Repair packaged-food PIT/state evidence before local daily simulation.",
            "Do not run sidecar basket yet.",
        )
    if candidate.sector_id == "insurance":
        return (
            "research_data_gate_repair",
            "specialist_ev_nbv_platform_attribution_gate",
            "Research Agent",
            "Keep insurance as specialist observation; repair EV/NBV/P/EV or wait for platform attribution.",
            "Do not add insurance to ETF core.",
        )
    if candidate.sector_id == "telecom_operators":
        return (
            "sidecar_candidate_needs_forward",
            "small_sample_capped_observation_gate",
            "Project Manager Agent",
            "Keep capped telecom overlay as diagnostic observation and wait for forward evidence.",
            "Do not let telecom replace V57f.",
        )
    if candidate.sector_id == "coal":
        return (
            "archived_not_current_mandate",
            "cyclical_data_gate_repair_only",
            "Research Agent",
            "Archive coal unless official commodity/output/inventory/spread and PIT business exposure data are repaired.",
            "Do not run JoinQuant or accept the high-return failed sample.",
        )
    if paper == "ready":
        return ("observation_paper_tracking", "paper_tracking_only", "Engineering Agent", "Continue paper tracking.", "Do not add to V57f.")
    return ("research_data_gate_repair", "research_repair", "Research Agent", "Repair data gate.", "Do not model.")


def _sidecar_row(candidate: Candidate, evidence: dict[str, Any], v57f: dict[str, Any]) -> dict[str, Any]:
    sidecar = evidence["sidecar"] or {}
    source = candidate.sidecar_summary if candidate.sidecar_summary else None
    if sidecar:
        metrics = sidecar.get("metrics", {})
        health = sidecar.get("rebalance_order_health", {})
        status = "completed_not_core_promotion"
    else:
        metrics = {}
        health = {}
        status = _sidecar_missing_status(candidate)
    v57f_metrics = v57f.get("metrics", {}) if isinstance(v57f, dict) else {}
    delta_return = _maybe_delta(metrics.get("strategy_return"), v57f_metrics.get("strategy_return"))
    delta_dd = _maybe_delta(metrics.get("max_drawdown"), v57f_metrics.get("max_drawdown"))
    return {
        "sidecar_id": f"v57f_plus_{candidate.sector_id}",
        "sector_id": candidate.sector_id,
        "label_en": candidate.label_en,
        "label_zh": candidate.label_zh,
        "sidecar_status": status,
        "strategy_return": _num(metrics.get("strategy_return")),
        "benchmark_return": _num(metrics.get("benchmark_return")),
        "excess_return": _num(metrics.get("excess_return")),
        "max_drawdown": _num(metrics.get("max_drawdown")),
        "information_ratio": _num(metrics.get("information_ratio")),
        "strategy_volatility": _num(metrics.get("strategy_volatility")),
        "order_health_status": _order_health_status(health, candidate) if sidecar else "not_applicable",
        "comparison_to_v57f": _comparison_text(delta_return, delta_dd) if sidecar else "No sidecar basket has been run or approved for this candidate.",
        "allowed_conclusion": _allowed_sidecar_conclusion(candidate),
        "blocked_conclusion": "Do not add the candidate to frozen V57f or select by historical return.",
        "source_summary_path": str(source or ""),
    }


def _next_agent_queue(route_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    priority = [
        "engineering_needs_review",
        "observation_paper_tracking",
        "sidecar_candidate_needs_forward",
        "research_data_gate_repair",
        "external_event_wait",
        "archived_not_current_mandate",
    ]
    actionable = [row for row in route_rows if row["route_status"] in {"engineering_needs_review", "observation_paper_tracking"}]
    rows = actionable or [row for row in route_rows if row["route_status"] not in {"external_event_wait", "archived_not_current_mandate"}]
    rows.sort(key=lambda row: (priority.index(row["route_status"]) if row["route_status"] in priority else 99, row["sector_id"]))
    if not rows:
        return []
    selected = rows[0]
    return [
        {
            "queue_rank": "1",
            "sector_id": selected["sector_id"],
            "owner": selected["next_owner"],
            "task": selected["allowed_next_action"],
            "input_artifacts": "candidate_route_table.csv; sidecar_basket_comparison.csv; PM decision packet",
            "output_artifacts": "checkpoint_or_repair_packet",
            "gate": selected["pm_gate"],
            "blocked_actions": "do_not_modify_V57f; do_not_tune_returns; do_not_add_observation_sleeve_to_core; do_not_claim_platform_replication",
        }
    ]


def _packet_payload(candidate: Candidate, route: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at_utc": _now(),
        "sector_id": candidate.sector_id,
        "label_en": candidate.label_en,
        "label_zh": candidate.label_zh,
        "route_status": route["route_status"],
        "pm_gate": route["pm_gate"],
        "data_gate": {
            key: route[key]
            for key in [
                "pit_panel_status",
                "price_status",
                "dividend_status",
                "low_vol_status",
                "external_state_status",
                "local_daily_status",
                "order_health_status",
                "paper_tracking_status",
            ]
        },
        "metrics": {
            "strategy_return": route["strategy_return"],
            "benchmark_return": route["benchmark_return"],
            "excess_return": route["excess_return"],
            "max_drawdown": route["max_drawdown"],
            "sharpe": route["sharpe"],
        },
        "allowed_next_action": route["allowed_next_action"],
        "blocked_action": route["blocked_action"],
        "source_paths": {
            "local_summary": str(candidate.local_summary or ""),
            "paper_summary": str(candidate.paper_summary or ""),
            "sidecar_summary": str(candidate.sidecar_summary or ""),
        },
        "pm_rule": "Observation sleeve packets cannot modify frozen V57f or imply strategy acceptance.",
    }


def _packet_markdown(candidate: Candidate, route: dict[str, Any], evidence: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {candidate.label_en} PM Decision Packet",
            "",
            f"Created at UTC: `{_now()}`",
            "",
            f"Route status: `{route['route_status']}`",
            f"PM gate: `{route['pm_gate']}`",
            f"Next owner: `{route['next_owner']}`",
            "",
            "## Data Gate",
            "",
            f"- PIT panel: `{route['pit_panel_status']}`",
            f"- Price: `{route['price_status']}`",
            f"- Dividend: `{route['dividend_status']}`",
            f"- Low-vol: `{route['low_vol_status']}`",
            f"- External state: `{route['external_state_status']}`",
            f"- Local daily: `{route['local_daily_status']}`",
            f"- Order health: `{route['order_health_status']}`",
            f"- Paper tracking: `{route['paper_tracking_status']}`",
            "",
            "## Metrics Snapshot",
            "",
            f"- Strategy return: `{_pct(route['strategy_return'])}`",
            f"- Benchmark return: `{_pct(route['benchmark_return'])}`",
            f"- Excess return: `{_pct(route['excess_return'])}`",
            f"- Max drawdown: `{_pct(route['max_drawdown'])}`",
            f"- Sharpe: `{route['sharpe']}`",
            "",
            "## PM Boundary",
            "",
            f"Allowed: {route['allowed_next_action']}",
            "",
            f"Blocked: {route['blocked_action']}",
            "",
            "This packet is observation routing only. It does not approve V57f modification, platform replication, accepted strategy status, or live trading.",
            "",
        ]
    )


def _master_summary(
    freeze: dict[str, Any],
    route_rows: list[dict[str, Any]],
    sidecar_rows: list[dict[str, Any]],
    next_queue: list[dict[str, str]],
    packet_paths: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at_utc": _now(),
        "project": "v5_new_sleeve_observation_execution",
        "status": "all_candidates_routed_no_v57f_change",
        "freeze": freeze,
        "route_status_counts": _count_values(route_rows, "route_status"),
        "sidecar_status_counts": _count_values(sidecar_rows, "sidecar_status"),
        "candidate_count": len(route_rows),
        "pm_decision_packet_count": len(packet_paths),
        "pm_decision_packets": packet_paths,
        "next_agent_queue": next_queue,
        "hard_rules": [
            "V57f core config remains unchanged.",
            "Observation sleeves cannot be added to V57f from this run.",
            "Historical returns cannot promote a sleeve.",
            "Accepted/platform/live statuses remain blocked.",
        ],
    }


def _master_report(
    summary: dict[str, Any],
    route_rows: list[dict[str, Any]],
    sidecar_rows: list[dict[str, Any]],
    next_queue: list[dict[str, str]],
) -> str:
    lines = [
        "# New Sleeve Observation Execution Master Report",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## PM Result",
        "",
        "All requested candidates were routed without changing frozen V57f.",
        "",
        f"Freeze status: `{summary['freeze']['freeze_status']}`",
        "",
        "## Candidate Routing",
        "",
        "| Sector | Route | Gate | Owner | Order health | Paper | Allowed next action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in route_rows:
        lines.append(
            f"| `{row['sector_id']}` | `{row['route_status']}` | `{row['pm_gate']}` | `{row['next_owner']}` | `{row['order_health_status']}` | `{row['paper_tracking_status']}` | {row['allowed_next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Sidecar Basket Diagnostics",
            "",
            "| Sector | Status | Return | Excess | Drawdown | Allowed conclusion |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in sidecar_rows:
        lines.append(
            f"| `{row['sector_id']}` | `{row['sidecar_status']}` | {_pct(row['strategy_return'])} | {_pct(row['excess_return'])} | {_pct(row['max_drawdown'])} | {row['allowed_conclusion']} |"
        )
    lines.extend(
        [
            "",
            "## Next Unique Agent Queue",
            "",
            "| Rank | Sector | Owner | Gate | Task |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in next_queue:
        lines.append(f"| {row['queue_rank']} | `{row['sector_id']}` | `{row['owner']}` | `{row['gate']}` | {row['task']} |")
    lines.extend(
        [
            "",
            "## Hard Rules",
            "",
            "- Do not modify V57f factors, weights, sleeves or rebalance rules.",
            "- Do not rank by historical return.",
            "- Do not claim `accepted_strategy`, `platform_replication_passed` or `live_trading_approved`.",
            "- Each candidate ends as observe, sidecar wait, engineering review, research repair, external wait or archive.",
            "",
        ]
    )
    return "\n".join(lines)


def _registry_corpus(registry: dict[str, Any], sector_id: str) -> str:
    tokens = _sector_tokens(sector_id)
    parts: list[str] = []
    for item in registry.get("strategies", []):
        text = json.dumps(item, ensure_ascii=False).lower()
        if any(token in text for token in tokens):
            parts.append(text)
    refs = registry.get("references", {})
    if isinstance(refs, dict):
        for key, value in refs.items():
            text = f"{key} {value}".lower()
            if any(token in text for token in tokens):
                parts.append(text)
    return "\n".join(parts)


def _sector_tokens(sector_id: str) -> list[str]:
    mapping = {
        "gas_water_operators": ["gas_water", "gas / water", "water tariff"],
        "home_appliances": ["home_appliances", "home appliances"],
        "oil_gas_pipeline_integrated": ["oil_gas", "oil / gas"],
        "food_beverage": ["food_beverage", "food / beverage", "packaged_food"],
        "insurance": ["insurance", "ev / nbv", "pev"],
        "telecom_operators": ["telecom", "arpu"],
        "coal": ["coal", "cyclical_sector"],
    }
    return mapping.get(sector_id, [sector_id])


def _data_gate_conclusion(evidence: dict[str, Any]) -> str:
    checks = [
        evidence["pit_panel_status"],
        evidence["price_status"],
        evidence["dividend_status"],
        evidence["low_vol_status"],
        evidence["external_state_status"],
        evidence["local_daily_status"],
        evidence["order_health_status"],
    ]
    if "needs_review" in checks:
        return "needs_review"
    if "missing" in checks or "blocked" in checks:
        return "blocked_or_missing"
    return "pass_or_not_applicable"


def _external_state_status(candidate: Candidate, corpus: str) -> str:
    if candidate.sector_id in {"coal"}:
        return "blocked"
    if candidate.sector_id in {"oil_gas_pipeline_integrated", "gas_water_operators", "food_beverage"}:
        return "pass" if _contains(corpus, ["external_state", "state_guard", "true_state", "cycle_state"]) else "needs_review"
    if candidate.sector_id in {"insurance"}:
        return "needs_review"
    return "not_applicable"


def _dividend_status(dividend_count: Any, candidate: Candidate) -> str:
    count = to_float(dividend_count)
    if count is not None and count > 0:
        return "pass"
    if candidate.sector_id == "coal":
        return "unknown"
    return "missing"


def _order_health_status(health: dict[str, Any], candidate: Candidate) -> str:
    if health:
        return "needs_review" if health.get("needs_review") else "pass"
    if candidate.sector_id in {"coal", "insurance", "telecom_operators"}:
        return "unknown"
    return "needs_review"


def _paper_default(candidate: Candidate) -> str:
    if candidate.sector_id in {"oil_gas_pipeline_integrated"}:
        return "external_event_wait"
    if candidate.sector_id == "coal":
        return "not_allowed"
    return "missing"


def _sidecar_missing_status(candidate: Candidate) -> str:
    if candidate.sector_id in {"home_appliances", "insurance", "oil_gas_pipeline_integrated", "food_beverage"}:
        return "not_run_pending_pm_gate"
    if candidate.sector_id == "coal":
        return "not_allowed_archived"
    return "not_run"


def _allowed_sidecar_conclusion(candidate: Candidate) -> str:
    if candidate.sidecar_summary:
        return "Observation diagnostic only; forward evidence is still required."
    if candidate.sector_id == "coal":
        return "No sidecar allowed until cyclical data gate is repaired."
    return "May be considered later only after PM gate; no V57f change now."


def _comparison_text(delta_return: float | None, delta_dd: float | None) -> str:
    parts = []
    if delta_return is not None:
        parts.append(f"return_delta_vs_v57f={delta_return:.4f}")
    if delta_dd is not None:
        parts.append(f"max_drawdown_delta_vs_v57f={delta_dd:.4f}")
    return "; ".join(parts)


def _maybe_delta(value: Any, base: Any) -> float | None:
    parsed = to_float(value)
    parsed_base = to_float(base)
    if parsed is None or parsed_base is None:
        return None
    return parsed - parsed_base


def _sum_dividend_counts(local: dict[str, Any]) -> float | None:
    counts = local.get("data_coverage", {}).get("dividend_file_event_counts") if isinstance(local, dict) else None
    if not isinstance(counts, dict):
        return None
    values = [to_float(value) or 0.0 for value in counts.values()]
    return sum(values)


def _count_csv_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    return len(read_csv_rows_if_exists(path))


def _count_values(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field) or "")
        result[value] = result.get(value, 0) + 1
    return result


def _read_json_if_exists(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        return {}
    return payload


def _contains(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(needle in lower for needle in needles)


def _status_from_bool(value: bool) -> str:
    return "pass" if value else "missing"


def _yes(value: Any) -> bool:
    return str(value or "").strip().lower() in {"yes", "true", "1", "pass", "passed"}


def _num(value: Any) -> str:
    parsed = to_float(value)
    return "" if parsed is None else f"{parsed:.12g}"


def _pct(value: Any) -> str:
    parsed = to_float(value)
    return "" if parsed is None else f"{parsed * 100:.2f}%"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
