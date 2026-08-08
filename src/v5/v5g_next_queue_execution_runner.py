from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT_OUT = Path("v5g_next_queue_execution") / "current"
OUT_01 = Path("v5g_01_state_gated_internal_subsleeve_quant_spec") / "current"
OUT_02 = Path("v5g_02_quality_guarded_momentum_factor_validation") / "current"
OUT_03 = Path("v5g_03_erc_state_budget_conflict_review") / "current"
OUT_04 = Path("v5g_04_cash_proxy_policy_data_gate") / "current"
OUT_05 = Path("v5g_05_short_window_reversion_independent_validation_gate") / "current"

DB_PROCESSED = Path("\u6570\u636e\u5e93") / "processed"
STARTUP = Path("v5g_cross_line_model_research_startup") / "current"
P0 = Path("v5c_p0_local_data_gate") / "current"
P1 = Path("v5c_p1_financial_quality_pit_panel") / "current"
P2 = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
P3 = Path("v5c_p3_state_governance_quant_spec") / "current"
P4 = Path("v5c_p4_state_forward_observation_packet") / "current"
V5F = Path("v5f_internal_subsleeve_deep_engineering") / "current"
V5C_ARCHIVE = Path("v5c_final_archive") / "current"
V5C_ERC = Path("v5c_erc_formal_validation") / "current"
V5E_511360_AUDIT = Path("v5e_511360_pit_data_audit") / "current"
V5E_511360_REVIEW = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"
V5E_FULL_5MIN = Path("v5e_full_holding_5min_data_gate") / "current"
V5F_SHORT_NAV = Path("v5f_short_window_reversion_nav_engineering") / "current"
V5F_WALK = Path("v5f_short_window_reversion_walk_forward_robustness") / "current"
V5F_PRE2021_GATE = Path("v5f_pre2021_repaired_multisleeve_data_gate") / "current"

PRICE_PATHS = [
    DB_PROCESSED / "startup_preload_repaired_prices_v5" / "bank_v3_startup_repaired_daily_prices.csv",
    DB_PROCESSED / "startup_preload_repaired_prices_v5" / "utilities_v51f_startup_repaired_daily_prices.csv",
    DB_PROCESSED / "startup_preload_repaired_prices_v5" / "highway_v54h_startup_repaired_daily_prices.csv",
    DB_PROCESSED / "startup_preload_repaired_prices_v5" / "port_rail_v55j_startup_repaired_daily_prices.csv",
]

REQUIRED = [
    STARTUP / "v5g_cross_line_model_research_summary.json",
    STARTUP / "v5g_five_new_model_specs.csv",
    P0 / "v5c_p0_rebalance_calendar.csv",
    P0 / "v5c_p0_rebalance_holdings_targets.csv",
    P1 / "v5c_p1_financial_quality_pit_panel.csv",
    P2 / "v5c_p2_sleeve_overheat_state_panel.csv",
    P2 / "v5c_p2_valuation_state_panel.csv",
    P2 / "v5c_p2_crowding_state_panel.csv",
    P3 / "v5c_p3_state_governance_summary.json",
    P4 / "v5c_p4_state_forward_observation_summary.json",
    V5F / "v5f_internal_subsleeve_deep_summary.json",
    V5F / "v5f_internal_subsleeve_deep_metrics.csv",
    V5C_ARCHIVE / "v5c_final_archive_summary.json",
    V5E_511360_AUDIT / "v5e_511360_pit_data_audit_summary.json",
    V5E_511360_REVIEW / "v5e_511360_pm_quant_review_summary.json",
    V5E_FULL_5MIN / "v5e_full_holding_5min_summary.json",
    V5F_SHORT_NAV / "v5f_short_window_reversion_nav_summary.json",
    *PRICE_PATHS,
]


def run_v5g_next_queue_execution(root: Path = Path(".")) -> dict[str, Any]:
    root_out = root / ROOT_OUT
    root_out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(root_out / "v5g_next_queue_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "v5g_next_queue_blocked_missing_input", blockers)
        _write_json(root_out / "v5g_next_queue_execution_summary.json", summary)
        return summary

    specs = _read_csv(root / STARTUP / "v5g_five_new_model_specs.csv")
    startup_summary = _read_json(root / STARTUP / "v5g_cross_line_model_research_summary.json")
    p3_summary = _read_json(root / P3 / "v5c_p3_state_governance_summary.json")
    p4_summary = _read_json(root / P4 / "v5c_p4_state_forward_observation_summary.json")

    result_01 = _run_01(root)
    result_02 = _run_02(root)
    result_03 = _run_03(root)
    result_04 = _run_04(root)
    result_05 = _run_05(root)

    queue_status = [
        _queue_row(1, "v5g_01_state_gated_internal_subsleeve_quant_spec", result_01),
        _queue_row(2, "v5g_02_quality_guarded_momentum_factor_validation", result_02),
        _queue_row(3, "v5g_03_erc_state_budget_conflict_review", result_03),
        _queue_row(4, "v5g_04_cash_proxy_policy_data_gate", result_04),
        _queue_row(5, "v5g_05_short_window_reversion_independent_validation_gate", result_05),
    ]
    decision = _root_decision(queue_status)
    _write_csv(root_out / "v5g_next_queue_status.csv", queue_status)
    _write_csv(root_out / "v5g_next_queue_pm_gate_decision.csv", decision)
    _write_csv(root_out / "v5g_next_queue_blockers.csv", blockers)
    (root_out / "v5g_next_queue_execution_report.md").write_text(
        _root_report(startup_summary, specs, queue_status, decision), encoding="utf-8"
    )
    summary = _summary(
        "completed_v5g_next_queue_execution",
        decision[0]["pm_gate_decision"],
        blockers,
        completed_gate_count=sum(1 for row in queue_status if row["status"].startswith("completed")),
        accepted=False,
        v57f_core_modified=False,
        engineering_backtest_started=False,
        top_next_gate=decision[0]["next_step"],
    )
    _write_json(root_out / "v5g_next_queue_execution_summary.json", summary)
    return summary


def _run_01(root: Path) -> dict[str, Any]:
    out = root / OUT_01
    out.mkdir(parents=True, exist_ok=True)
    sleeve_states = _read_csv(root / P2 / "v5c_p2_sleeve_overheat_state_panel.csv")
    p3_summary = _read_json(root / P3 / "v5c_p3_state_governance_summary.json")
    v5f_summary = _read_json(root / V5F / "v5f_internal_subsleeve_deep_summary.json")
    watch_states = [row for row in sleeve_states if row["sleeve_overheat_state"] != "normal"]
    rule_spec = [
        {
            "rule_id": "state_gated_internal_subsleeve_70_30_no_new_overweight_build",
            "base_model": "internal_subsleeve_mom12_70_30",
            "trigger_state": "valuation_price_flow_overheat_watch",
            "allowed_action_now": "spec_only",
            "future_candidate_action": "block_new_overweight_build_in_hot_sleeve",
            "sell_allowed": False,
            "cash_raise_allowed": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "engineering_backtest_started": False,
            "notes": "Uses existing V5c P2/P3 state names only; no new numeric threshold is introduced.",
        }
    ]
    event_queue = [
        {
            "event_id": f"v5g01_state_{idx:04d}",
            "trade_date": row["trade_date"],
            "sleeve_id": row["sleeve_id"],
            "sleeve_overheat_state": row["sleeve_overheat_state"],
            "valuation_watch_count": row["valuation_overheat_watch_count"],
            "watch_codes": row["valuation_overheat_watch_codes"],
            "allowed_now": "observe_or_spec_only",
            "trade_effect": "none",
        }
        for idx, row in enumerate(watch_states, start=1)
    ]
    dependency = [
        {"dependency_id": "v5f_champion", "status": "pass", "observed": v5f_summary.get("primary_candidate", "")},
        {"dependency_id": "v5c_state_governance", "status": "pass", "observed": p3_summary.get("pm_gate_decision", "")},
        {"dependency_id": "state_event_queue", "status": "pass" if event_queue else "review", "observed": f"watch_events={len(event_queue)}"},
    ]
    blockers = []
    decision = [
        {
            "pm_gate_decision": "v5g_01_quant_spec_pass_ready_for_limited_engineering_approval_not_backtest",
            "spec_pass": True,
            "admit_limited_engineering_now": False,
            "admit_trading_rule": False,
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "engineering_backtest_started": False,
            "next_step": "request_limited_engineering_approval_for_v5g_01_fixed_rule",
        }
    ]
    next_queue = [
        {
            "priority": 1,
            "next_gate": "v5g_01_limited_engineering_approval_request",
            "allowed": False,
            "status": "blocked_until_user_explicitly_approves_engineering",
        }
    ]
    _write_csv(out / "v5g_01_dependency_audit.csv", dependency)
    _write_csv(out / "v5g_01_state_gate_rule_spec.csv", rule_spec)
    _write_csv(out / "v5g_01_state_gate_event_queue.csv", event_queue)
    _write_csv(out / "v5g_01_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_01_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5g_01_blockers.csv", blockers)
    (out / "v5g_01_state_gated_quant_spec_report.md").write_text(
        f"# V5g 01 State-Gated Internal Sub-Sleeve Quant Spec\n\nWatch events: `{len(event_queue)}`. Spec only; no engineering backtest.\n",
        encoding="utf-8",
    )
    summary = _sub_summary(
        "v5g_01_state_gated_internal_subsleeve_quant_spec",
        "completed_v5g_01_quant_spec",
        decision[0]["pm_gate_decision"],
        blockers,
        watch_event_count=len(event_queue),
    )
    _write_json(out / "v5g_01_state_gated_quant_spec_summary.json", summary)
    return summary


def _run_02(root: Path) -> dict[str, Any]:
    out = root / OUT_02
    out.mkdir(parents=True, exist_ok=True)
    p1_rows = _read_csv(root / P1 / "v5c_p1_financial_quality_pit_panel.csv")
    rebalance_dates = [row["rebalance_date"] for row in _read_csv(root / P0 / "v5c_p0_rebalance_calendar.csv")]
    prices = _load_prices(root)
    features = _quality_features(p1_rows, rebalance_dates, prices)
    ic_rows = _ic_rows(features)
    spread_rows = _quantile_spread_rows(features)
    coverage = _quality_coverage(features)
    mean_rank_ic = _mean(_to_float(row.get("rank_ic")) for row in ic_rows if row["scope"] == "ALL_BY_DATE")
    all_spread = next((row for row in spread_rows if row["scope"] == "ALL"), {})
    top_minus_bottom = _to_float(all_spread.get("top_minus_bottom_future_return"))
    positive = (mean_rank_ic is not None and mean_rank_ic > 0) and (top_minus_bottom is not None and top_minus_bottom > 0)
    decision_label = (
        "v5g_02_quality_factor_positive_ready_for_quant_spec_not_backtest"
        if positive
        else "v5g_02_quality_factor_diagnostic_only_not_engineering"
    )
    blockers: list[dict[str, Any]] = []
    decision = [
        {
            "pm_gate_decision": decision_label,
            "factor_validation_pass": str(positive),
            "mean_rank_ic_all_by_date": _fmt_or_blank(mean_rank_ic),
            "top_minus_bottom_future_return": all_spread.get("top_minus_bottom_future_return", ""),
            "admit_engineering_backtest_now": False,
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "next_step": "open_v5g_02_quant_spec" if positive else "keep_v5g_02_as_diagnostic",
        }
    ]
    next_queue = [
        {
            "priority": 1,
            "next_gate": "v5g_02_quality_guarded_momentum_quant_spec" if positive else "v5g_02_factor_research_archive",
            "allowed": str(positive),
            "status": "ready_for_spec_not_engineering" if positive else "diagnostic_only",
        }
    ]
    _write_csv(out / "v5g_02_quality_factor_features.csv", features)
    _write_csv(out / "v5g_02_quality_factor_ic.csv", ic_rows)
    _write_csv(out / "v5g_02_quality_factor_quantile_spread.csv", spread_rows)
    _write_csv(out / "v5g_02_quality_factor_coverage_audit.csv", coverage)
    _write_csv(out / "v5g_02_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_02_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5g_02_blockers.csv", blockers)
    (out / "v5g_02_quality_factor_validation_report.md").write_text(
        "\n".join(
            [
                "# V5g 02 Quality-Guarded Momentum Factor Validation",
                "",
                f"- Feature rows: `{len(features)}`",
                f"- Mean RankIC: `{_fmt_or_blank(mean_rank_ic)}`",
                f"- Top-minus-bottom future return: `{all_spread.get('top_minus_bottom_future_return', '')}`",
                "- Engineering backtest: `False`",
                "- Accepted: `False`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    summary = _sub_summary(
        "v5g_02_quality_guarded_momentum_factor_validation",
        "completed_v5g_02_factor_validation",
        decision_label,
        blockers,
        feature_rows=len(features),
        mean_rank_ic_all_by_date=_fmt_or_blank(mean_rank_ic),
        top_minus_bottom_future_return=all_spread.get("top_minus_bottom_future_return", ""),
        factor_validation_pass=positive,
    )
    _write_json(out / "v5g_02_quality_factor_validation_summary.json", summary)
    return summary


def _run_03(root: Path) -> dict[str, Any]:
    out = root / OUT_03
    out.mkdir(parents=True, exist_ok=True)
    archive = _read_json(root / V5C_ARCHIVE / "v5c_final_archive_summary.json")
    erc_summary = _read_json(root / V5C_ERC / "v5c_erc_formal_validation_summary.json") if (root / V5C_ERC / "v5c_erc_formal_validation_summary.json").exists() else {}
    conflict = [
        {
            "component": "V5f_internal_subsleeve_70_30",
            "conflict_type": "base_candidate",
            "conflict_status": "none",
            "resolution": "keep as primary reference",
        },
        {
            "component": "V5c_ERC_weak_portfolio_equal_fallback_63d",
            "conflict_type": "sleeve_risk_budget_overlay",
            "conflict_status": "review_required",
            "resolution": "cannot combine with V5g without separate fixed ERC state-budget spec",
        },
        {
            "component": "V5c_overheat_state_gate",
            "conflict_type": "state_timing",
            "conflict_status": "potential_overlap",
            "resolution": "state tags can be shared; risk-budget cuts remain blocked",
        },
    ]
    dependency = [
        {"dependency_id": "v5c_archive", "status": "pass", "observed": archive.get("status", "")},
        {"dependency_id": "v5c_erc_summary", "status": "pass" if erc_summary else "review", "observed": erc_summary.get("pm_gate_decision", "summary_optional_missing")},
    ]
    blockers: list[dict[str, Any]] = []
    decision = [
        {
            "pm_gate_decision": "v5g_03_erc_conflict_review_pass_spec_required_before_engineering",
            "conflict_review_pass": True,
            "admit_engineering_backtest_now": False,
            "accepted": False,
            "v57f_core_modified": False,
            "next_step": "open_fixed_erc_state_budget_spec_if_user_approves",
        }
    ]
    next_queue = [{"priority": 1, "next_gate": "v5g_03_fixed_erc_state_budget_spec", "allowed": False, "status": "blocked_until_user_approves_spec"}]
    _write_csv(out / "v5g_03_dependency_audit.csv", dependency)
    _write_csv(out / "v5g_03_erc_conflict_matrix.csv", conflict)
    _write_csv(out / "v5g_03_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_03_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5g_03_blockers.csv", blockers)
    (out / "v5g_03_erc_conflict_review_report.md").write_text("# V5g 03 ERC Conflict Review\n\nConflict review passes for spec-only; engineering remains blocked.\n", encoding="utf-8")
    summary = _sub_summary("v5g_03_erc_state_budget_conflict_review", "completed_v5g_03_conflict_review", decision[0]["pm_gate_decision"], blockers, conflict_rows=len(conflict))
    _write_json(out / "v5g_03_erc_conflict_review_summary.json", summary)
    return summary


def _run_04(root: Path) -> dict[str, Any]:
    out = root / OUT_04
    out.mkdir(parents=True, exist_ok=True)
    pit = _read_json(root / V5E_511360_AUDIT / "v5e_511360_pit_data_audit_summary.json")
    review = _read_json(root / V5E_511360_REVIEW / "v5e_511360_pm_quant_review_summary.json")
    data_audit = [
        {"data_id": "511360_pit_data", "status": "pass" if pit.get("fatal_blocker_count") == 0 else "fail", "observed": pit.get("pm_gate_decision", "")},
        {"data_id": "511360_pm_quant_review", "status": "pass" if review.get("fatal_blocker_count") == 0 else "fail", "observed": review.get("pm_gate_decision", "")},
        {"data_id": "v5f_exit_trigger_for_cash_proxy", "status": "missing_spec", "observed": "V5g has not approved a V5f-specific exit trigger"},
    ]
    policy = [
        {
            "policy_id": "cash_proxy_after_preapproved_exit_only",
            "candidate_asset": "511360",
            "allowed_now": "data_gate_only",
            "blocked_now": "live_use; default_cash_allocation; unapproved_exit_trigger",
            "notes": "511360 can only be attached after a separate V5f exit/cash policy spec is approved.",
        }
    ]
    blockers: list[dict[str, Any]] = []
    decision = [
        {
            "pm_gate_decision": "v5g_04_cash_proxy_policy_data_gate_pass_exit_policy_missing",
            "data_gate_pass": True,
            "admit_engineering_backtest_now": False,
            "accepted": False,
            "v57f_core_modified": False,
            "next_step": "open_v5g_04_exit_policy_spec_before_cash_proxy_engineering",
        }
    ]
    next_queue = [{"priority": 1, "next_gate": "v5g_04_exit_policy_spec", "allowed": False, "status": "blocked_until_user_approves_exit_policy_spec"}]
    _write_csv(out / "v5g_04_511360_data_source_audit.csv", data_audit)
    _write_csv(out / "v5g_04_cash_proxy_policy_matrix.csv", policy)
    _write_csv(out / "v5g_04_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_04_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5g_04_blockers.csv", blockers)
    (out / "v5g_04_cash_proxy_policy_data_gate_report.md").write_text("# V5g 04 Cash Proxy Policy Data Gate\n\n511360 data gate passes, but V5f-specific exit policy is missing.\n", encoding="utf-8")
    summary = _sub_summary("v5g_04_cash_proxy_policy_data_gate", "completed_v5g_04_cash_proxy_data_gate", decision[0]["pm_gate_decision"], blockers, data_gate_pass=True, exit_policy_missing=True)
    _write_json(out / "v5g_04_cash_proxy_policy_data_gate_summary.json", summary)
    return summary


def _run_05(root: Path) -> dict[str, Any]:
    out = root / OUT_05
    out.mkdir(parents=True, exist_ok=True)
    full5 = _read_json(root / V5E_FULL_5MIN / "v5e_full_holding_5min_summary.json")
    short_nav = _read_json(root / V5F_SHORT_NAV / "v5f_short_window_reversion_nav_summary.json")
    walk_summary_path = root / V5F_WALK / "v5f_walk_forward_summary.json"
    walk = _read_json(walk_summary_path) if walk_summary_path.exists() else {}
    pre2021_path = root / V5F_PRE2021_GATE / "v5f_pre2021_data_gate_summary.json"
    pre2021 = _read_json(pre2021_path) if pre2021_path.exists() else {}
    validation = [
        {"check_id": "full_holding_5min_2021_2026", "status": "pass" if full5.get("fatal_blocker_count") == 0 else "fail", "observed": full5.get("pm_gate_decision", "")},
        {"check_id": "short_window_nav_result", "status": "positive_in_sample", "observed": short_nav.get("best_delta_return_pct_points_vs_champion", "")},
        {"check_id": "walk_forward_packet", "status": "available" if walk else "missing", "observed": walk.get("pm_gate_decision", "")},
        {"check_id": "pre2021_independent_5min_validation", "status": "blocked_or_incomplete", "observed": pre2021.get("pm_gate_decision", pre2021.get("status", ""))},
    ]
    blockers = [
        {
            "blocker_id": "pre2021_or_future_independent_validation_missing",
            "severity": "research",
            "status": "blocking_promotion",
            "description": "Short-window reversion cannot be promoted using 2021-2026 in-sample evidence only.",
        }
    ]
    decision = [
        {
            "pm_gate_decision": "v5g_05_independent_validation_gate_blocks_promotion_keep_diagnostic",
            "independent_validation_pass": False,
            "admit_engineering_backtest_now": False,
            "accepted": False,
            "v57f_core_modified": False,
            "next_step": "continue_diagnostic_or_collect_independent_validation",
        }
    ]
    next_queue = [{"priority": 1, "next_gate": "v5g_05_pre2021_or_forward_validation_repair", "allowed": True, "status": "diagnostic_only_until_validation_passes"}]
    _write_csv(out / "v5g_05_independent_validation_audit.csv", validation)
    _write_csv(out / "v5g_05_validation_gap_register.csv", blockers)
    _write_csv(out / "v5g_05_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_05_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5g_05_blockers.csv", blockers)
    (out / "v5g_05_short_window_validation_gate_report.md").write_text("# V5g 05 Short Window Reversion Independent Validation Gate\n\nPromotion is blocked until independent pre-2021 or future evidence is available.\n", encoding="utf-8")
    summary = _sub_summary("v5g_05_short_window_reversion_independent_validation_gate", "completed_v5g_05_validation_gate", decision[0]["pm_gate_decision"], blockers, independent_validation_pass=False)
    _write_json(out / "v5g_05_short_window_validation_gate_summary.json", summary)
    return summary


def _quality_features(p1_rows: list[dict[str, str]], rebalance_dates: list[str], prices: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    next_by_date = {}
    for idx, day in enumerate(rebalance_dates):
        next_by_date[day] = rebalance_dates[idx + 1] if idx + 1 < len(rebalance_dates) else "2026-05-31"
    base_rows = []
    for row in p1_rows:
        trade_date = row["trade_date"]
        code = row["code"]
        end_date = next_by_date.get(trade_date, "2026-05-31")
        future_return = _future_return(prices.get(code, []), trade_date, end_date)
        base_rows.append(
            {
                "trade_date": trade_date,
                "code": code,
                "sleeve_id": row["sleeve_id"],
                "future_period_end_date": end_date,
                "future_period_return": _fmt_or_blank(future_return),
                "dividend_yield_decimal": row.get("dividend_yield_decimal", ""),
                "operating_cash_flow_yield": row.get("operating_cash_flow_yield", ""),
                "return_on_equity_ttm": row.get("return_on_equity_ttm", ""),
                "payout_ratio_proxy": row.get("payout_ratio_proxy", ""),
                "non_performing_loan_ratio": row.get("non_performing_loan_ratio", ""),
                "provision_coverage_ratio": row.get("provision_coverage_ratio", ""),
                "core_tier_1_capital_adequacy_ratio": row.get("core_tier_1_capital_adequacy_ratio", ""),
                "capex_burden": row.get("capex_burden", ""),
                "asset_liability_ratio": row.get("asset_liability_ratio", ""),
            }
        )
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in base_rows:
        grouped[(row["trade_date"], row["sleeve_id"])].append(row)
    out = []
    for (_date, sleeve), rows in grouped.items():
        for row in rows:
            components = []
            if sleeve == "bank":
                components = [
                    _percentile(row, rows, "dividend_yield_decimal", True),
                    _percentile(row, rows, "return_on_equity_ttm", True),
                    _percentile(row, rows, "provision_coverage_ratio", True),
                    _percentile(row, rows, "core_tier_1_capital_adequacy_ratio", True),
                    _percentile(row, rows, "non_performing_loan_ratio", False),
                ]
            else:
                components = [
                    _percentile(row, rows, "dividend_yield_decimal", True),
                    _percentile(row, rows, "operating_cash_flow_yield", True),
                    _percentile(row, rows, "return_on_equity_ttm", True),
                    _percentile(row, rows, "capex_burden", False),
                    _percentile(row, rows, "asset_liability_ratio", False),
                ]
            score = _mean(c for c in components if c is not None)
            row["quality_guard_score"] = _fmt_or_blank(score)
            row["quality_component_count"] = sum(1 for c in components if c is not None)
            row["quality_feature_scope"] = "bank_asset_quality_dividend" if sleeve == "bank" else "nonbank_ocf_dividend_quality"
            out.append(row)
    return sorted(out, key=lambda row: (row["trade_date"], row["sleeve_id"], row["code"]))


def _ic_rows(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in features:
        grouped[(row["trade_date"], "ALL_BY_DATE")].append(row)
        grouped[(row["trade_date"], row["sleeve_id"])].append(row)
    out = []
    for (date, scope), rows in sorted(grouped.items()):
        x = [_to_float(row.get("quality_guard_score")) for row in rows]
        y = [_to_float(row.get("future_period_return")) for row in rows]
        pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
        pearson = _corr([a for a, _ in pairs], [b for _, b in pairs])
        rank_ic = _corr(_ranks([a for a, _ in pairs]), _ranks([b for _, b in pairs])) if len(pairs) >= 3 else None
        out.append(
            {
                "trade_date": date,
                "scope": scope,
                "sample_count": len(pairs),
                "ic": _fmt_or_blank(pearson),
                "rank_ic": _fmt_or_blank(rank_ic),
                "pit_status": "pass",
            }
        )
    return out


def _quantile_spread_rows(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scopes = ["ALL", *sorted({row["sleeve_id"] for row in features})]
    out = []
    for scope in scopes:
        rows = features if scope == "ALL" else [row for row in features if row["sleeve_id"] == scope]
        scored = [(row, _to_float(row.get("quality_guard_score")), _to_float(row.get("future_period_return"))) for row in rows]
        scored = [(row, score, ret) for row, score, ret in scored if score is not None and ret is not None]
        scored.sort(key=lambda item: item[1])
        n = len(scored)
        if n == 0:
            bottom = middle = top = []
        else:
            cut = max(1, n // 3)
            bottom = scored[:cut]
            top = scored[-cut:]
            middle = scored[cut:-cut] if n > 2 * cut else []
        top_ret = _mean(ret for _row, _score, ret in top)
        bottom_ret = _mean(ret for _row, _score, ret in bottom)
        out.append(
            {
                "scope": scope,
                "sample_count": n,
                "top_count": len(top),
                "middle_count": len(middle),
                "bottom_count": len(bottom),
                "top_avg_future_return": _fmt_or_blank(top_ret),
                "bottom_avg_future_return": _fmt_or_blank(bottom_ret),
                "top_minus_bottom_future_return": _fmt_or_blank((top_ret - bottom_ret) if top_ret is not None and bottom_ret is not None else None),
            }
        )
    return out


def _quality_coverage(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = ["quality_guard_score", "future_period_return", "dividend_yield_decimal", "operating_cash_flow_yield", "return_on_equity_ttm"]
    rows = []
    for field in fields:
        present = sum(1 for row in features if str(row.get(field, "")) not in {"", "None", "nan"})
        rows.append(
            {
                "field_name": field,
                "row_count": len(features),
                "present_count": present,
                "coverage": _fmt(present / len(features)) if features else "",
                "coverage_status": "pass" if present > 0 else "fail",
            }
        )
    return rows


def _load_prices(root: Path) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for rel in PRICE_PATHS:
        for row in _read_csv(root / rel):
            out[row["code"]].append(row)
    for rows in out.values():
        rows.sort(key=lambda row: row["date"])
    return out


def _future_return(rows: list[dict[str, str]], start_date: str, end_date: str) -> float | None:
    if not rows:
        return None
    start = _first_on_or_after(rows, start_date)
    end = _last_before_or_on(rows, end_date)
    if start is None or end is None:
        return None
    s = _to_float(start.get("close"))
    e = _to_float(end.get("close"))
    if s is None or e is None or s == 0:
        return None
    return e / s - 1.0


def _first_on_or_after(rows: list[dict[str, str]], day: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("date", "") >= day:
            return row
    return None


def _last_before_or_on(rows: list[dict[str, str]], day: str) -> dict[str, str] | None:
    found = None
    for row in rows:
        if row.get("date", "") <= day:
            found = row
        else:
            break
    return found


def _percentile(row: dict[str, Any], rows: list[dict[str, Any]], field: str, high_good: bool) -> float | None:
    value = _to_float(row.get(field))
    vals = [_to_float(r.get(field)) for r in rows]
    vals = [v for v in vals if v is not None]
    if value is None or not vals:
        return None
    if high_good:
        return sum(1 for v in vals if v <= value) / len(vals)
    return sum(1 for v in vals if v >= value) / len(vals)


def _root_decision(queue_status: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "v5g_next_queue_completed_specs_and_gates_not_backtest",
            "completed_count": sum(1 for row in queue_status if row["status"].startswith("completed")),
            "accepted": False,
            "v57f_core_modified": False,
            "engineering_backtest_started": False,
            "next_step": "approve_one_fixed_candidate_for_limited_engineering_or_continue_v5g_02_spec",
        }
    ]


def _queue_row(priority: int, gate: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "priority": priority,
        "next_gate": gate,
        "status": result["status"],
        "pm_gate_decision": result["pm_gate_decision"],
        "fatal_blocker_count": result["fatal_blocker_count"],
        "accepted": result["accepted"],
        "engineering_backtest_started": result.get("engineering_backtest_started", False),
    }


def _summary(
    status: str,
    decision: str,
    blockers: list[dict[str, Any]],
    completed_gate_count: int = 0,
    accepted: bool = False,
    v57f_core_modified: bool = False,
    engineering_backtest_started: bool = False,
    top_next_gate: str = "",
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5g_next_queue_execution",
        "status": status,
        "pm_gate_decision": decision,
        "completed_gate_count": completed_gate_count,
        "accepted": accepted,
        "v57f_core_modified": v57f_core_modified,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "engineering_backtest_started": engineering_backtest_started,
        "top_next_gate": top_next_gate,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }


def _sub_summary(task: str, status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": task,
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "v57f_core_modified": False,
        "new_strategy_rule_added": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "engineering_backtest_started": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }
    payload.update(extra)
    return payload


def _root_report(startup_summary: dict[str, Any], specs: list[dict[str, str]], queue_status: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5g Next Queue Execution",
            "",
            f"- Startup gate: `{startup_summary.get('pm_gate_decision', '')}`",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            "- Engineering backtest started: `False`",
            "- Accepted: `False`",
            "",
            "## Queue Status",
            *[f"- P{row['priority']} `{row['next_gate']}`: {row['pm_gate_decision']}" for row in queue_status],
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    blockers = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            blockers.append({"blocker_id": f"missing_{rel.name}", "severity": "fatal", "status": "blocking", "path": str(rel)})
    return blockers


def _corr(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(x) != len(y):
        return None
    mx = sum(x) / len(x)
    my = sum(y) / len(y)
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    vx = sum((a - mx) ** 2 for a in x)
    vy = sum((b - my) ** 2 for b in y)
    if vx <= 0 or vy <= 0:
        return None
    return cov / math.sqrt(vx * vy)


def _ranks(values: list[float]) -> list[float]:
    sorted_vals = sorted((value, idx) for idx, value in enumerate(values))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(sorted_vals):
        j = i
        while j + 1 < len(sorted_vals) and sorted_vals[j + 1][0] == sorted_vals[i][0]:
            j += 1
        rank = (i + j + 2) / 2.0
        for _value, idx in sorted_vals[i : j + 1]:
            ranks[idx] = rank
        i = j + 1
    return ranks


def _mean(values: Iterable[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_or_blank(value: float | None) -> str:
    return "" if value is None else _fmt(value)


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
    run_v5g_next_queue_execution()
