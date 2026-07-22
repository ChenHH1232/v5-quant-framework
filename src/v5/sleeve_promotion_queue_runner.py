from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file


DEFAULT_SLEEVE_REGISTRY = Path("enhanced_etf_production_lines_v5") / "current" / "sleeve_registry.csv"
DEFAULT_STATUS_REGISTRY = Path("docs/governance/status_registry.json")
DEFAULT_OUT_DIR = Path("enhanced_etf_production_lines_v5") / "current"

DEFAULT_CANDIDATES = [
    "gas_water_operators",
    "insurance",
    "telecom_operators",
    "oil_gas_pipeline_integrated",
    "home_appliances",
    "consumer_staples_cashflow",
    "food_beverage",
]

PROMOTION_FIELDS = [
    "rank",
    "sector_id",
    "display_name",
    "production_lane",
    "promotion_lane",
    "promotion_score",
    "fit_score",
    "completion_cost",
    "risk_penalty",
    "missing_pit_data",
    "missing_real_dividends",
    "missing_low_vol_factors",
    "missing_external_state",
    "missing_local_daily_simulation",
    "missing_rebalance_order_health",
    "sample_size_too_small",
    "platform_exports_missing",
    "specialist_data_required",
    "can_enter_research",
    "can_enter_quant",
    "can_enter_engineering",
    "can_promote_to_v57f",
    "recommended_next_owner",
    "recommended_next_action",
    "pm_gate",
    "pm_note",
]

AGENT_QUEUE_FIELDS = [
    "queue_rank",
    "sector_id",
    "owner",
    "task",
    "input_artifacts",
    "output_artifacts",
    "gate",
    "blocked_actions",
]


BASE_FIT_SCORES = {
    "gas_water_operators": 88,
    "home_appliances": 82,
    "oil_gas_pipeline_integrated": 76,
    "consumer_staples_cashflow": 72,
    "food_beverage": 68,
    "insurance": 64,
    "telecom_operators": 62,
}

CASHFLOW_FIT_BONUS = {
    "observation_refresh_only": 6,
    "research_repair_queue": 0,
    "data_gate_blocked": -18,
    "archived_or_rejected": -30,
    "excluded_from_current_mandate": -40,
}


@dataclass(frozen=True)
class SleevePromotionQueueResult:
    output_dir: Path
    queue_csv: Path
    summary_json: Path
    report_path: Path
    selected_agent_queue_csv: Path
    selected_sector_id: str
    selected_owner: str
    candidate_count: int


def build_sleeve_promotion_queue(
    sleeve_registry: Path = DEFAULT_SLEEVE_REGISTRY,
    status_registry: Path = DEFAULT_STATUS_REGISTRY,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    candidate_ids: list[str] | None = None,
) -> SleevePromotionQueueResult:
    sleeve_rows = read_csv_rows_if_exists(sleeve_registry)
    if not sleeve_rows:
        raise FileNotFoundError(f"sleeve registry not found or empty: {sleeve_registry}")
    registry = _read_json(status_registry) if status_registry.exists() else {}
    ids = candidate_ids or DEFAULT_CANDIDATES
    sleeves_by_id = {str(row.get("sector_id") or ""): row for row in sleeve_rows}

    candidate_rows = []
    for sector_id in ids:
        sleeve = sleeves_by_id.get(sector_id)
        if sleeve is None:
            continue
        evidence = _collect_sector_evidence(registry, sector_id)
        candidate_rows.append(_build_candidate_row(sleeve, evidence))

    candidate_rows.sort(key=lambda row: (-float(row["promotion_score"]), float(row["completion_cost"]), row["sector_id"]))
    for index, row in enumerate(candidate_rows, start=1):
        row["rank"] = str(index)

    selected = candidate_rows[0] if candidate_rows else {}
    agent_queue_rows = _build_selected_agent_queue(selected)

    out_dir.mkdir(parents=True, exist_ok=True)
    queue_csv = out_dir / "sleeve_promotion_queue.csv"
    summary_json = out_dir / "sleeve_promotion_summary.json"
    report_path = out_dir / "sleeve_promotion_report.md"
    queue_dir = out_dir / "promotion_agent_queues"
    selected_agent_queue_csv = queue_dir / "selected_candidate_agent_queue.csv"
    selected_agent_queue_json = queue_dir / "selected_candidate_agent_queue.json"

    write_csv_rows(queue_csv, PROMOTION_FIELDS, candidate_rows)
    write_csv_rows(selected_agent_queue_csv, AGENT_QUEUE_FIELDS, agent_queue_rows)
    write_json_file(selected_agent_queue_json, agent_queue_rows)

    summary = _build_summary(
        sleeve_registry=sleeve_registry,
        status_registry=status_registry,
        queue_csv=queue_csv,
        report_path=report_path,
        selected_agent_queue_csv=selected_agent_queue_csv,
        candidate_rows=candidate_rows,
        selected=selected,
    )
    write_json_file(summary_json, summary)
    report_path.write_text(_build_report(summary, candidate_rows, agent_queue_rows), encoding="utf-8")

    return SleevePromotionQueueResult(
        output_dir=out_dir,
        queue_csv=queue_csv,
        summary_json=summary_json,
        report_path=report_path,
        selected_agent_queue_csv=selected_agent_queue_csv,
        selected_sector_id=str(selected.get("sector_id") or ""),
        selected_owner=str(selected.get("recommended_next_owner") or ""),
        candidate_count=len(candidate_rows),
    )


def _build_candidate_row(sleeve: dict[str, str], evidence: dict[str, Any]) -> dict[str, Any]:
    sector_id = str(sleeve.get("sector_id") or "")
    lane = str(sleeve.get("production_lane") or "")
    fit_score = BASE_FIT_SCORES.get(sector_id, 50) + CASHFLOW_FIT_BONUS.get(lane, -8)
    gaps = _gap_checklist(sleeve, evidence)
    completion_cost = _completion_cost(gaps, sleeve)
    risk_penalty = _risk_penalty(gaps, sleeve, evidence)
    promotion_score = fit_score - completion_cost - risk_penalty
    owner, action, gate, promotion_lane = _next_route(sleeve, evidence, gaps)
    return {
        "rank": "",
        "sector_id": sector_id,
        "display_name": sleeve.get("display_name", ""),
        "production_lane": lane,
        "promotion_lane": promotion_lane,
        "promotion_score": f"{promotion_score:.1f}",
        "fit_score": f"{fit_score:.1f}",
        "completion_cost": f"{completion_cost:.1f}",
        "risk_penalty": f"{risk_penalty:.1f}",
        **{key: _yes_no(value) for key, value in gaps.items()},
        "can_enter_research": _yes_no(owner == "Research Agent" or lane in {"research_repair_queue", "observation_refresh_only"}),
        "can_enter_quant": _yes_no(owner == "Quant Validation Agent"),
        "can_enter_engineering": _yes_no(owner == "Engineering Agent"),
        "can_promote_to_v57f": "no",
        "recommended_next_owner": owner,
        "recommended_next_action": action,
        "pm_gate": gate,
        "pm_note": _pm_note(sleeve, evidence, gaps),
    }


def _gap_checklist(sleeve: dict[str, str], evidence: dict[str, Any]) -> dict[str, bool]:
    data_gate = _lower(sleeve.get("data_gate"))
    burden = _lower(sleeve.get("external_state_burden"))
    sample = _lower(sleeve.get("sample_size_risk"))
    corpus = evidence["corpus"]
    return {
        "missing_pit_data": not (_yes(sleeve.get("panel_exists")) or evidence["has_pit_panel"]),
        "missing_real_dividends": not (_yes(sleeve.get("dividend_exists")) or evidence["has_dividend"]),
        "missing_low_vol_factors": not evidence["has_low_vol"],
        "missing_external_state": _state_required(data_gate, burden, corpus) and not evidence["has_external_state"],
        "missing_local_daily_simulation": not evidence["has_local_daily"],
        "missing_rebalance_order_health": not evidence["has_rebalance_order_health"],
        "sample_size_too_small": "high" in sample or "small_sample" in corpus or "only three" in corpus or "only five" in corpus,
        "platform_exports_missing": evidence["platform_exports_missing"],
        "specialist_data_required": "specialist" in data_gate or "specialist" in corpus or "ev / nbv" in corpus or "arpu" in corpus,
    }


def _completion_cost(gaps: dict[str, bool], sleeve: dict[str, str]) -> float:
    cost = 0.0
    weights = {
        "missing_pit_data": 18,
        "missing_real_dividends": 12,
        "missing_low_vol_factors": 10,
        "missing_external_state": 14,
        "missing_local_daily_simulation": 14,
        "missing_rebalance_order_health": 8,
        "platform_exports_missing": 5,
    }
    for key, weight in weights.items():
        if gaps.get(key):
            cost += weight
    lane = str(sleeve.get("production_lane") or "")
    if lane == "observation_refresh_only":
        cost -= 6
    if lane == "research_repair_queue":
        cost += 4
    return max(cost, 0.0)


def _risk_penalty(gaps: dict[str, bool], sleeve: dict[str, str], evidence: dict[str, Any]) -> float:
    penalty = 0.0
    burden = _lower(sleeve.get("external_state_burden"))
    data_gate = _lower(sleeve.get("data_gate"))
    corpus = evidence["corpus"]
    if gaps["sample_size_too_small"]:
        penalty += 16
    if "high" in burden:
        penalty += 12
    elif "medium_high" in burden:
        penalty += 8
    if "blocked" in data_gate:
        penalty += 22
    if gaps["specialist_data_required"]:
        penalty += 10
    if "cycle" in corpus or "inventory" in corpus or "commodity" in corpus:
        penalty += 8
    if "not_engineering_handoff" in corpus:
        penalty += 5
    return penalty


def _next_route(
    sleeve: dict[str, str],
    evidence: dict[str, Any],
    gaps: dict[str, bool],
) -> tuple[str, str, str, str]:
    sector_id = str(sleeve.get("sector_id") or "")
    corpus = evidence["corpus"]
    lane = str(sleeve.get("production_lane") or "")
    if sector_id == "gas_water_operators" and evidence["has_local_daily"] and not gaps["missing_rebalance_order_health"]:
        return (
            "Engineering Agent",
            "Keep gas/water as an observation sleeve; refresh paper-trading inputs and wait for the next clean forward signal. Do not add it to frozen V57f.",
            "paper_tracking_only_no_core_inclusion",
            "observation_paper_tracking",
        )
    if gaps["platform_exports_missing"] and evidence["has_local_daily"]:
        return (
            "Project Manager Agent",
            "Keep parked until user-supplied platform exports or a clean forward event arrive. Do not rerun factor validation for returns.",
            "wait_for_external_platform_or_forward_event",
            "external_event_wait",
        )
    if gaps["missing_pit_data"] or gaps["missing_external_state"] or gaps["specialist_data_required"]:
        return (
            "Research Agent",
            "Repair PIT/source/state evidence, then hand a revised hypothesis packet to Quant Validation. Do not run Engineering.",
            "research_data_gate_repair",
            "research_repair",
        )
    if "research_pit_validation_completed" in corpus and gaps["missing_local_daily_simulation"]:
        return (
            "Engineering Agent",
            "Run local daily simulation with real dividends, cash/holding/trade logs and rebalance_order_health only. Do not tune.",
            "local_daily_engineering_gate",
            "engineering_smoke_test_candidate",
        )
    if lane == "research_repair_queue":
        return (
            "Quant Validation Agent",
            "Rerun baseline, IC/RankIC, rolling, ablation and robustness after Research repair. Do not promote on returns alone.",
            "formal_validation_recheck",
            "quant_recheck",
        )
    return (
        "Project Manager Agent",
        "Keep in observation queue until a new evidence packet changes the route.",
        "pm_observation_gate",
        "observation_only",
    )


def _build_selected_agent_queue(selected: dict[str, Any]) -> list[dict[str, str]]:
    if not selected:
        return []
    owner = str(selected.get("recommended_next_owner") or "Project Manager Agent")
    sector_id = str(selected.get("sector_id") or "")
    if owner == "Engineering Agent":
        output = "paper_trading_signal_log_or_local_daily_health_refresh"
    elif owner == "Quant Validation Agent":
        output = "formal_validation_recheck_packet"
    elif owner == "Research Agent":
        output = "repaired_research_hypothesis_and_source_packet"
    else:
        output = "pm_checkpoint"
    return [
        {
            "queue_rank": "1",
            "sector_id": sector_id,
            "owner": owner,
            "task": str(selected.get("recommended_next_action") or ""),
            "input_artifacts": "sleeve_promotion_queue.csv; status_registry.json; sleeve_registry.csv",
            "output_artifacts": output,
            "gate": str(selected.get("pm_gate") or ""),
            "blocked_actions": "do_not_modify_V57f; do_not_tune_returns; do_not_claim_platform_replication; do_not_start_joinquant_test",
        }
    ]


def _build_summary(
    *,
    sleeve_registry: Path,
    status_registry: Path,
    queue_csv: Path,
    report_path: Path,
    selected_agent_queue_csv: Path,
    candidate_rows: list[dict[str, Any]],
    selected: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "governance_rule": "Historical performance alone is never sufficient evidence for accepting a strategy.",
        "objective": "Rank expansion sleeve candidates by minimum completion cost and dividend/low-vol/OCF fit, not by returns.",
        "inputs": {
            "sleeve_registry": str(sleeve_registry),
            "status_registry": str(status_registry),
        },
        "outputs": {
            "queue_csv": str(queue_csv),
            "report_path": str(report_path),
            "selected_agent_queue_csv": str(selected_agent_queue_csv),
        },
        "candidate_count": len(candidate_rows),
        "selected_candidate": {
            "sector_id": selected.get("sector_id", ""),
            "display_name": selected.get("display_name", ""),
            "rank": selected.get("rank", ""),
            "promotion_score": selected.get("promotion_score", ""),
            "owner": selected.get("recommended_next_owner", ""),
            "action": selected.get("recommended_next_action", ""),
            "gate": selected.get("pm_gate", ""),
        },
        "hard_rules": [
            "Only the first-ranked candidate enters the next agent queue.",
            "No observation sleeve may be silently added to frozen V57f.",
            "No return tuning is allowed in this queue.",
            "Engineering receives only frozen local-simulation or paper-refresh tasks.",
            "Platform replication still requires user-supplied JoinQuant daily, transaction, position and log exports.",
        ],
    }


def _build_report(summary: dict[str, Any], rows: list[dict[str, Any]], agent_queue: list[dict[str, str]]) -> str:
    lines = [
        "# V5 Sleeve Promotion Queue",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Purpose",
        "",
        "This PM packet ranks expansion sleeve candidates by minimum completion cost and dividend / low-volatility / operating-cash-flow fit. It does not rank by historical returns.",
        "",
        "Historical performance alone is never sufficient evidence for accepting a strategy.",
        "",
        "## Flow Table",
        "",
        "| Stage | Owner | Input | Action | Output | Gate |",
        "| --- | --- | --- | --- | --- | --- |",
        "| 1. Load production registry | PM Agent | `sleeve_registry.csv` | Read current active, observation and repair lanes | Candidate universe | Stop if registry missing |",
        "| 2. Load strategy evidence | PM Agent | `status_registry.json` | Collect evidence paths, blockers and next gates by sector | Evidence corpus | Ignore historical return ranking |",
        "| 3. Build gap checklist | PM Agent | Candidate rows + evidence corpus | Check PIT, dividends, low-vol, state variables, local daily, order health and sample size | `sleeve_promotion_queue.csv` | Any missing item becomes a gate, not a reason to tune |",
        "| 4. Score candidates | PM Agent | Gap checklist | Score cash-flow fit minus completion cost and risk | Ranked queue | Do not use return metrics |",
        "| 5. Select first candidate only | PM Agent | Ranked queue | Route only rank 1 to next agent | `promotion_agent_queues/selected_candidate_agent_queue.csv` | Other candidates stay parked |",
        "| 6. Agent handoff | PM Agent | Selected candidate task | Send Research / Quant / Engineering a bounded next task | Checkpoint packet | No V57f config changes |",
        "",
        "## Ranked Candidates",
        "",
        "| Rank | Sector | Lane | Score | Fit | Cost | Risk | Next Owner | Gate |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {rank} | {sector_id} | {promotion_lane} | {promotion_score} | {fit_score} | {completion_cost} | {risk_penalty} | {recommended_next_owner} | {pm_gate} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Selected Agent Queue",
            "",
            "| Rank | Sector | Owner | Task | Gate |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in agent_queue:
        lines.append(f"| {row['queue_rank']} | {row['sector_id']} | {row['owner']} | {row['task']} | {row['gate']} |")
    lines.extend(
        [
            "",
            "## Hard Rules",
            "",
            "- Only the first-ranked candidate enters the next agent queue.",
            "- Do not modify frozen V57f.",
            "- Do not add observation sleeves into V57f without a separate PM stage gate.",
            "- Do not tune returns, factor weights, selection count, timing or sector caps.",
            "- Do not claim platform replication without JoinQuant daily, transaction, position and log attribution.",
        ]
    )
    return "\n".join(lines) + "\n"


def _collect_sector_evidence(registry: dict[str, Any], sector_id: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    corpus_parts: list[str] = []
    sector_tokens = _sector_tokens(sector_id)
    for item in registry.get("strategies", []):
        sector = str(item.get("sector") or "")
        blob = json.dumps(item, ensure_ascii=False).lower()
        if sector == sector_id or any(token in blob for token in sector_tokens):
            matches.append(item)
            corpus_parts.append(blob)
    references = registry.get("references", {})
    if isinstance(references, dict):
        for key, value in references.items():
            text = f"{key} {value}".lower()
            if any(token in text for token in sector_tokens):
                corpus_parts.append(text)
    corpus = "\n".join(corpus_parts)
    return {
        "matches": matches,
        "corpus": corpus,
        "has_pit_panel": _contains_any(corpus, ["panel.csv", "panel_with", "pit_panel", "panel_"]),
        "has_dividend": _contains_any(
            corpus,
            ["cash_dividend", "cash_dividends", "cash dividend", "dividend_events", "dividend events", "dividend_cash"],
        ),
        "has_low_vol": _contains_any(corpus, ["low_vol", "low-vol", "low volatility", "volatility_factors"]),
        "has_external_state": _contains_any(corpus, ["external_state", "state_guard", "state_diagnostic", "true_state", "cycle_state", "official_state"]),
        "has_local_daily": _contains_any(
            corpus,
            ["local_daily", "validation_daily", "daily_simulation", "daily_backtest", "local_joinquant", "real_daily"],
        ),
        "has_rebalance_order_health": _contains_any(corpus, ["rebalance_order_health", "order_health", "rebalance order health"]),
        "platform_exports_missing": _contains_any(
            corpus,
            ["pending exports", "waiting_for_exports", "exports have not been supplied", "pending_attribution", "not_platform_replication"],
        ),
    }


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _state_required(data_gate: str, burden: str, corpus: str) -> bool:
    return (
        "high" in burden
        or "state" in data_gate
        or "specialist" in data_gate
        or "cycle" in corpus
        or "tariff" in corpus
        or "inventory" in corpus
        or "arpu" in corpus
        or "ev / nbv" in corpus
    )


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _sector_tokens(sector_id: str) -> list[str]:
    tokens = {sector_id, sector_id.replace("_operators", ""), sector_id.replace("_integrated", "")}
    if sector_id == "oil_gas_pipeline_integrated":
        tokens.update({"oil_gas", "oil / gas"})
    if sector_id == "gas_water_operators":
        tokens.update({"gas_water", "gas / water"})
    if sector_id == "consumer_staples_cashflow":
        tokens.add("consumer_staples")
    return [token for token in tokens if token]


def _pm_note(sleeve: dict[str, str], evidence: dict[str, Any], gaps: dict[str, bool]) -> str:
    sector_id = str(sleeve.get("sector_id") or "")
    if sector_id == "gas_water_operators" and evidence["has_local_daily"]:
        return "Most complete observation candidate; promote only to clean forward/paper queue, not to V57f."
    if gaps["sample_size_too_small"]:
        return "Sample-size constrained; keep as specialist observation unless PM approves a small-sample sleeve policy."
    if gaps["specialist_data_required"]:
        return "Specialist or true-state policy remains open; Research must repair the source contract before Engineering."
    if gaps["platform_exports_missing"]:
        return "External platform exports or clean forward evidence are missing; keep parked and do not rerun for returns."
    if gaps["missing_external_state"]:
        return "External or specialist state gate is still open; Research must repair sources before Engineering."
    if gaps["missing_local_daily_simulation"]:
        return "Research/Quant evidence exists; next possible step is local daily simulation after PM gate."
    return "Keep parked unless a new evidence packet changes the route."


def _yes(value: Any) -> bool:
    return str(value or "").strip().lower() in {"yes", "true", "1", "passed", "ok"}


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()
