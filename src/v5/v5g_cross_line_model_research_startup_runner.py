from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5g_cross_line_model_research_startup") / "current"

MIDTERM = Path("v5_midterm_report") / "current"
V5F_CHAMPION = Path("v5f_internal_subsleeve_deep_engineering") / "current"
V5C_P1 = Path("v5c_p1_financial_quality_pit_panel") / "current"
V5C_P2 = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
V5C_P3 = Path("v5c_p3_state_governance_quant_spec") / "current"
V5C_P4 = Path("v5c_p4_state_forward_observation_packet") / "current"
V5C_OVERHEAT = Path("v5c_overheat_overlay_pm_quant_spec") / "current"
V5E_511360 = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"
KNOWLEDGE = Path("knowledge") / "research_agent"
QUANT_KNOWLEDGE = Path("knowledge") / "quant_validation_agent"
V4_ROOT = Path("D:/hh/codex/v4")

REQUIRED_INPUTS = [
    MIDTERM / "v5_midterm_summary.json",
    MIDTERM / "v5_midterm_top_models.csv",
    MIDTERM / "v5_midterm_diagnostic_watchlist.csv",
    V5F_CHAMPION / "v5f_internal_subsleeve_deep_summary.json",
    V5F_CHAMPION / "v5f_internal_subsleeve_deep_metrics.csv",
    V5C_P1 / "v5c_p1_financial_quality_summary.json",
    V5C_P2 / "v5c_p2_valuation_crowding_summary.json",
    V5C_P3 / "v5c_p3_state_governance_summary.json",
    V5C_P4 / "v5c_p4_state_forward_observation_summary.json",
    V5C_OVERHEAT / "v5c_overheat_overlay_pm_quant_spec_summary.json",
    V5E_511360 / "v5e_511360_pm_quant_review_summary.json",
    KNOWLEDGE / "INDEX.md",
    KNOWLEDGE / "v5c_defense_profit_taking" / "v5c_knowledge_base_summary.json",
    QUANT_KNOWLEDGE / "methodology" / "factor_validation_methods.md",
]


def run_v5g_cross_line_model_research_startup(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5g_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "v5g_startup_blocked_missing_input", blockers)
        _write_json(out / "v5g_cross_line_model_research_summary.json", summary)
        return summary

    midterm_summary = _read_json(root / MIDTERM / "v5_midterm_summary.json")
    top_models = _read_csv(root / MIDTERM / "v5_midterm_top_models.csv")
    watchlist = _read_csv(root / MIDTERM / "v5_midterm_diagnostic_watchlist.csv")
    v5f_summary = _read_json(root / V5F_CHAMPION / "v5f_internal_subsleeve_deep_summary.json")
    v5f_metrics = _read_csv(root / V5F_CHAMPION / "v5f_internal_subsleeve_deep_metrics.csv")
    v5c_p1 = _read_json(root / V5C_P1 / "v5c_p1_financial_quality_summary.json")
    v5c_p2 = _read_json(root / V5C_P2 / "v5c_p2_valuation_crowding_summary.json")
    v5c_p3 = _read_json(root / V5C_P3 / "v5c_p3_state_governance_summary.json")
    v5c_p4 = _read_json(root / V5C_P4 / "v5c_p4_state_forward_observation_summary.json")
    v5c_overheat = _read_json(root / V5C_OVERHEAT / "v5c_overheat_overlay_pm_quant_spec_summary.json")
    v5e_511360 = _read_json(root / V5E_511360 / "v5e_511360_pm_quant_review_summary.json")

    source_manifest = _source_manifest(root)
    success_transfer = _success_transfer_matrix(top_models, watchlist, v5f_summary, v5e_511360)
    knowledge_inventory = _external_data_knowledge_inventory(root)
    model_specs = _five_new_model_specs()
    priority = _model_research_priority_matrix(model_specs, success_transfer)
    governance = _governance_boundary_matrix(model_specs)
    data_gate = _data_gate_requirements(model_specs)
    limited_queue = _limited_research_queue(priority)
    blockers_out = _v5g_blockers(midterm_summary, v5f_summary, v5c_p1, v5c_p2, v5c_p3, v5c_p4, v5c_overheat, v5e_511360)
    decision = _pm_gate_decision(blockers_out)
    next_queue = _next_agent_queue(decision[0], limited_queue)

    _write_csv(out / "v5g_input_source_manifest.csv", source_manifest)
    _write_csv(out / "v5g_midterm_success_transfer_matrix.csv", success_transfer)
    _write_csv(out / "v5g_external_data_knowledge_inventory.csv", knowledge_inventory)
    _write_csv(out / "v5g_five_new_model_specs.csv", model_specs)
    _write_csv(out / "v5g_model_research_priority_matrix.csv", priority)
    _write_csv(out / "v5g_governance_boundary_matrix.csv", governance)
    _write_csv(out / "v5g_data_gate_requirements.csv", data_gate)
    _write_csv(out / "v5g_limited_research_queue.csv", limited_queue)
    _write_csv(out / "v5g_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5g_blockers.csv", blockers_out)
    (out / "v5g_cross_line_model_research_report.md").write_text(
        _report(midterm_summary, v5f_metrics, model_specs, priority, decision, next_queue),
        encoding="utf-8",
    )
    (out / "v5g_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5g_next_prompt.md").write_text(_next_prompt(), encoding="utf-8")

    summary = _summary(
        "completed_v5g_cross_line_model_research_startup",
        decision[0]["pm_gate_decision"],
        blockers_out,
        model_count=len(model_specs),
        top_priority_model=priority[0]["model_id"] if priority else "",
        primary_v5f_candidate=v5f_summary.get("primary_candidate", ""),
        primary_v5f_delta_return_pct_points_vs_repaired_baseline=v5f_summary.get("primary_delta_return_pct_points_vs_repaired_baseline", ""),
        v5c_state_gate_available=True,
        v5e_cash_proxy_available=True,
        external_knowledge_sources=len(knowledge_inventory),
    )
    _write_json(out / "v5g_cross_line_model_research_summary.json", summary)
    return summary


def _source_manifest(root: Path) -> list[dict[str, Any]]:
    sources = [
        ("midterm_summary", MIDTERM / "v5_midterm_summary.json", "midterm primary conclusion and repaired baseline truth"),
        ("midterm_top_models", MIDTERM / "v5_midterm_top_models.csv", "top governed model list"),
        ("midterm_diagnostic_watchlist", MIDTERM / "v5_midterm_diagnostic_watchlist.csv", "diagnostic successes and blockers"),
        ("v5f_internal_subsleeve", V5F_CHAMPION / "v5f_internal_subsleeve_deep_summary.json", "V5f champion evidence"),
        ("v5c_p1_financial_quality", V5C_P1 / "v5c_p1_financial_quality_summary.json", "PIT financial quality panel status"),
        ("v5c_p2_state_panels", V5C_P2 / "v5c_p2_valuation_crowding_summary.json", "valuation/crowding state gate"),
        ("v5c_p3_state_governance", V5C_P3 / "v5c_p3_state_governance_summary.json", "observe-only state governance"),
        ("v5c_p4_forward_observation", V5C_P4 / "v5c_p4_state_forward_observation_summary.json", "forward observation packet"),
        ("v5c_overheat_spec", V5C_OVERHEAT / "v5c_overheat_overlay_pm_quant_spec_summary.json", "overheat spec only, no backtest"),
        ("v5e_511360_cash_proxy", V5E_511360 / "v5e_511360_pm_quant_review_summary.json", "cash proxy candidate evidence"),
        ("research_knowledge_index", KNOWLEDGE / "INDEX.md", "local research knowledge index"),
        ("quant_validation_methods", QUANT_KNOWLEDGE / "methodology" / "factor_validation_methods.md", "validation standards"),
    ]
    rows = []
    for source_id, rel, role in sources:
        path = root / rel if not rel.is_absolute() else rel
        rows.append(
            {
                "source_id": source_id,
                "path": str(rel),
                "exists": path.exists(),
                "source_role": role,
                "used_for": "V5g idea generation and governance boundary only",
            }
        )
    return rows


def _success_transfer_matrix(
    top_models: list[dict[str, str]],
    watchlist: list[dict[str, str]],
    v5f_summary: dict[str, Any],
    v5e_511360: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for row in top_models:
        rows.append(
            {
                "source_model_id": row["model_id"],
                "source_family": row["family"],
                "observed_edge": row.get("delta_return_pct_points_vs_reference", ""),
                "source_status": row.get("status", ""),
                "transferable_mechanism": _transferable_mechanism(row["model_id"]),
                "v5g_use": _v5g_use(row["model_id"]),
                "acceptance_transfer_allowed": False,
            }
        )
    for row in watchlist:
        rows.append(
            {
                "source_model_id": row["item_id"],
                "source_family": row["family"],
                "observed_edge": row.get("observed_result", ""),
                "source_status": row.get("current_status", ""),
                "transferable_mechanism": "diagnostic signal and blocker awareness",
                "v5g_use": "research queue only until independent validation or forward evidence exists",
                "acceptance_transfer_allowed": False,
            }
        )
    rows.append(
        {
            "source_model_id": "v5f_internal_subsleeve_champion_snapshot",
            "source_family": "startup_repaired_primary",
            "observed_edge": v5f_summary.get("primary_delta_return_pct_points_vs_repaired_baseline", ""),
            "source_status": v5f_summary.get("pm_gate_decision", ""),
            "transferable_mechanism": "separate value/fundamental and momentum budgets inside existing V57f sleeves",
            "v5g_use": "base architecture for all five V5g models",
            "acceptance_transfer_allowed": False,
        }
    )
    rows.append(
        {
            "source_model_id": "v5e_511360_cash_proxy_snapshot",
            "source_family": "cash_governance",
            "observed_edge": v5e_511360.get("delta_return_vs_v57f", ""),
            "source_status": v5e_511360.get("pm_gate_decision", ""),
            "transferable_mechanism": "cash drag mitigation after rule-governed exits",
            "v5g_use": "cash proxy branch for V5g model 04 only; not default live usage",
            "acceptance_transfer_allowed": False,
        }
    )
    return rows


def _external_data_knowledge_inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "inventory_id": "v5_local_repaired_panels",
            "source_type": "local_structured_data",
            "path": "数据库/processed/startup_preload_repaired_panels_v5",
            "available": (root / "数据库" / "processed" / "startup_preload_repaired_panels_v5").exists(),
            "allowed_use": "PIT financial/valuation/low-vol inputs for V5g data gates",
            "blocked_use": "new accepted status without validation",
        },
        {
            "inventory_id": "v5_local_repaired_prices",
            "source_type": "local_structured_data",
            "path": "数据库/processed/startup_preload_repaired_prices_v5",
            "available": (root / "数据库" / "processed" / "startup_preload_repaired_prices_v5").exists(),
            "allowed_use": "daily money/volume/crowding and liquidity states",
            "blocked_use": "post-2026-05-31 historical backtest evidence",
        },
        {
            "inventory_id": "v5_5min_data",
            "source_type": "local_intraday_data",
            "path": "v5e_full_holding_5min_data_gate/current",
            "available": (root / "v5e_full_holding_5min_data_gate" / "current").exists(),
            "allowed_use": "diagnostic short-window execution/reversion research",
            "blocked_use": "accepted intraday trigger without independent validation",
        },
        {
            "inventory_id": "v4_reference_folder",
            "source_type": "external_local_project_reference",
            "path": str(V4_ROOT),
            "available": V4_ROOT.exists(),
            "allowed_use": "reference old momentum/mean-reversion architecture ideas",
            "blocked_use": "benchmark or acceptance evidence for V5g",
        },
        {
            "inventory_id": "weread_fxbaogao_v5c_knowledge",
            "source_type": "local_external_knowledge_cards",
            "path": str(KNOWLEDGE / "v5c_defense_profit_taking"),
            "available": (root / KNOWLEDGE / "v5c_defense_profit_taking").exists(),
            "allowed_use": "governance, rebalancing, behavior, risk-control hypotheses",
            "blocked_use": "numeric thresholds or accepted status",
        },
        {
            "inventory_id": "quant_validation_methodology",
            "source_type": "local_methodology_knowledge",
            "path": str(QUANT_KNOWLEDGE / "methodology" / "factor_validation_methods.md"),
            "available": (root / QUANT_KNOWLEDGE / "methodology" / "factor_validation_methods.md").exists(),
            "allowed_use": "IC/RankIC, quantile, ablation, rolling validation design",
            "blocked_use": "skipping common-sample and PIT validation",
        },
        {
            "inventory_id": "public_network_or_apis",
            "source_type": "external_optional",
            "path": "BaoStock / public web / fxbaogao / official sources",
            "available": "not_called_in_this_packet",
            "allowed_use": "future data gap repair when explicitly needed",
            "blocked_use": "silent network fetch inside V5g startup package",
        },
    ]


def _five_new_model_specs() -> list[dict[str, Any]]:
    return [
        {
            "model_id": "v5g_01_state_gated_internal_subsleeve_70_30",
            "short_name": "state-gated champion",
            "base_success": "internal_subsleeve_mom12_70_30 + V5c P2/P3 overheat states",
            "fixed_hypothesis": "Keep V5f 70/30 internal sub-sleeve structure, but block new overweight build when sleeve state is valuation_price_flow_overheat_watch.",
            "expected_improvement_path": "reduce bad-timing adds into already-hot sleeves while preserving V57f pool and sleeve totals",
            "primary_data_needed": "P2 sleeve overheat state + V5f target weights/trades",
            "main_risk": "can mute a true trend winner; needs common-sample engineering before promotion",
            "research_status": "spec_ready_for_limited_engineering_decision",
            "accepted": False,
        },
        {
            "model_id": "v5g_02_quality_guarded_momentum_subsleeve",
            "short_name": "quality-guarded momentum",
            "base_success": "V5f internal sub-sleeve + V5c P1 financial quality panel",
            "fixed_hypothesis": "Momentum budget remains 30%, but momentum allocation must favor names with stronger PIT dividend/OCF/ROE quality inside the same V57f-selected sleeve.",
            "expected_improvement_path": "keep momentum edge while avoiding weak-cash-flow value traps and fragile dividend names",
            "primary_data_needed": "P1 financial quality PIT panel + V5f momentum ranks",
            "main_risk": "quality overlay may duplicate V57f value selection or reduce momentum breadth",
            "research_status": "spec_ready_for_factor_validation",
            "accepted": False,
        },
        {
            "model_id": "v5g_03_erc_state_budget_internal_subsleeve",
            "short_name": "ERC-state budget blend",
            "base_success": "V5f internal sub-sleeve + retained V5c ERC weak-portfolio fallback",
            "fixed_hypothesis": "Apply V5c ERC/weak-portfolio risk budget idea only as a sleeve-level risk review layer over V5f champion.",
            "expected_improvement_path": "reduce drawdown or unstable sleeve concentration without changing V57f stock pool",
            "primary_data_needed": "V5c ERC archive + P2/P3 broad/sleeve states + V5f NAV",
            "main_risk": "conflicts with ERC/defense boundary and may overfit state timing",
            "research_status": "separate_pm_spec_required_before_engineering",
            "accepted": False,
        },
        {
            "model_id": "v5g_04_profit_lock_cash_proxy_internal_subsleeve",
            "short_name": "profit-lock cash proxy",
            "base_success": "V5f champion + V5e 20/50 profit lock + 511360 cash proxy",
            "fixed_hypothesis": "If a pre-approved V5e-style exit happens on the V5f champion, cash drag is governed by 511360 proxy rather than idle cash.",
            "expected_improvement_path": "capture V5e drawdown/cash-governance benefit without treating V5e as V57f replacement",
            "primary_data_needed": "V5e exit/cash proxy packet + V5f champion holdings",
            "main_risk": "adds asset-class boundary and may dilute V5f champion edge",
            "research_status": "cash_proxy_data_gate_and_policy_spec_required",
            "accepted": False,
        },
        {
            "model_id": "v5g_05_short_window_reversion_confirmation_overlay",
            "short_name": "short-window repair overlay",
            "base_success": "short-window 5min reversion diagnostic + V5f champion",
            "fixed_hypothesis": "Use morning30/VWAP short-window reversion only as execution or temporary review confirmation inside V5f selected holdings.",
            "expected_improvement_path": "harvest liquidity shock repair without making an independent intraday stock-selection model",
            "primary_data_needed": "full holding-period 5min data + pre-2021 or forward validation",
            "main_risk": "highest overfit risk because strong result is inside 2021-2026 historical sample",
            "research_status": "diagnostic_until_independent_validation",
            "accepted": False,
        },
    ]


def _model_research_priority_matrix(model_specs: list[dict[str, Any]], success_transfer: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {
        "v5g_01_state_gated_internal_subsleeve_70_30": (1, 9, 8, 8, "Best next limited-engineering candidate: uses champion plus newly completed V5c state contract."),
        "v5g_02_quality_guarded_momentum_subsleeve": (2, 8, 7, 7, "Clean fundamental mechanism; needs IC/RankIC and ablation before engineering."),
        "v5g_03_erc_state_budget_internal_subsleeve": (3, 7, 5, 6, "Potential drawdown control but ERC conflict review required."),
        "v5g_04_profit_lock_cash_proxy_internal_subsleeve": (4, 6, 5, 5, "Uses proven cash governance but may be smaller edge than V5f champion."),
        "v5g_05_short_window_reversion_confirmation_overlay": (5, 8, 3, 4, "Potentially high edge, but validation risk is highest."),
    }
    rows = []
    for spec in model_specs:
        rank, evidence, governance, data, rationale = priority[spec["model_id"]]
        rows.append(
            {
                "priority_rank": rank,
                "model_id": spec["model_id"],
                "evidence_score_1_10": evidence,
                "governance_score_1_10": governance,
                "data_readiness_score_1_10": data,
                "rough_total_score": evidence + governance + data,
                "recommended_next_gate": _recommended_next_gate(spec["model_id"]),
                "priority_rationale": rationale,
            }
        )
    return sorted(rows, key=lambda row: int(row["priority_rank"]))


def _governance_boundary_matrix(model_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for spec in model_specs:
        rows.append(
            {
                "model_id": spec["model_id"],
                "v57f_core_modified_allowed": False,
                "new_stock_pool_allowed": False,
                "cross_sleeve_transfer_allowed": False,
                "threshold_scan_allowed": False,
                "accepted_allowed_now": False,
                "live_approved_allowed_now": False,
                "engineering_backtest_allowed_now": False,
                "requires_fixed_rule_before_engineering": True,
                "notes": "V5g startup admits research/spec only; limited engineering requires a separate explicit approval.",
            }
        )
    return rows


def _data_gate_requirements(model_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requirements = {
        "v5g_01_state_gated_internal_subsleeve_70_30": ["P2 sleeve overheat state by rebalance", "V5f champion target/actual weights", "turnover and cost audit"],
        "v5g_02_quality_guarded_momentum_subsleeve": ["P1 financial quality PIT fields", "V5f momentum ranks", "IC/RankIC and ablation outputs"],
        "v5g_03_erc_state_budget_internal_subsleeve": ["V5c ERC archive", "P2 broad trend state", "ERC conflict matrix"],
        "v5g_04_profit_lock_cash_proxy_internal_subsleeve": ["V5e exit logs", "511360 PIT price/liquidity gate", "cash proxy policy approval"],
        "v5g_05_short_window_reversion_confirmation_overlay": ["full holding-period 5min data", "pre-2021 or forward validation evidence", "PIT/no-reentry audit"],
    }
    rows = []
    for spec in model_specs:
        for item in requirements[spec["model_id"]]:
            rows.append(
                {
                    "model_id": spec["model_id"],
                    "requirement": item,
                    "status": "available_or_partial" if spec["model_id"] != "v5g_05_short_window_reversion_confirmation_overlay" else "validation_blocker",
                    "requires_network_now": False,
                    "requires_v57f_change": False,
                }
            )
    return rows


def _limited_research_queue(priority: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in priority:
        rows.append(
            {
                "priority": row["priority_rank"],
                "model_id": row["model_id"],
                "next_gate": row["recommended_next_gate"],
                "allowed_now": "spec_or_data_gate_only",
                "limited_engineering_allowed_now": False,
                "requires_user_approval_for_engineering": True,
                "status": "ready_for_prompt_generation" if int(row["priority_rank"]) <= 2 else "queued_after_p1_p2",
            }
        )
    return rows


def _pm_gate_decision(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passed = not blockers
    return [
        {
            "pm_gate_decision": "v5g_startup_pass_five_models_ready_for_spec_and_data_gates_not_backtest" if passed else "v5g_startup_blocked",
            "v5g_pass": str(passed),
            "model_count": 5,
            "admit_spec_generation": str(passed),
            "admit_limited_engineering_now": False,
            "admit_trading_rule": False,
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "network_fetch_started": False,
            "joinquant_started": False,
            "next_step": "generate_v5g_01_and_v5g_02_deep_prompts" if passed else "repair_v5g_inputs",
            "review_notes": "V5g startup creates five research models from governed V5f/V5c/V5e successes. It does not run backtests or accept models.",
        }
    ]


def _next_agent_queue(decision: dict[str, Any], limited_queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if decision["v5g_pass"] != "True":
        return [
            {
                "priority": 1,
                "next_gate": "repair_v5g_inputs",
                "model_id": "",
                "allowed": "True",
                "status": "blocked_until_repair",
            }
        ]
    return [
        {
            "priority": 1,
            "next_gate": "v5g_01_state_gated_internal_subsleeve_quant_spec",
            "model_id": "v5g_01_state_gated_internal_subsleeve_70_30",
            "allowed": "True",
            "status": "ready",
        },
        {
            "priority": 2,
            "next_gate": "v5g_02_quality_guarded_momentum_factor_validation",
            "model_id": "v5g_02_quality_guarded_momentum_subsleeve",
            "allowed": "True",
            "status": "ready",
        },
        {
            "priority": 3,
            "next_gate": "v5g_03_erc_state_budget_conflict_review",
            "model_id": "v5g_03_erc_state_budget_internal_subsleeve",
            "allowed": "True",
            "status": "queued",
        },
        {
            "priority": 4,
            "next_gate": "v5g_04_cash_proxy_policy_data_gate",
            "model_id": "v5g_04_profit_lock_cash_proxy_internal_subsleeve",
            "allowed": "True",
            "status": "queued",
        },
        {
            "priority": 5,
            "next_gate": "v5g_05_short_window_reversion_independent_validation_gate",
            "model_id": "v5g_05_short_window_reversion_confirmation_overlay",
            "allowed": "True",
            "status": "diagnostic_only_until_validation",
        },
    ]


def _v5g_blockers(
    midterm_summary: dict[str, Any],
    v5f_summary: dict[str, Any],
    v5c_p1: dict[str, Any],
    v5c_p2: dict[str, Any],
    v5c_p3: dict[str, Any],
    v5c_p4: dict[str, Any],
    v5c_overheat: dict[str, Any],
    v5e_511360: dict[str, Any],
) -> list[dict[str, Any]]:
    checks = [
        ("midterm_completed", midterm_summary.get("status") == "completed_midterm_report", midterm_summary.get("status", "")),
        ("midterm_repaired_baseline", midterm_summary.get("historical_backtest_scope", {}).get("benchmark") == "v57f_startup_preload_repaired_baseline", str(midterm_summary.get("historical_backtest_scope", {}))),
        ("v5f_champion_available", v5f_summary.get("fatal_blocker_count") == 0, v5f_summary.get("pm_gate_decision", "")),
        ("v5c_p1_available", v5c_p1.get("fatal_blocker_count") == 0, v5c_p1.get("pm_gate_decision", "")),
        ("v5c_p2_available", v5c_p2.get("fatal_blocker_count") == 0, v5c_p2.get("pm_gate_decision", "")),
        ("v5c_p3_available", v5c_p3.get("fatal_blocker_count") == 0, v5c_p3.get("pm_gate_decision", "")),
        ("v5c_p4_available", v5c_p4.get("fatal_blocker_count") == 0, v5c_p4.get("pm_gate_decision", "")),
        ("v5c_overheat_spec_available", v5c_overheat.get("fatal_blocker_count") == 0, v5c_overheat.get("pm_gate_decision", "")),
        ("v5e_511360_available", v5e_511360.get("fatal_blocker_count") == 0, v5e_511360.get("pm_gate_decision", "")),
    ]
    return [
        {
            "blocker_id": check_id,
            "severity": "fatal",
            "status": "blocking",
            "observed": observed,
            "description": "Required V5g startup dependency failed.",
        }
        for check_id, passed, observed in checks
        if not passed
    ]


def _summary(
    status: str,
    decision: str,
    blockers: list[dict[str, Any]],
    model_count: int = 0,
    top_priority_model: str = "",
    primary_v5f_candidate: str = "",
    primary_v5f_delta_return_pct_points_vs_repaired_baseline: Any = "",
    v5c_state_gate_available: bool = False,
    v5e_cash_proxy_available: bool = False,
    external_knowledge_sources: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5g_cross_line_model_research_startup",
        "status": status,
        "pm_gate_decision": decision,
        "model_count": model_count,
        "top_priority_model": top_priority_model,
        "primary_v5f_candidate": primary_v5f_candidate,
        "primary_v5f_delta_return_pct_points_vs_repaired_baseline": primary_v5f_delta_return_pct_points_vs_repaired_baseline,
        "v5c_state_gate_available": v5c_state_gate_available,
        "v5e_cash_proxy_available": v5e_cash_proxy_available,
        "external_knowledge_sources": external_knowledge_sources,
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
            "summary": str(OUT_DIR / "v5g_cross_line_model_research_summary.json"),
            "report": str(OUT_DIR / "v5g_cross_line_model_research_report.md"),
            "five_new_model_specs": str(OUT_DIR / "v5g_five_new_model_specs.csv"),
            "priority_matrix": str(OUT_DIR / "v5g_model_research_priority_matrix.csv"),
            "next_queue": str(OUT_DIR / "v5g_next_agent_queue.csv"),
        },
    }


def _report(
    midterm_summary: dict[str, Any],
    v5f_metrics: list[dict[str, str]],
    model_specs: list[dict[str, Any]],
    priority: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
) -> str:
    baseline = midterm_summary.get("baseline", {})
    primary = midterm_summary.get("primary_candidate", {})
    model_lines = [f"- `{row['model_id']}`: {row['fixed_hypothesis']}" for row in model_specs]
    priority_lines = [f"- P{row['priority_rank']} `{row['model_id']}`: {row['recommended_next_gate']}" for row in priority]
    queue_lines = [f"- P{row['priority']} `{row['next_gate']}`: {row['status']}" for row in next_queue]
    return "\n".join(
        [
            "# V5g Cross-Line Model Research Startup",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Repaired baseline return: `{baseline.get('strategy_return_pct', '')}%`",
            f"- V5f primary candidate: `{primary.get('model_id', '')}` delta `{primary.get('delta_return_pct_points_vs_repaired_baseline', '')}` pct",
            "- Accepted: `False`",
            "- Engineering backtest started: `False`",
            "- V57f core modified: `False`",
            "",
            "## Five New Model Directions",
            *model_lines,
            "",
            "## Priority",
            *priority_lines,
            "",
            "## Next Queue",
            *queue_lines,
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5g Agent Execution Rules",
            "",
            "1. Use `v57f_startup_preload_repaired` as the benchmark lineage; do not use old first_signal 2021-10-08.",
            "2. V5g startup generates research/spec directions only; no accepted, live approval, or V57f replacement.",
            "3. Do not modify V57f core, target_count, sleeve structure, caps, or rebalance cadence.",
            "4. Do not scan thresholds or choose variants by historical return.",
            "5. External knowledge can suggest hypotheses but cannot provide PIT values, thresholds, or accepted status.",
            "6. Limited engineering requires a separate explicit approval for one fixed model.",
            "",
        ]
    )


def _next_prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5g model 01 / 02 deep spec queue：state-gated champion 与 quality-guarded momentum 深层研究

任务目标：
基于 v5g_cross_line_model_research_startup/current 输出，优先推进：
1. v5g_01_state_gated_internal_subsleeve_70_30
2. v5g_02_quality_guarded_momentum_subsleeve

只做 Quant spec / data gate / validation design，不标记 accepted，不直接工程回测，除非另行明确批准 limited engineering。
"""


def _transferable_mechanism(model_id: str) -> str:
    if "internal_subsleeve" in model_id:
        return "separate value/fundamental and momentum budgets inside sleeve"
    if "erc" in model_id:
        return "portfolio risk-budget fallback and drawdown control discipline"
    if "511360" in model_id or "cash_proxy" in model_id:
        return "cash drag mitigation through governed cash proxy"
    if "momentum_plus_mean" in model_id:
        return "combined but weak overlay benchmark"
    return "diagnostic evidence"


def _v5g_use(model_id: str) -> str:
    if "internal_subsleeve_mom12_70_30" in model_id:
        return "primary base architecture"
    if "internal_subsleeve_mom12_80_20" in model_id:
        return "stress reference for lower momentum budget"
    if "erc" in model_id:
        return "risk budget branch with conflict review"
    if "511360" in model_id:
        return "cash governance branch"
    return "secondary comparison only"


def _recommended_next_gate(model_id: str) -> str:
    mapping = {
        "v5g_01_state_gated_internal_subsleeve_70_30": "v5g_01_state_gated_internal_subsleeve_quant_spec",
        "v5g_02_quality_guarded_momentum_subsleeve": "v5g_02_quality_guarded_momentum_factor_validation",
        "v5g_03_erc_state_budget_internal_subsleeve": "v5g_03_erc_state_budget_conflict_review",
        "v5g_04_profit_lock_cash_proxy_internal_subsleeve": "v5g_04_cash_proxy_policy_data_gate",
        "v5g_05_short_window_reversion_confirmation_overlay": "v5g_05_short_window_reversion_independent_validation_gate",
    }
    return mapping[model_id]


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    blockers = []
    for rel in REQUIRED_INPUTS:
        path = root / rel
        if not path.exists():
            blockers.append(
                {
                    "blocker_id": f"missing_{rel.name}",
                    "severity": "fatal",
                    "status": "blocking",
                    "path": str(rel),
                    "description": "Required V5g startup input is missing.",
                }
            )
    return blockers


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
    run_v5g_cross_line_model_research_startup()
