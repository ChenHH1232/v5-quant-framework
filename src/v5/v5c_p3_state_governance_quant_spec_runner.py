from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_p3_state_governance_quant_spec") / "current"
P2_DIR = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"

P2_SUMMARY = P2_DIR / "v5c_p2_valuation_crowding_summary.json"
P2_PM_DECISION = P2_DIR / "v5c_p2_pm_gate_decision.csv"
P2_VALUATION = P2_DIR / "v5c_p2_valuation_state_panel.csv"
P2_CROWDING = P2_DIR / "v5c_p2_crowding_state_panel.csv"
P2_SLEEVE_OVERHEAT = P2_DIR / "v5c_p2_sleeve_overheat_state_panel.csv"
P2_BROAD_TREND = P2_DIR / "v5c_p2_broad_index_trend_state_panel.csv"
P2_PIT_AUDIT = P2_DIR / "v5c_p2_pit_leakage_audit.csv"
P2_COVERAGE_AUDIT = P2_DIR / "v5c_p2_field_coverage_audit.csv"


def run_v5c_p3_state_governance_quant_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_p3_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "p3_blocked_missing_required_input", blockers)
        _write_json(out / "v5c_p3_state_governance_summary.json", summary)
        return summary

    p2_summary = _read_json(root / P2_SUMMARY)
    p2_decision = _read_csv(root / P2_PM_DECISION)[0]
    valuation = _read_csv(root / P2_VALUATION)
    crowding = _read_csv(root / P2_CROWDING)
    sleeve_overheat = _read_csv(root / P2_SLEEVE_OVERHEAT)
    broad_trend = _read_csv(root / P2_BROAD_TREND)
    pit_audit = _read_csv(root / P2_PIT_AUDIT)
    coverage_audit = _read_csv(root / P2_COVERAGE_AUDIT)

    state_taxonomy = _state_taxonomy()
    state_summary = _state_observation_summary(valuation, crowding, sleeve_overheat, broad_trend)
    boundary = _state_action_boundary_matrix(state_taxonomy)
    allowed_uses = _allowed_diagnostic_uses()
    blocked_actions = _blocked_actions()
    observation_schema = _forward_observation_schema()
    approval_requirements = _overlay_engineering_approval_requirements()
    transition_spec = _state_transition_observation_spec()
    admission = _pm_admission_decision(p2_summary, p2_decision, pit_audit, coverage_audit)
    blockers_out = _p3_blockers(p2_summary, p2_decision, pit_audit, coverage_audit)
    if blockers_out:
        admission[0]["pm_gate_decision"] = "p3_state_governance_spec_blocked"
        admission[0]["p3_pass"] = "False"
        admission[0]["next_step"] = "repair_p2_dependency_before_p3"
    next_queue = _next_queue(admission[0])

    _write_csv(out / "v5c_p3_input_dependency_audit.csv", _input_dependency_audit(p2_summary, p2_decision, pit_audit, coverage_audit))
    _write_csv(out / "v5c_p3_state_taxonomy.csv", state_taxonomy)
    _write_csv(out / "v5c_p3_state_observation_summary.csv", state_summary)
    _write_csv(out / "v5c_p3_state_action_boundary_matrix.csv", boundary)
    _write_csv(out / "v5c_p3_allowed_diagnostic_uses.csv", allowed_uses)
    _write_csv(out / "v5c_p3_blocked_actions.csv", blocked_actions)
    _write_csv(out / "v5c_p3_forward_observation_schema.csv", observation_schema)
    _write_csv(out / "v5c_p3_state_transition_observation_spec.csv", transition_spec)
    _write_csv(out / "v5c_p3_overlay_engineering_approval_requirements.csv", approval_requirements)
    _write_csv(out / "v5c_p3_pm_gate_decision.csv", admission)
    _write_csv(out / "v5c_p3_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_p3_blockers.csv", blockers_out)
    (out / "v5c_p3_state_governance_report.md").write_text(
        _report(state_summary, admission, next_queue),
        encoding="utf-8",
    )
    (out / "v5c_p3_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_p3_state_governance_quant_spec",
        admission[0]["pm_gate_decision"],
        blockers_out,
        p2_dependency_pass=admission[0]["p2_dependency_pass"] == "True",
        taxonomy_rows=len(state_taxonomy),
        boundary_rows=len(boundary),
        blocked_action_count=len(blocked_actions),
        valuation_overheat_watch_count=_count_state(valuation, "valuation_state", "valuation_overheat_watch"),
        sleeve_watch_count=sum(1 for row in sleeve_overheat if row.get("sleeve_overheat_state") != "normal"),
    )
    _write_json(out / "v5c_p3_state_governance_summary.json", summary)
    return summary


def _input_dependency_audit(
    p2_summary: dict[str, Any],
    p2_decision: dict[str, str],
    pit_audit: list[dict[str, str]],
    coverage_audit: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "dependency_id": "p2_summary",
            "status": "pass" if p2_summary.get("fatal_blocker_count") == 0 else "fail",
            "observed": f"fatal_blocker_count={p2_summary.get('fatal_blocker_count')}",
            "required_for_p3": True,
        },
        {
            "dependency_id": "p2_pm_gate",
            "status": "pass" if p2_decision.get("p2_pass") == "True" else "fail",
            "observed": p2_decision.get("pm_gate_decision", ""),
            "required_for_p3": True,
        },
        {
            "dependency_id": "p2_pit_audit",
            "status": "pass" if all(row.get("audit_status") == "pass" for row in pit_audit) else "fail",
            "observed": _status_counts(pit_audit, "audit_status"),
            "required_for_p3": True,
        },
        {
            "dependency_id": "p2_required_coverage",
            "status": "pass"
            if all(row.get("coverage_status") != "fail" for row in coverage_audit if row.get("required_for_p2") == "True")
            else "fail",
            "observed": _status_counts(coverage_audit, "coverage_status"),
            "required_for_p3": True,
        },
    ]


def _state_taxonomy() -> list[dict[str, Any]]:
    return [
        _taxonomy_row("valuation_cheap_support", "valuation", "P2 valuation_cheapness_score high enough to show cheap support.", "support_context_only", "diagnostic_only"),
        _taxonomy_row("neutral", "valuation_or_trend", "No valuation/crowding/trend warning state.", "baseline_context", "diagnostic_only"),
        _taxonomy_row("valuation_overheat_watch", "valuation", "P2 valuation_overheat_score high enough to require review.", "watchlist_context_only", "pm_review_only"),
        _taxonomy_row("market_attention_hot", "crowding", "Prior-day money percentile is high for the selected stock.", "liquidity_attention_context", "diagnostic_only"),
        _taxonomy_row("market_attention_cold", "crowding", "Prior-day money percentile is low for the selected stock.", "liquidity_attention_context", "diagnostic_only"),
        _taxonomy_row("rebalance_liquidity_pressure_watch", "crowding", "P0 order value is material relative to local 20d money.", "execution_risk_context", "execution_review_only"),
        _taxonomy_row("valuation_price_flow_overheat_watch", "sleeve", "Sleeve valuation, flow, and price trend are all hot.", "composite_watch_context", "separate_pm_spec_required"),
        _taxonomy_row("cooldown_or_stress_watch", "sleeve", "Sleeve benchmark trend is stressed or cooling.", "risk_context_only", "separate_pm_spec_required"),
        _taxonomy_row("uptrend", "broad_trend", "Broad repaired benchmark trend is positive.", "macro_context_only", "diagnostic_only"),
        _taxonomy_row("downtrend", "broad_trend", "Broad repaired benchmark trend is negative.", "macro_context_only", "diagnostic_only"),
        _taxonomy_row("review_insufficient_history", "broad_trend", "Lookback history is insufficient for full trend state.", "data_review_context", "review_only"),
        _taxonomy_row("initial_rebalance_no_prior_baseline_nav", "broad_trend", "Initial repaired rebalance has no prior baseline NAV.", "initial_condition_context", "review_only"),
    ]


def _taxonomy_row(state_id: str, state_family: str, definition: str, allowed_role: str, admission_status: str) -> dict[str, Any]:
    return {
        "state_id": state_id,
        "state_family": state_family,
        "definition": definition,
        "allowed_role": allowed_role,
        "admission_status": admission_status,
        "can_trigger_trade": False,
        "can_modify_v57f_weight": False,
        "can_modify_v57f_universe": False,
        "can_mark_accepted": False,
    }


def _state_observation_summary(
    valuation: list[dict[str, str]],
    crowding: list[dict[str, str]],
    sleeve_overheat: list[dict[str, str]],
    broad_trend: list[dict[str, str]],
) -> list[dict[str, Any]]:
    rows = []
    rows.extend(_counter_rows("valuation", valuation, "valuation_state"))
    rows.extend(_counter_rows("crowding", crowding, "crowding_state"))
    rows.extend(_counter_rows("sleeve_overheat", sleeve_overheat, "sleeve_overheat_state"))
    rows.extend(_counter_rows("broad_trend", broad_trend, "broad_trend_state"))
    rows.extend(_sleeve_watch_rows(sleeve_overheat))
    return rows


def _state_action_boundary_matrix(state_taxonomy: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for state in state_taxonomy:
        rows.append(
            {
                "state_id": state["state_id"],
                "allowed_action": "observe_record_report",
                "trade_order_allowed": False,
                "weight_change_allowed": False,
                "cash_raise_allowed": False,
                "cash_proxy_allowed": False,
                "reentry_allowed": False,
                "cross_sleeve_transfer_allowed": False,
                "threshold_scan_allowed": False,
                "engineering_backtest_allowed_now": False,
                "requires_separate_pm_approval_for_any_trade_use": True,
                "governance_note": _boundary_note(state["state_id"]),
            }
        )
    return rows


def _allowed_diagnostic_uses() -> list[dict[str, Any]]:
    return [
        {
            "use_id": "forward_watchlist_tagging",
            "allowed": True,
            "scope": "Tag future V57f selected holdings with valuation/crowding/sleeve/broad states for PM review.",
            "trading_impact": "none",
        },
        {
            "use_id": "post_rebalance_state_attribution",
            "allowed": True,
            "scope": "Explain later drawdown, sleeve concentration, or execution stress using pre-existing state tags.",
            "trading_impact": "none",
        },
        {
            "use_id": "execution_liquidity_review",
            "allowed": True,
            "scope": "Use crowding and order-to-money fields to route to V5d execution review.",
            "trading_impact": "no strategy trade path change",
        },
        {
            "use_id": "separate_overlay_hypothesis_admission",
            "allowed": True,
            "scope": "Use P2/P3 state evidence to write a separate fixed-rule overlay spec for later approval.",
            "trading_impact": "requires separate PM approval before any backtest",
        },
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    actions = [
        ("sell_or_trim_on_overheat", "P3 states cannot sell or trim holdings."),
        ("reduce_sleeve_weight_on_overheat", "P3 states cannot lower sleeve target weights."),
        ("increase_sleeve_weight_on_cheap_state", "Cheap support cannot increase sleeve weights."),
        ("change_v57f_stock_pool", "P3 cannot add or remove stocks from V57f selection universe."),
        ("change_v57f_target_count_or_caps", "P3 cannot change target_count, single-name caps, sleeve caps, or rebalance cadence."),
        ("cash_raise_or_cash_proxy", "P3 cannot raise cash or buy a cash proxy asset."),
        ("defense_overlay_activation", "P3 cannot activate V5c defense or ERC changes."),
        ("profit_taking_rule_activation", "P3 cannot activate V5e profit taking."),
        ("threshold_scan", "P3 cannot scan overheat, cheapness, flow, or trend thresholds."),
        ("accepted_or_live_approved", "P3 cannot mark any V5c state rule accepted or live approved."),
    ]
    return [
        {
            "blocked_action": action,
            "blocked": True,
            "reason": reason,
            "unblock_condition": "separate_pm_quant_spec_plus_fixed_rule_plus_limited_engineering_approval",
        }
        for action, reason in actions
    ]


def _forward_observation_schema() -> list[dict[str, Any]]:
    fields = [
        ("observation_date", "date", "Future V57f signal/rebalance observation date."),
        ("code", "string", "Selected holding code."),
        ("sleeve_id", "string", "V57f sleeve."),
        ("valuation_state", "string", "P2 valuation state."),
        ("crowding_state", "string", "P2 money/order crowding state."),
        ("sleeve_overheat_state", "string", "P2 sleeve composite state."),
        ("broad_trend_state", "string", "P2 broad repaired benchmark trend state."),
        ("state_visible_time", "string", "When state is visible to PM, always after source data is observable."),
        ("action_taken", "string", "Must remain observe_only until separately approved."),
        ("pm_review_status", "string", "open/reviewed/escalated/no_action."),
    ]
    return [{"field_name": name, "field_type": typ, "description": desc, "required": True} for name, typ, desc in fields]


def _state_transition_observation_spec() -> list[dict[str, Any]]:
    return [
        {
            "transition_id": "normal_to_valuation_overheat_watch",
            "source_state_family": "valuation",
            "allowed_interpretation": "valuation has become less supportive; review attribution only",
            "trade_effect": "none",
        },
        {
            "transition_id": "market_attention_cold_to_hot",
            "source_state_family": "crowding",
            "allowed_interpretation": "liquidity/attention changed; route to execution review if order pressure is high",
            "trade_effect": "none",
        },
        {
            "transition_id": "normal_to_valuation_price_flow_overheat_watch",
            "source_state_family": "sleeve",
            "allowed_interpretation": "composite sleeve watch suitable for separate PM hypothesis admission",
            "trade_effect": "none_without_new_approval",
        },
        {
            "transition_id": "uptrend_to_downtrend",
            "source_state_family": "broad_trend",
            "allowed_interpretation": "broad state context for post-period attribution",
            "trade_effect": "none",
        },
    ]


def _overlay_engineering_approval_requirements() -> list[dict[str, Any]]:
    return [
        {
            "requirement_id": "fixed_pre_registered_rule",
            "required": True,
            "description": "Any later overlay must be a fixed pre-registered rule, not selected by historical return.",
        },
        {
            "requirement_id": "separate_pm_quant_spec",
            "required": True,
            "description": "P3 only opens a spec queue; engineering backtest requires separate PM approval.",
        },
        {
            "requirement_id": "no_v57f_core_change",
            "required": True,
            "description": "V57f universe, sleeve structure, target_count, caps, and cadence remain frozen.",
        },
        {
            "requirement_id": "pit_and_forward_review",
            "required": True,
            "description": "PIT audit and later forward/paper observation must be included before candidate promotion.",
        },
        {
            "requirement_id": "no_accepted_from_p3",
            "required": True,
            "description": "P3 cannot mark accepted or live approved.",
        },
    ]


def _pm_admission_decision(
    p2_summary: dict[str, Any],
    p2_decision: dict[str, str],
    pit_audit: list[dict[str, str]],
    coverage_audit: list[dict[str, str]],
) -> list[dict[str, Any]]:
    p2_pass = (
        p2_summary.get("fatal_blocker_count") == 0
        and p2_decision.get("p2_pass") == "True"
        and all(row.get("audit_status") == "pass" for row in pit_audit)
        and all(row.get("coverage_status") != "fail" for row in coverage_audit if row.get("required_for_p2") == "True")
    )
    return [
        {
            "pm_gate_decision": "p3_state_governance_spec_pass_ready_for_forward_observation_not_backtest" if p2_pass else "p3_state_governance_spec_blocked",
            "p3_pass": str(p2_pass),
            "p2_dependency_pass": str(p2_pass),
            "admit_forward_observation": str(p2_pass),
            "admit_engineering_backtest": False,
            "admit_trading_rule": False,
            "accepted": False,
            "v57f_core_modified": False,
            "new_strategy_rule_added": False,
            "threshold_scan_used": False,
            "network_fetch_started": False,
            "joinquant_started": False,
            "next_step": "open_v5c_p4_state_forward_observation_packet" if p2_pass else "repair_p2_dependency_before_p3",
            "review_notes": "P3 admits observe-only state governance. Any overheat or defense trading use requires a separate PM/Quant spec and later approval.",
        }
    ]


def _p3_blockers(
    p2_summary: dict[str, Any],
    p2_decision: dict[str, str],
    pit_audit: list[dict[str, str]],
    coverage_audit: list[dict[str, str]],
) -> list[dict[str, Any]]:
    blockers = []
    if p2_summary.get("fatal_blocker_count") != 0:
        blockers.append(_blocker("p2_summary_has_fatal_blockers", f"fatal_blocker_count={p2_summary.get('fatal_blocker_count')}"))
    if p2_decision.get("p2_pass") != "True":
        blockers.append(_blocker("p2_pm_gate_not_pass", p2_decision.get("pm_gate_decision", "")))
    for row in pit_audit:
        if row.get("audit_status") != "pass":
            blockers.append(_blocker(f"p2_pit_{row.get('audit_id')}", row.get("notes", "")))
    for row in coverage_audit:
        if row.get("required_for_p2") == "True" and row.get("coverage_status") == "fail":
            blockers.append(_blocker(f"p2_coverage_{row.get('scope')}_{row.get('field_name')}", row.get("coverage", "")))
    return blockers


def _next_queue(decision: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = decision["p3_pass"]
    return [
        {
            "priority": 1,
            "next_gate": "v5c_p4_state_forward_observation_packet",
            "allowed": allowed,
            "scope": "Observe P3 states on future V57f/paper rebalances and collect PM review evidence; no trading impact.",
            "requires_network": False,
            "requires_v57f_change": False,
            "status": "ready" if allowed == "True" else "blocked_until_p3_repair",
        },
        {
            "priority": 2,
            "next_gate": "v5c_overheat_overlay_pm_quant_spec_separate_approval",
            "allowed": "False",
            "scope": "Only if PM separately approves: write fixed overheat/defense overlay spec before any engineering backtest.",
            "requires_network": False,
            "requires_v57f_change": False,
            "status": "blocked_until_separate_pm_approval",
        },
        {
            "priority": 3,
            "next_gate": "v5c_p2_market_crowding_deepening_optional",
            "allowed": "True",
            "scope": "Optional local data deepening for free-float turnover or shareholder flow; not blocking observation.",
            "requires_network": "maybe_if_local_fields_missing",
            "requires_v57f_change": False,
            "status": "optional",
        },
    ]


def _summary(
    status: str,
    decision: str,
    blockers: list[dict[str, Any]],
    p2_dependency_pass: bool = False,
    taxonomy_rows: int = 0,
    boundary_rows: int = 0,
    blocked_action_count: int = 0,
    valuation_overheat_watch_count: int = 0,
    sleeve_watch_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_p3_state_governance_quant_spec",
        "status": status,
        "pm_gate_decision": decision,
        "p2_dependency_pass": p2_dependency_pass,
        "taxonomy_rows": taxonomy_rows,
        "boundary_rows": boundary_rows,
        "blocked_action_count": blocked_action_count,
        "valuation_overheat_watch_count": valuation_overheat_watch_count,
        "sleeve_watch_count": sleeve_watch_count,
        "accepted": False,
        "v57f_core_modified": False,
        "new_strategy_rule_added": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "engineering_backtest_started": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
        "outputs": {
            "summary": str(OUT_DIR / "v5c_p3_state_governance_summary.json"),
            "report": str(OUT_DIR / "v5c_p3_state_governance_report.md"),
            "state_taxonomy": str(OUT_DIR / "v5c_p3_state_taxonomy.csv"),
            "state_action_boundary_matrix": str(OUT_DIR / "v5c_p3_state_action_boundary_matrix.csv"),
            "blocked_actions": str(OUT_DIR / "v5c_p3_blocked_actions.csv"),
            "pm_gate_decision": str(OUT_DIR / "v5c_p3_pm_gate_decision.csv"),
            "next_queue": str(OUT_DIR / "v5c_p3_next_agent_queue.csv"),
        },
    }


def _report(state_summary: list[dict[str, Any]], admission: list[dict[str, Any]], next_queue: list[dict[str, Any]]) -> str:
    summary_lines = [
        f"- `{row['scope']}` / `{row['state_id']}`: `{row['count']}`"
        for row in state_summary
        if row.get("summary_type") == "state_count"
    ]
    return "\n".join(
        [
            "# V5c P3 State Governance Quant Spec",
            "",
            f"- PM gate: `{admission[0]['pm_gate_decision']}`",
            "- Scope: observe-only valuation/crowding/overheat governance.",
            "- Engineering backtest admitted now: `False`",
            "- Trading rule admitted now: `False`",
            "- Accepted: `False`",
            "- V57f core modified: `False`",
            "",
            "## State Counts",
            *summary_lines,
            "",
            "## Boundary",
            "P3 states may tag, report, and support PM review. They may not sell, trim, reweight, raise cash, change sleeve weights, or alter V57f without a separate approved PM/Quant spec.",
            "",
            "## Next",
            *[f"- P{row['priority']} `{row['next_gate']}`: {row['status']}" for row in next_queue],
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5c P3 State Governance Quant Spec Agent Rules",
            "",
            "1. Use P2 valuation/crowding/sleeve/broad state panels as inputs.",
            "2. P3 is observe-only governance. Do not run an engineering backtest.",
            "3. Do not add trading rules, sell/trim actions, reweighting, cash proxy usage, or threshold scans.",
            "4. Do not modify V57f, start JoinQuant, fetch network data, mark accepted, or mark live approved.",
            "5. Any future overheat/defense overlay must be opened as a separate PM/Quant spec with fixed rules and explicit approval.",
            "",
        ]
    )


def _counter_rows(scope: str, rows: list[dict[str, str]], field: str) -> list[dict[str, Any]]:
    counts = Counter(row.get(field, "") for row in rows)
    total = len(rows)
    return [
        {
            "summary_type": "state_count",
            "scope": scope,
            "state_id": state,
            "count": count,
            "share": _fmt(count / total) if total else "",
            "notes": "P2 observed state count; diagnostic only.",
        }
        for state, count in sorted(counts.items())
    ]


def _sleeve_watch_rows(sleeve_overheat: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts = defaultdict(int)
    for row in sleeve_overheat:
        if row.get("sleeve_overheat_state") != "normal":
            counts[(row.get("sleeve_id", ""), row.get("sleeve_overheat_state", ""))] += 1
    return [
        {
            "summary_type": "sleeve_watch_count",
            "scope": sleeve,
            "state_id": state,
            "count": count,
            "share": "",
            "notes": "Sleeve-level watch rows across P2 rebalance-state observations.",
        }
        for (sleeve, state), count in sorted(counts.items())
    ]


def _boundary_note(state_id: str) -> str:
    if "overheat" in state_id:
        return "Watch state may justify separate PM review, not immediate trading."
    if "crowding" in state_id or "market_attention" in state_id or "liquidity" in state_id:
        return "May route to execution/liquidity review without changing strategy path."
    if "cheap" in state_id:
        return "Cheap support is context only and cannot increase allocation."
    return "Observation context only."


def _count_state(rows: list[dict[str, str]], field: str, state: str) -> int:
    return sum(1 for row in rows if row.get(field) == state)


def _status_counts(rows: list[dict[str, str]], field: str) -> str:
    counts = Counter(row.get(field, "") for row in rows)
    return ";".join(f"{key}={value}" for key, value in sorted(counts.items()))


def _blocker(blocker_id: str, observed: str) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "severity": "fatal",
        "status": "blocking",
        "observed": observed,
        "description": "P3 dependency failed; repair P2 before admitting state governance spec.",
    }


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        P2_SUMMARY,
        P2_PM_DECISION,
        P2_VALUATION,
        P2_CROWDING,
        P2_SLEEVE_OVERHEAT,
        P2_BROAD_TREND,
        P2_PIT_AUDIT,
        P2_COVERAGE_AUDIT,
    ]
    blockers = []
    for rel in required:
        if not (root / rel).exists():
            blockers.append(
                {
                    "blocker_id": f"missing_{rel.name}",
                    "severity": "fatal",
                    "status": "blocking",
                    "path": str(rel),
                    "description": "Required P3 local input is missing.",
                }
            )
    return blockers


def _fmt(value: float) -> str:
    return f"{value:.12g}"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run_v5c_p3_state_governance_quant_spec()
