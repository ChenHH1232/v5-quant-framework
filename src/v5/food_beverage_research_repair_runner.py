from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from v5.agent_loop_packet_runner import create_agent_loop_packet
from v5.formal_validation_runner import run_formal_validation
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "consumer_working_capital_state_v5a6" / "food_beverage" / "panel_with_working_capital_state.csv"
DEFAULT_OUT_DIR = Path("validation_formal_v5a9_food_beverage_research_repair")
DEFAULT_PACKET_DIR = Path("agent_loop_packets_v5a9") / "food_beverage_research_repair"

FLOW_FIELDS = ["stage", "owner", "input", "action", "output", "gate", "status"]
RESULT_FIELDS = [
    "strategy_id",
    "hypothesis",
    "panel_path",
    "summary_path",
    "row_count",
    "date_count",
    "security_count",
    "median_codes_per_date",
    "selection_count",
    "equal_weight_return",
    "candidate_return",
    "negative_rolling_windows",
    "mean_ic",
    "mean_rankic",
    "common_sample_securities",
    "pm_gate",
    "pm_decision",
    "blocker",
]


@dataclass(frozen=True)
class FoodBeverageResearchRepairResult:
    output_dir: Path
    flow_table_csv: Path
    result_csv: Path
    summary_json: Path
    report_path: Path
    agent_packet_json: Path
    status: str
    next_gate: str


def run_food_beverage_research_repair(
    panel_csv: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
    agent_packet_dir: Path = DEFAULT_PACKET_DIR,
) -> FoodBeverageResearchRepairResult:
    rows = read_csv_rows(panel_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_dir = out_dir / "panels"
    spec_dir = out_dir / "specs"
    formal_dir = out_dir / "formal"
    panel_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    candidate_defs = _candidate_definitions()
    result_rows: list[dict[str, Any]] = []
    for candidate in candidate_defs:
        candidate_rows = _filter_rows(rows, candidate)
        profile = _profile(candidate_rows)
        selection_count = _selection_count(profile["median_codes_per_date"])
        panel_path = panel_dir / f"{candidate['strategy_id']}.csv"
        spec_path = spec_dir / f"{candidate['strategy_id']}.json"
        write_csv_rows(panel_path, _fieldnames(candidate_rows), candidate_rows)
        write_json_file(spec_path, _spec(candidate, selection_count))
        report_path = run_formal_validation(spec_path, panel_path, formal_dir)
        summary_path = report_path.with_name("formal_validation_summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result_rows.append(_result_row(candidate, panel_path, summary_path, profile, selection_count, summary))

    status, next_gate = _pm_status(result_rows)
    flow_rows = _flow_rows(status, next_gate)
    summary_payload = {
        "schema_version": 1,
        "dataset": "food_beverage_research_repair_v5a9",
        "experiment_layer": "research_pit_validation",
        "status": status,
        "next_gate": next_gate,
        "input_panel": str(panel_csv),
        "flow_table_csv": str(out_dir / "food_beverage_research_repair_flow_table.csv"),
        "result_csv": str(out_dir / "food_beverage_research_repair_results.csv"),
        "report_path": str(out_dir / "food_beverage_research_repair_report.md"),
        "candidate_count": len(result_rows),
        "candidate_results": result_rows,
        "pm_rules": [
            "This is Research/Quant repair only; it cannot accept a strategy.",
            "Food/beverage may enter Engineering only if a subsector/business-state hypothesis has enough PIT sample width and stable evidence.",
            "Do not tune factor weights, selection count, timing or subindustry membership based on 2021-2026 returns.",
            "Do not send small-sample specialist watchlists to Engineering without a separate PM approval gate.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    flow_table_csv = out_dir / "food_beverage_research_repair_flow_table.csv"
    result_csv = out_dir / "food_beverage_research_repair_results.csv"
    summary_json = out_dir / "food_beverage_research_repair_summary.json"
    report_md = out_dir / "food_beverage_research_repair_report.md"
    write_csv_rows(flow_table_csv, FLOW_FIELDS, flow_rows)
    write_csv_rows(result_csv, RESULT_FIELDS, result_rows)
    write_json_file(summary_json, summary_payload)
    report_md.write_text(_report(summary_payload, flow_rows, result_rows), encoding="utf-8")

    packet = create_agent_loop_packet(
        packet_type="checkpoint_packet" if status == "food_beverage_engineering_handoff_ready" else "blocker_packet",
        objective="food_beverage_subsector_business_state_repair_until_engineering_gate",
        agent="Project Manager Agent",
        experiment_layer="pm_decision_gate",
        decision="return_to_research" if status != "food_beverage_engineering_handoff_ready" else "return_to_engineering",
        next_owner="Research Agent" if status != "food_beverage_engineering_handoff_ready" else "Engineering Agent",
        out_dir=agent_packet_dir,
        timebox_minutes=60,
        artifacts=[str(flow_table_csv), str(result_csv), str(summary_json), str(report_md)],
        evidence=[
            f"{row['strategy_id']}: gate={row['pm_gate']} decision={row['pm_decision']} blocker={row['blocker']}"
            for row in result_rows
        ],
        blockers=[] if status == "food_beverage_engineering_handoff_ready" else [row["blocker"] for row in result_rows if row["blocker"]],
        stop_rule_status="not_triggered" if status == "food_beverage_engineering_handoff_ready" else "blocked_by_evidence_gate",
        allowed_next_action=next_gate,
        restart_condition="Restart only with a new Research hypothesis, wider PIT business-quality subset, or PM-approved small-sample specialist sleeve policy.",
        loop_id="food_beverage_research_repair_v5a9",
    )
    summary_payload["agent_packet"] = {"packet_path": str(packet.packet_path), "report_path": str(packet.report_path)}
    write_json_file(summary_json, summary_payload)
    return FoodBeverageResearchRepairResult(out_dir, flow_table_csv, result_csv, summary_json, report_md, packet.packet_path, status, next_gate)


def _candidate_definitions() -> list[dict[str, Any]]:
    return [
        {
            "strategy_id": "food_beverage_packaged_food_ocf_quality_v5a9a",
            "hypothesis": "branded_packaged_food_ocf_quality",
            "subindustries": {"sw_condiments", "sw_snack_food"},
            "guard": "none",
            "factors": ["operating_cash_flow_yield", "operating_cash_flow_to_net_profit"],
            "weights": {"operating_cash_flow_yield": 0.7, "operating_cash_flow_to_net_profit": 0.3},
            "rationale": "Combine asset-light packaged-food subindustries where OCF quality is economically interpretable; keep OCF conversion as support.",
        },
        {
            "strategy_id": "food_beverage_packaged_food_high_ocf_wc_guard_v5a9b",
            "hypothesis": "branded_packaged_food_high_ocf_with_working_capital_guard",
            "subindustries": {"sw_condiments", "sw_snack_food"},
            "guard": "working_capital_pressure",
            "factors": ["operating_cash_flow_yield"],
            "weights": {"operating_cash_flow_yield": 1.0},
            "rationale": "Apply the fixed V5a.7 working-capital stress guard to the wider packaged-food pool, then use OCF yield as the only positive factor.",
        },
    ]


def _filter_rows(rows: list[dict[str, str]], candidate: dict[str, Any]) -> list[dict[str, str]]:
    selected = [row for row in rows if row.get("sub_industry") in candidate["subindustries"]]
    if candidate["guard"] == "working_capital_pressure":
        selected = [
            row
            for row in selected
            if str(row.get("high_inventory_pressure_flag") or "").lower() != "true"
            and str(row.get("high_receivables_pressure_flag") or "").lower() != "true"
            and str(row.get("high_working_capital_pressure_flag") or "").lower() != "true"
        ]
    return selected


def _profile(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_date: dict[str, set[str]] = {}
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        if trade_date and code:
            by_date.setdefault(trade_date, set()).add(code)
    counts = [len(codes) for codes in by_date.values()]
    return {
        "row_count": len(rows),
        "date_count": len(by_date),
        "security_count": len({row.get("code") for row in rows if row.get("code")}),
        "median_codes_per_date": int(median(counts)) if counts else 0,
        "min_codes_per_date": min(counts) if counts else 0,
        "max_codes_per_date": max(counts) if counts else 0,
    }


def _selection_count(median_codes_per_date: int) -> int:
    return max(4, min(8, int(median_codes_per_date * 0.35))) if median_codes_per_date else 0


def _spec(candidate: dict[str, Any], selection_count: int) -> dict[str, Any]:
    factors = [
        {
            "name": name,
            "source": "JoinQuant/DataJQ PIT financial fields and V5a.6 working-capital state panel",
            "role": "primary_cash_generation" if name == "operating_cash_flow_yield" else "cash_conversion_quality",
            "direction": "higher_is_better",
            "definition": name,
            "as_of": "trade_date_lagged",
            "disclosure_lag_days": 1,
            "missing_policy": "drop_security",
        }
        for name in candidate["factors"]
    ]
    return {
        "meta": {
            "strategy_id": candidate["strategy_id"],
            "name": f"{candidate['hypothesis']} V5a.9",
            "objective": candidate["rationale"],
        },
        "universe": {
            "name": "food_beverage:packaged_food",
            "construction": "PIT food/beverage panel filtered to sw_condiments and sw_snack_food; optional fixed working-capital guard.",
            "point_in_time": True,
            "minimum_rebalance_coverage_ratio": 0.8,
        },
        "data": {
            "vendor": "JoinQuant/DataJQ PIT financial fields, real daily prices, cash-dividend panel and V5a.6 working-capital state runner",
            "price_frequency": "quarterly_signal_panel",
            "financial_as_of_policy": "vendor_get_fundamentals_date_proxy",
            "window": {"research_start": "2021-05-01", "research_end": "2026-05-31"},
        },
        "signals": {
            "factors": factors,
            "scoring": {
                "method": "weighted_composite",
                "normalization_scope": "rebalance_cross_section",
                "weights": candidate["weights"],
                "min_factor_count": len(candidate["factors"]),
                "value_trap_guard": "No extra scorer guard; any working-capital guard is applied by the input panel.",
            },
        },
        "schedule": {"signal_frequency": "quarterly", "rebalance_frequency": "quarterly"},
        "portfolio": {"selection_count": selection_count, "weighting": "equal_weight_research_candidate", "max_position_weight": 0.25},
        "risk": {"defensive_asset": "cash", "defensive_rule": {"enabled": False}},
        "validation": {
            "method": "rolling",
            "train_years": 3,
            "test_years": 1,
            "weak_years": ["2021", "2022", "2024", "2026"],
            "baselines": [
                {"name": "equal_weight_packaged_food", "mode": "equal_all"},
                {"name": "candidate_current", "mode": "composite", "selection_count": selection_count},
            ],
            "common_sample_fields": candidate["factors"],
            "common_sample_interactions": [{"name": "common_candidate_current", "factors": candidate["factors"]}],
            "robustness": {
                "selection_counts": sorted({max(3, selection_count - 1), selection_count, selection_count + 1}),
                "weight_scale_factors": candidate["factors"],
                "weight_scales": [0.8, 1.0, 1.2],
            },
        },
        "execution": {
            "status": "not_started",
            "next_gate": "research_data_gate",
            "commission_bps": 3,
            "slippage_bps": 5,
            "suspension_policy": "skip_untradeable",
            "limit_policy": "skip_limit_blocked",
        },
        "outputs": {"save_holdings": True, "save_rebalance_signals": True, "report": "markdown"},
    }


def _result_row(
    candidate: dict[str, Any],
    panel_path: Path,
    summary_path: Path,
    profile: dict[str, Any],
    selection_count: int,
    summary: dict[str, Any],
) -> dict[str, Any]:
    equal_return = _case_return(summary, "equal_weight_packaged_food")
    candidate_return = _case_return(summary, "candidate_current")
    negative_rolling = sum(1 for row in summary.get("rolling_validation", []) if _to_float(row.get("cum_return")) is not None and (_to_float(row.get("cum_return")) or 0.0) < 0)
    first_ic = (summary.get("factor_ic_rankic") or [{}])[0]
    common = (summary.get("common_sample_interaction_tests") or [{}])[0]
    blocker = _blocker(profile, selection_count, summary, equal_return, candidate_return, negative_rolling, first_ic, common)
    pm_gate = "engineering_handoff_candidate" if not blocker else "research_repair_blocked"
    decision = (
        "can_start_engineering_local_daily_only"
        if not blocker
        else "return_to_research_or_archive_until_new_business_state_evidence"
    )
    return {
        "strategy_id": candidate["strategy_id"],
        "hypothesis": candidate["hypothesis"],
        "panel_path": str(panel_path),
        "summary_path": str(summary_path),
        "row_count": profile["row_count"],
        "date_count": profile["date_count"],
        "security_count": profile["security_count"],
        "median_codes_per_date": profile["median_codes_per_date"],
        "selection_count": selection_count,
        "equal_weight_return": equal_return,
        "candidate_return": candidate_return,
        "negative_rolling_windows": negative_rolling,
        "mean_ic": first_ic.get("mean_ic"),
        "mean_rankic": first_ic.get("mean_rankic"),
        "common_sample_securities": common.get("common_sample_securities"),
        "pm_gate": pm_gate,
        "pm_decision": decision,
        "blocker": blocker,
    }


def _blocker(
    profile: dict[str, Any],
    selection_count: int,
    summary: dict[str, Any],
    equal_return: float | None,
    candidate_return: float | None,
    negative_rolling: int,
    first_ic: dict[str, Any],
    common: dict[str, Any],
) -> str:
    leakage = summary.get("notice_date_leakage_audit") or []
    if any(row.get("status") != "pass" for row in leakage):
        return "PIT leakage audit did not pass."
    if profile["date_count"] < 18:
        return "Not enough rebalance dates for a stable food/beverage sleeve."
    if profile["security_count"] < 18 or int(common.get("common_sample_securities") or 0) < 18:
        return "Sample width remains too narrow for a normal enhanced-ETF sleeve."
    if selection_count < 6:
        return "Selection count is too small; this behaves like a specialist watchlist."
    if negative_rolling > 1:
        return "Rolling validation has too many weak windows."
    if (first_ic.get("mean_rankic") is None) or float(first_ic.get("mean_rankic") or 0.0) <= 0:
        return "Primary factor RankIC is not positive."
    if candidate_return is None or candidate_return <= 0:
        return "Candidate cumulative return is not positive; keep as diagnostic rather than Engineering handoff."
    if candidate_return is None or equal_return is None or candidate_return <= equal_return:
        return "Candidate does not beat the matched equal-weight business pool."
    return ""


def _pm_status(result_rows: list[dict[str, Any]]) -> tuple[str, str]:
    if any(row["pm_gate"] == "engineering_handoff_candidate" for row in result_rows):
        return "food_beverage_engineering_handoff_ready", "engineering_local_daily_simulation_only_no_tuning"
    return "food_beverage_research_repair_completed_not_engineering_handoff", "research_needs_new_business_state_or_archive"


def _flow_rows(status: str, next_gate: str) -> list[dict[str, str]]:
    return [
        _flow("1", "Project Manager Agent", "V5a.6 / V5a.7 / V5a.8 evidence", "Confirm parent food/beverage cannot be modeled as one pool", "repair scope", "subsector_only", "completed"),
        _flow("2", "Research Agent", "business model map", "Define packaged-food candidate: condiments + snack food, excluding liquor/dairy/processing", "fixed hypothesis", "no_return_tuning", "completed"),
        _flow("3", "Research Agent", "working-capital state panel", "Build unguarded and fixed-guard PIT panels", "candidate panels", "PIT_visible_fields_only", "completed"),
        _flow("4", "Quant Validation Agent", "candidate panels + specs", "Run formal validation, rolling, IC/RankIC, ablation and robustness", "formal packets", "research_pit_validation", "completed"),
        _flow("5", "Project Manager Agent", "formal packets", "Apply sample-width, stability and matched-baseline engineering gate", "PM decision", "no_engineering_without_gate", "completed"),
        _flow("6", "Project Manager Agent", status, "Route next owner", next_gate, "stage_gate", "completed"),
    ]


def _case_return(summary: dict[str, Any], case_name: str) -> float | None:
    for row in summary.get("baseline_tests", []):
        if row.get("case") == case_name:
            return _to_float(row.get("cum_return"))
    return None


def _to_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fieldnames(rows: list[dict[str, str]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def _flow(stage: str, owner: str, input_path: str, action: str, output: str, gate: str, status: str) -> dict[str, str]:
    return {"stage": stage, "owner": owner, "input": input_path, "action": action, "output": output, "gate": gate, "status": status}


def _report(summary: dict[str, Any], flow_rows: list[dict[str, str]], result_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5a.9 Food/Beverage Research Repair",
        "",
        f"- Status: `{summary['status']}`",
        f"- Next gate: `{summary['next_gate']}`",
        "",
        "## Detailed Flow Table",
        "",
        "| Stage | Owner | Input | Action | Output | Gate | Status |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in flow_rows:
        lines.append(f"| {row['stage']} | {row['owner']} | `{row['input']}` | {row['action']} | `{row['output']}` | `{row['gate']}` | `{row['status']}` |")
    lines.extend(["", "## Candidate Results", "", "| Strategy | Rows | Securities | Selection | Equal | Candidate | RankIC | Gate | Blocker |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"])
    for row in result_rows:
        lines.append(
            f"| `{row['strategy_id']}` | {row['row_count']} | {row['security_count']} | {row['selection_count']} | {row['equal_weight_return']} | {row['candidate_return']} | {row['mean_rankic']} | `{row['pm_gate']}` | {row['blocker']} |"
        )
    lines.extend(["", "## PM Rules", ""])
    for item in summary["pm_rules"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"
