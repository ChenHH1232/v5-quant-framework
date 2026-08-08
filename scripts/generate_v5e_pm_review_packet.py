from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\hh\codex\v5")
OUT = ROOT / "v5e_holding_period_exit_pm_review" / "current"


def read_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(name: str, data: dict) -> None:
    with (OUT / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_csv(name: str, rows: list[dict], fieldnames: list[str]) -> None:
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pct(x: float | None) -> str:
    if x is None:
        return ""
    return f"{x * 100:.2f}%"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    startup = read_json("v5_startup_warmup_price_repair/current/v5_startup_warmup_price_repair_summary.json")
    governance = read_json("enhanced_etf_governance_v5/current/enhanced_etf_governance_summary.json")
    v5c = read_json("v5c_closeout/current/v5c_closeout_summary.json")
    v5d = read_json("v5d_closeout/current/v5d_closeout_summary.json")
    l4_cost = read_json("v5d_l4_rebalance_neighborhood_order_completion/current/v5d_l4_cost_closeout_summary.json")
    knowledge = read_json("knowledge/research_agent/v5c_defense_profit_taking/v5c_knowledge_base_summary.json")

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pre_post = startup["pre_post"]

    startup_passed = (
        startup.get("status") == "startup_warmup_price_repair_completed"
        and startup.get("blocker_count") == 0
        and not startup.get("v57f_core_logic_modified")
        and pre_post.get("repaired_first_signal_date") == "2021-05-06"
    )

    branch_rows = [
        {
            "branch": "V57f",
            "scope": "core stock selection, target weights, quarterly rebalance schedule",
            "v5e_relationship": "baseline only; must not be modified",
            "allowed_in_v5e": "read repaired startup schedule and holdings/trades",
            "blocked_in_v5e": "change sleeves, factors, weights, caps, target_count or rebalance frequency",
            "status": "frozen_formal_etf_candidate_not_accepted",
        },
        {
            "branch": "V5c",
            "scope": "portfolio risk budget and defensive overlays",
            "v5e_relationship": "separate overlay family; ERC remains candidate only",
            "allowed_in_v5e": "use governance lessons and data-gate language",
            "blocked_in_v5e": "treat profit lock as ERC replacement or accepted overlay",
            "status": v5c.get("erc_status", {}).get("status", "v5c_overlay_candidate_not_accepted"),
        },
        {
            "branch": "V5d",
            "scope": "rebalance-day and D0/D1/D2 execution policy",
            "v5e_relationship": "execution layer after V5e exit signal exists",
            "allowed_in_v5e": "reuse T+1 and order-health governance concepts",
            "blocked_in_v5e": "turn holding-period exit into minute timing or intraday T",
            "status": v5d.get("final_candidate_status", {}).get("l4_exception_governed_completion", "execution_candidate_not_accepted"),
        },
        {
            "branch": "V5e",
            "scope": "holding-period exit, profit lock, de-risking between official V57f rebalances",
            "v5e_relationship": "current PM boundary review",
            "allowed_in_v5e": "define fixed PIT-safe exit rules and next quant spec queue",
            "blocked_in_v5e": "run backtests, scan thresholds, mark accepted, or replace V57f",
            "status": "pm_review_boundary_defined_not_engineered",
        },
        {
            "branch": "V5b",
            "scope": "non-core sector sidecar and data-gate research",
            "v5e_relationship": "excluded from V5e mainline",
            "allowed_in_v5e": "record future data-gate relevance only",
            "blocked_in_v5e": "promote sidecar or add sectors to V57f core",
            "status": "sidecar_data_gate_not_merged",
        },
    ]

    rule_rows = [
        {
            "rule_id": "single_name_profit_lock_daily_confirmed",
            "direction": "single_stock_holding_period_profit_lock",
            "rule_spec": "If a current holding reaches a pre-registered coarse profit zone versus its rebalance reference price, allow partial exit only after daily confirmation.",
            "trigger_data": "previously visible daily close and rebalance reference price",
            "execution_data": "daily execution proxy first; 5min only for execution governance if separately available",
            "post_trade_state": "reduced position; proceeds held as cash until next official V57f rebalance",
            "reentry_policy": "no reentry until next V57f rebalance",
            "pm_decision": "admit_to_v5e_quant_spec",
            "rationale": "simple PIT-safe profit-lock candidate; does not change stock selection or target weights",
        },
        {
            "rule_id": "single_name_trailing_profit_protection",
            "direction": "single_stock_trailing_profit_lock",
            "rule_spec": "After a holding has a visible unrealized profit, a coarse drawdown from the already observed stage high can trigger partial exit.",
            "trigger_data": "previous trading day close series; no same-day high/low look-ahead",
            "execution_data": "daily execution proxy first; 5min only for fixed execution slicing",
            "post_trade_state": "partial exit; cash held until next official V57f rebalance",
            "reentry_policy": "no reentry until next V57f rebalance",
            "pm_decision": "admit_to_v5e_quant_spec",
            "rationale": "captures profit protection without intraday prediction if state is based on prior closes",
        },
        {
            "rule_id": "no_reentry_until_next_rebalance",
            "direction": "governance_rule",
            "rule_spec": "Any stock or sleeve exited by V5e cannot be bought back before the next official V57f rebalance.",
            "trigger_data": "V5e exit log and official V57f rebalance calendar",
            "execution_data": "order health log",
            "post_trade_state": "cash remains idle in portfolio cash bucket",
            "reentry_policy": "hard no reentry before next official rebalance",
            "pm_decision": "admit_to_v5e_quant_spec",
            "rationale": "prevents V5e from becoming intraday T or repeated timing",
        },
        {
            "rule_id": "sleeve_level_profit_lock",
            "direction": "sleeve_holding_period_profit_lock",
            "rule_spec": "If a sleeve NAV rises into a pre-registered coarse profit zone during a rebalance cycle, allow sleeve-level exposure reduction.",
            "trigger_data": "PIT sleeve NAV from existing holdings and prices",
            "execution_data": "daily orders; 5min only as execution governance",
            "post_trade_state": "cash held at portfolio level; no automatic redistribution to other sleeves",
            "reentry_policy": "no sleeve re-risk before next official V57f rebalance unless later PM approves",
            "pm_decision": "diagnostic_only",
            "rationale": "potentially useful but can conflict with V57f sleeve neutrality and V5c risk-budget overlays",
        },
        {
            "rule_id": "portfolio_profit_lock",
            "direction": "portfolio_holding_period_de_risking",
            "rule_spec": "If total portfolio NAV reaches a pre-registered coarse profit zone after rebalance, allow portfolio-level exposure reduction.",
            "trigger_data": "PIT portfolio NAV and cash ledger",
            "execution_data": "daily orders; V5d execution candidates may be used later after data gate",
            "post_trade_state": "portfolio cash increases; no rotation into unapproved names",
            "reentry_policy": "no re-risk before next official V57f rebalance unless explicitly approved",
            "pm_decision": "diagnostic_only",
            "rationale": "may duplicate V5c defensive intent and requires clean priority ordering",
        },
        {
            "rule_id": "failed_breakout_reversal_exit",
            "direction": "technical_reversal_exit",
            "rule_spec": "Potential reversal/failure pattern after profit, not allowed into engineering without stronger PIT-safe evidence.",
            "trigger_data": "daily OHLC only if later approved",
            "execution_data": "not applicable in current PM packet",
            "post_trade_state": "undefined until future spec",
            "reentry_policy": "must obey no reentry if ever admitted",
            "pm_decision": "diagnostic_only",
            "rationale": "too close to technical timing; keep as research note only",
        },
        {
            "rule_id": "event_risk_exit",
            "direction": "event_risk_exit",
            "rule_spec": "Exit or reduce exposure after PIT-visible event risk such as dividend, financial-report, policy or corporate action deterioration.",
            "trigger_data": "PIT event announcement dates and visible timestamps",
            "execution_data": "not available in current packet",
            "post_trade_state": "cash until next rebalance if later approved",
            "reentry_policy": "must be defined after data gate",
            "pm_decision": "admit_to_data_gate_only",
            "rationale": "requires event visibility chain; no current engineering backtest allowed",
        },
    ]

    allowed_blocked = [
        {"action": "define_v5e_boundary", "classification": "allowed", "reason": "PM review only"},
        {"action": "read_repaired_startup_schedule", "classification": "allowed", "reason": "V5e must use repaired 2021-05-06 startup schedule"},
        {"action": "draft_quant_spec_queue", "classification": "allowed", "reason": "next stage planning only"},
        {"action": "single_name_daily_profit_lock_spec", "classification": "allowed", "reason": "fixed coarse PIT-safe candidate"},
        {"action": "single_name_trailing_profit_protection_spec", "classification": "allowed", "reason": "uses prior daily closes only in later spec"},
        {"action": "no_reentry_governance", "classification": "allowed", "reason": "prevents T and repeated timing"},
        {"action": "modify_v57f_core", "classification": "blocked", "reason": "V57f frozen mainline"},
        {"action": "engineering_backtest", "classification": "blocked", "reason": "current task is PM review only"},
        {"action": "scan_profit_thresholds", "classification": "blocked", "reason": "historical return selection forbidden"},
        {"action": "intraday_T", "classification": "blocked", "reason": "T+1 and governance prohibition"},
        {"action": "same_day_sell_then_buyback", "classification": "blocked", "reason": "would convert exit overlay into T/timing"},
        {"action": "use_future_bar_or_next_rebalance_info", "classification": "blocked", "reason": "future function"},
        {"action": "auto_reallocate_cash_to_other_stocks", "classification": "blocked", "reason": "would alter V57f target exposure without PM approval"},
        {"action": "start_joinquant_or_network_fetch", "classification": "blocked", "reason": "not needed for PM review"},
        {"action": "mark_v5e_accepted_or_v57f_replacement", "classification": "blocked", "reason": "not an acceptance gate"},
    ]

    data_rows = [
        {"data_item": "repaired_v57f_daily_holdings", "minimum_for_quant_spec": "required", "pit_requirement": "holding known after official rebalance execution", "current_status": "expected_from_repaired_shadow_backtest", "notes": "Needed to know which names are eligible for V5e exits."},
        {"data_item": "repaired_v57f_trades", "minimum_for_quant_spec": "required", "pit_requirement": "trade date and fill proxy must be visible in ledger", "current_status": "available_from_repaired_v57f_metrics_context", "notes": "Needed for cost basis/reference price."},
        {"data_item": "daily_ohlc_for_holdings", "minimum_for_quant_spec": "required", "pit_requirement": "V5e trigger may only use prior close or fully visible daily bar after market close", "current_status": "available_from_repaired_price_files", "notes": "Daily trigger first; 5min is not trigger source."},
        {"data_item": "rebalance_reference_price_or_cost_basis", "minimum_for_quant_spec": "required", "pit_requirement": "must be derived from executed order or rebalance-day allowed price proxy", "current_status": "needs_quant_spec_contract", "notes": "Do not use future average cost."},
        {"data_item": "cash_ledger", "minimum_for_quant_spec": "required", "pit_requirement": "cash changes only after executed sells/dividends", "current_status": "needs_quant_spec_contract", "notes": "V5e sale proceeds remain cash until next rebalance."},
        {"data_item": "dividends_and_corporate_actions", "minimum_for_quant_spec": "required_for_correct_nav", "pit_requirement": "use announcement/record/ex-date visibility", "current_status": "partially available in V57f; advanced event exits data gate only", "notes": "No event-risk backtest without visibility chain."},
        {"data_item": "official_v57f_rebalance_calendar", "minimum_for_quant_spec": "required", "pit_requirement": "calendar must be pre-defined", "current_status": "available", "notes": "Defines no-reentry end point."},
        {"data_item": "5min_execution_bars", "minimum_for_quant_spec": "optional_for_execution_only", "pit_requirement": "trigger-day bars cannot be used for trigger prediction", "current_status": "initial 2021-05-06 D0/D1/D2 missing for V5d; not blocker for PM review", "notes": "Needed only if later testing execution slicing."},
        {"data_item": "event_risk_announcements", "minimum_for_quant_spec": "advanced_data_gate", "pit_requirement": "announcement timestamp/date must be explicit", "current_status": "not admitted for engineering", "notes": "Data-gate only."},
        {"data_item": "FCF_OCF_quality", "minimum_for_quant_spec": "advanced_data_gate", "pit_requirement": "financial report announce-date lag", "current_status": "not admitted for engineering", "notes": "Data-gate only."},
        {"data_item": "valuation_crowding", "minimum_for_quant_spec": "advanced_data_gate", "pit_requirement": "PIT valuation/fund-flow/holding crowding contract", "current_status": "not admitted for engineering", "notes": "Data-gate only."},
    ]

    pit_rows = [
        {"signal_family": "profit_lock_daily_confirmed", "allowed_visible_information": "prior close, executed cost/reference price, current holding quantity, official rebalance calendar", "forbidden_information": "same-day final close before close, future bars, next rebalance constituents", "decision_time": "after daily confirmation; execution next allowed window"},
        {"signal_family": "trailing_profit_protection", "allowed_visible_information": "prior closes and prior observed peak computed as of decision time", "forbidden_information": "same-day intraday high/low used retroactively, full-cycle high known after the fact", "decision_time": "after prior-day close or next legal execution day"},
        {"signal_family": "sleeve_profit_lock", "allowed_visible_information": "sleeve NAV from current holdings and visible daily prices", "forbidden_information": "future sleeve returns or reallocating based on later winner/loser status", "decision_time": "after daily sleeve NAV confirmation"},
        {"signal_family": "portfolio_profit_lock", "allowed_visible_information": "portfolio NAV and cash ledger visible at decision time", "forbidden_information": "future drawdown/rebound knowledge", "decision_time": "after daily NAV confirmation"},
        {"signal_family": "event_risk_exit", "allowed_visible_information": "public announcement or event date chain after release", "forbidden_information": "unannounced financial/dividend facts", "decision_time": "blocked until data gate proves visibility"},
    ]

    cash_rows = [
        {"policy_id": "cash_after_exit", "rule": "V5e exits move proceeds to portfolio cash.", "allowed": "hold cash until next official V57f rebalance", "blocked": "automatic reinvestment into other stocks or sleeves"},
        {"policy_id": "no_same_cycle_reentry", "rule": "Exited stock or sleeve cannot be re-entered before next official V57f rebalance.", "allowed": "re-enter only if next V57f rebalance selects/targets it again", "blocked": "buyback because price falls or momentum improves"},
        {"policy_id": "next_rebalance_reset", "rule": "Next official V57f rebalance resets target positions and clears V5e no-reentry flags for new official targets.", "allowed": "follow V57f repaired schedule", "blocked": "carry old V5e cash decision past next official rebalance without spec"},
        {"policy_id": "cash_drag_visibility", "rule": "Any cash created by V5e must be measured explicitly.", "allowed": "report cash drag and reduced exposure", "blocked": "hide cash drag or compare as if fully invested"},
    ]

    t_rows = [
        {"rule_id": "no_intraday_T", "requirement": "V5e cannot buy and sell the same stock on the same day for timing.", "audit_field": "same_day_buy_sell_stock_count", "required_value": "0"},
        {"rule_id": "sell_then_no_buyback", "requirement": "If V5e sells a stock, same-day buyback is forbidden.", "audit_field": "same_day_sell_then_buyback_count", "required_value": "0"},
        {"rule_id": "buy_then_no_exit_same_day", "requirement": "A new official V57f buy cannot be exited by V5e on the same day.", "audit_field": "same_day_buy_then_exit_count", "required_value": "0"},
        {"rule_id": "existing_vs_new_lot_tagging", "requirement": "Future engineering must distinguish existing holdings, newly bought lots and V5e-exited lots.", "audit_field": "lot_state_available", "required_value": "true"},
        {"rule_id": "no_reentry_until_rebalance", "requirement": "Exited positions can only become eligible again at the next official V57f rebalance.", "audit_field": "pre_rebalance_reentry_count", "required_value": "0"},
    ]

    admission_rows = [
        {"candidate": "single_name_profit_lock_daily_confirmed", "pm_decision": "admit_to_v5e_quant_spec", "reason": "PIT-safe daily rule candidate; clear cash and no-reentry treatment", "next_required": "write fixed-rule quant spec; no threshold scan"},
        {"candidate": "single_name_trailing_profit_protection", "pm_decision": "admit_to_v5e_quant_spec", "reason": "can be defined from prior closes and observed profit state", "next_required": "define fixed coarse trigger using prior close only"},
        {"candidate": "no_reentry_until_next_rebalance", "pm_decision": "admit_to_v5e_quant_spec", "reason": "hard governance control required for all exit rules", "next_required": "include in every V5e engineering audit"},
        {"candidate": "sleeve_level_profit_lock", "pm_decision": "diagnostic_only", "reason": "may conflict with sleeve neutrality and V5c risk budget; useful but needs priority ordering", "next_required": "separate PM priority spec before engineering"},
        {"candidate": "portfolio_profit_lock", "pm_decision": "diagnostic_only", "reason": "may duplicate V5c defense and cash exposure rules", "next_required": "define hierarchy versus ERC before engineering"},
        {"candidate": "failed_breakout_reversal_exit", "pm_decision": "diagnostic_only", "reason": "too close to technical timing", "next_required": "stronger evidence and PIT guardrails before admission"},
        {"candidate": "event_risk_exit", "pm_decision": "admit_to_data_gate_only", "reason": "requires PIT event announcement chain", "next_required": "build event visibility data gate only"},
        {"candidate": "dividend_safety_exit", "pm_decision": "admit_to_data_gate_only", "reason": "requires proposal/approval/implementation/record/ex-date chain", "next_required": "data contract before any test"},
        {"candidate": "FCF_OCF_quality_exit", "pm_decision": "admit_to_data_gate_only", "reason": "requires financial statement announcement lag", "next_required": "PIT financial data gate"},
        {"candidate": "valuation_crowding_exit", "pm_decision": "admit_to_data_gate_only", "reason": "requires PIT valuation, flows and crowding data", "next_required": "data contract only"},
        {"candidate": "5min_prediction_timing", "pm_decision": "reject_or_archive", "reason": "not V5e; violates no minute prediction boundary", "next_required": "none"},
        {"candidate": "intraday_T_or_repeated_buyback", "pm_decision": "reject_or_archive", "reason": "violates T+1/no-reentry governance", "next_required": "none"},
        {"candidate": "threshold_parameter_scan", "pm_decision": "reject_or_archive", "reason": "historical return selection forbidden", "next_required": "none"},
    ]

    next_queue = [
        {"priority": 1, "task_name": "V5e fixed-rule quant spec for single-name daily profit lock and trailing protection", "scope": "spec only; pre-register coarse rules; no backtest yet", "inputs": "repaired V57f schedule, holdings, trades, daily OHLC, cash ledger contract", "blocked_actions": "threshold scan; V57f modification; accepted decision"},
        {"priority": 2, "task_name": "V5e cash/no-reentry ledger design", "scope": "define position states, exit flags, cash drag reporting and next-rebalance reset", "inputs": "V57f trades and official rebalance calendar", "blocked_actions": "auto reallocation; same-cycle buyback"},
        {"priority": 3, "task_name": "V5e data gate for event/dividend/FCF/valuation exits", "scope": "data availability and PIT visibility only", "inputs": "announcement dates, financial statement visibility, dividend event chain", "blocked_actions": "engineering backtest without PIT data"},
        {"priority": 4, "task_name": "Optional V5d initial 5min data completion", "scope": "execution-layer repair only if user reopens V5d", "inputs": "2021-05-06 D0/D1/D2 BaoStock 5min bars", "blocked_actions": "fake minute bars"},
    ]

    blocker_rows = [
        {
            "blocker_id": "none_for_pm_review",
            "severity": "none",
            "status": "not_blocking",
            "description": "Startup repair passed and all required PM review inputs were found.",
            "impact": "V5e PM boundary review can proceed.",
            "next_action": "Proceed to V5e quant spec only after PM accepts admitted rules.",
        },
        {
            "blocker_id": "v5d_initial_5min_data_gap",
            "severity": "known_external_to_v5e_pm_review",
            "status": "not_blocking_pm_review",
            "description": "2021-05-06 D0/D1/D2 BaoStock 5min data is still missing for V5d repaired execution reruns.",
            "impact": "Blocks full V5d repaired execution chain, but does not block V5e PM review because V5e trigger spec starts daily.",
            "next_action": "Only refill minute data if V5d execution rerun is explicitly reopened.",
        },
    ]

    summary = {
        "schema_version": 1,
        "project": "v5e_holding_period_exit_pm_review",
        "status": "completed_pm_review_boundary_defined_no_backtest",
        "created_at_utc": created_at,
        "working_directory": str(ROOT),
        "startup_repair_status": startup.get("status"),
        "startup_repair_passed_for_v5e_pm_review": startup_passed,
        "deployment_model": startup.get("deployment_model", {}),
        "pre_post_startup": pre_post,
        "original_v57f_config_modified": startup.get("original_v57f_config_modified"),
        "v57f_core_logic_modified": startup.get("v57f_core_logic_modified"),
        "v57f_status": "frozen_formal_etf_candidate_not_accepted_not_live",
        "erc_status": v5c.get("erc_status", {}).get("status", "v5c_overlay_candidate_not_accepted"),
        "v5d_status": v5d.get("final_candidate_status", {}),
        "v5d_initial_minute_data_status": startup.get("v5d_initial_minute_data_status"),
        "current_task_actions": {
            "engineering_backtest_started": False,
            "joinquant_started": False,
            "network_fetch_started": False,
            "v57f_modified": False,
            "erc_modified": False,
            "v5d_modified": False,
            "accepted_marked": False,
        },
        "v5e_definition": "Holding-period exit / profit-lock overlay between official V57f rebalances, based on repaired startup schedule and fixed PIT-safe rules.",
        "admitted_to_quant_spec": [
            "single_name_profit_lock_daily_confirmed",
            "single_name_trailing_profit_protection",
            "no_reentry_until_next_rebalance",
        ],
        "diagnostic_only": [
            "sleeve_level_profit_lock",
            "portfolio_profit_lock",
            "failed_breakout_reversal_exit",
        ],
        "data_gate_only": [
            "event_risk_exit",
            "dividend_safety_exit",
            "FCF_OCF_quality_exit",
            "valuation_crowding_exit",
        ],
        "rejected_or_archived": [
            "5min_prediction_timing",
            "intraday_T_or_repeated_buyback",
            "threshold_parameter_scan",
        ],
        "blocker_count": 0,
        "known_nonblocking_gap": "V5d initial 2021-05-06 D0/D1/D2 5min data missing; not blocking V5e PM review.",
        "next_gate": "v5e_quant_spec_for_single_name_daily_profit_lock_and_trailing_protection",
        "source_context": {
            "v57f_governance_status": governance.get("status"),
            "v5c_closeout_status": v5c.get("status"),
            "v5d_closeout_status": v5d.get("status"),
            "l4_cost_closeout_status": l4_cost.get("status"),
            "knowledge_base_status": knowledge.get("status"),
            "knowledge_ab_card_count": knowledge.get("fxbaogao_pdf_review_status", {}).get("ab_evidence_card_count"),
        },
        "outputs": {
            "summary": "v5e_holding_period_exit_pm_review/current/v5e_pm_review_summary.json",
            "report": "v5e_holding_period_exit_pm_review/current/v5e_pm_review_report.md",
            "branch_boundary_matrix": "v5e_holding_period_exit_pm_review/current/v5e_branch_boundary_matrix.csv",
            "candidate_rule_matrix": "v5e_holding_period_exit_pm_review/current/v5e_candidate_rule_matrix.csv",
            "allowed_blocked_actions": "v5e_holding_period_exit_pm_review/current/v5e_allowed_blocked_actions.csv",
            "data_requirement_matrix": "v5e_holding_period_exit_pm_review/current/v5e_data_requirement_matrix.csv",
            "pit_visibility_requirement": "v5e_holding_period_exit_pm_review/current/v5e_pit_visibility_requirement.csv",
            "cash_and_reentry_policy": "v5e_holding_period_exit_pm_review/current/v5e_cash_and_reentry_policy.csv",
            "t_plus_one_governance": "v5e_holding_period_exit_pm_review/current/v5e_t_plus_one_governance.csv",
            "pm_admission_decision": "v5e_holding_period_exit_pm_review/current/v5e_pm_admission_decision.csv",
            "next_quant_spec_queue": "v5e_holding_period_exit_pm_review/current/v5e_next_quant_spec_queue.csv",
            "blockers": "v5e_holding_period_exit_pm_review/current/v5e_blockers.csv",
            "agent_execution_rules": "v5e_holding_period_exit_pm_review/current/v5e_agent_execution_rules.md",
        },
    }

    report = f"""# V5e holding-period exit / profit-lock overlay 前置 PM review

## 总结论

本次 V5e 前置 PM review 已完成。V5e 被定义为：在两次 V57f 正式调仓之间，对已经持有的股票或 sleeve 做持仓期退出、止盈、减仓或风险释放的 overlay。

本任务没有做工程回测，没有调参，没有启动 JoinQuant，没有联网拉数据，也没有修改 V57f / ERC / V5d。V5e 不是 accepted strategy，也不是 V57f replacement。

startup preload 主修复已作为 V5e 的前置基础：旧 first_signal / first_trade 为 `{pre_post["old_first_signal_date"]}`，修复后 first_signal / first_trade 为 `{pre_post["repaired_first_signal_date"]}`，startup_gap 从 `{pre_post["startup_gap_days_old"]}` 天降到 `{pre_post["startup_gap_days_repaired"]}` 天。V5e 后续必须基于 repaired startup schedule / shadow config，而不是旧冷启动链路。

## 分支边界

- V57f：负责选股、权重、季度调仓；V5e 不得修改。
- V5c：负责组合风险预算 / 防守 overlay；ERC 仍是 candidate not accepted。
- V5d：负责调仓日及 D0/D1/D2 执行优化；L2/L3/L4 仍是 execution candidates not accepted。
- V5e：负责调仓周期内持仓期退出 / profit lock。
- V5b：非核心行业 sidecar / data gate，不并入 V5e。

## 允许进入 Quant spec 的方向

1. `single_name_profit_lock_daily_confirmed`
   - 单股从本轮建仓参考价达到预注册粗粒度利润区间后，仅在日线确认后允许减仓。
   - 5 分钟只用于执行治理，不用于触发。
   - 卖出后现金留到下一次 V57f 正式调仓。

2. `single_name_trailing_profit_protection`
   - 单股已经有浮盈后，若从已经可见的阶段高点回撤到预注册粗粒度区间，允许部分退出。
   - 必须使用前一交易日已经可见的收盘价确认。
   - 不允许使用当天全天高低点倒推。

3. `no_reentry_until_next_rebalance`
   - 任何 V5e 退出后的股票或 sleeve，在下一次 V57f 正式调仓前不得重新买入。
   - 这是治理规则，不是收益规则。

## 仅 diagnostic 的方向

- `sleeve_level_profit_lock`：可能与 V57f sleeve neutrality、V5c ERC 风险预算冲突，先 diagnostic。
- `portfolio_profit_lock`：可能与 V5c 防守 overlay 重叠，必须先定义优先级。
- `failed_breakout_reversal_exit`：过于接近技术择时，不能直接工程。

## 仅 data gate 的方向

- `event_risk_exit`
- `dividend_safety_exit`
- `FCF_OCF_quality_exit`
- `valuation_crowding_exit`

这些方向需要 PIT 公告日期、财报公告滞后、分红事件链、估值/资金流/拥挤数据。当前不得工程回测。

## 硬禁止

- 不得修改 V57f 选股逻辑、core sleeve、因子、权重、target_count、sector cap、single stock cap 或调仓频率。
- 不得按历史收益扫描止盈阈值。
- 不得日内 T。
- 不得当日卖出后同日买回同一股票。
- 不得当日买入后同日卖出同一股票。
- 不得使用未来 bar 或下个调仓日信息。
- 不得把卖出资金自动重配到其他股票。
- 不得启动 JoinQuant 或联网拉数据。
- 不得把 V5e 标记 accepted 或 V57f replacement。

## 数据门

V5e Quant spec 的最低可行数据包括 repaired V57f daily holdings、trades、daily OHLC、调仓参考价或成本基准、现金状态、corporate actions / dividends、T+1 状态和下次 V57f 调仓日 schedule。

如果后续使用 5 分钟数据，只能作为执行价格和成交治理，不作为止盈触发预测。当前 V5d 仍缺 `2021-05-06` D0/D1/D2 初始建仓 5 分钟数据；这不阻塞 V5e PM review，但阻塞 V5d repaired execution 全链路声称。

## PM admission decision

本次 PM review 的下一门是：`v5e_quant_spec_for_single_name_daily_profit_lock_and_trailing_protection`。

第一优先级应写一版固定规则 Quant spec，覆盖：

1. 单股日线确认 profit-lock；
2. 单股 trailing profit protection；
3. no reentry until next rebalance；
4. 现金留存和 cash drag 记录；
5. T+1 / no intraday T 审计；
6. 不扫阈值、不做收益择优。

## Blocker

本次 V5e PM review 无阻塞。

已知非阻塞缺口：V5d 初始 `2021-05-06` D0/D1/D2 5 分钟数据缺失。它不阻塞 V5e PM review，但若未来要把 V5e exit 交给 V5d 分钟执行层复核，需要先补该分钟数据门。
"""

    rules_md = """# V5e Agent Execution Rules

1. This packet is PM review / boundary definition only.
2. Do not run engineering backtests from this packet.
3. Do not modify V57f, ERC, V5c, or V5d source/config.
4. Use repaired startup schedule / shadow config as the baseline for future V5e work.
5. V5e may only study holding-period exit/profit-lock between official V57f rebalances.
6. V5e must not change stock selection, target weights, sleeves, caps, or quarterly rebalance frequency.
7. No intraday T, no same-day buyback, no repeated reentry before next official rebalance.
8. No threshold scan or historical-return selection.
9. 5min data can support execution governance only; it cannot trigger predictive exits.
10. Event/dividend/FCF/valuation/crowding exits remain data-gate only until PIT visibility is proven.
11. Do not mark V5e accepted, live-approved, or V57f replacement.
12. If future work needs JoinQuant/network/API data, stop and request explicit authorization.
"""

    write_json("v5e_pm_review_summary.json", summary)
    (OUT / "v5e_pm_review_report.md").write_text(report, encoding="utf-8")
    write_csv("v5e_branch_boundary_matrix.csv", branch_rows, ["branch", "scope", "v5e_relationship", "allowed_in_v5e", "blocked_in_v5e", "status"])
    write_csv("v5e_candidate_rule_matrix.csv", rule_rows, ["rule_id", "direction", "rule_spec", "trigger_data", "execution_data", "post_trade_state", "reentry_policy", "pm_decision", "rationale"])
    write_csv("v5e_allowed_blocked_actions.csv", allowed_blocked, ["action", "classification", "reason"])
    write_csv("v5e_data_requirement_matrix.csv", data_rows, ["data_item", "minimum_for_quant_spec", "pit_requirement", "current_status", "notes"])
    write_csv("v5e_pit_visibility_requirement.csv", pit_rows, ["signal_family", "allowed_visible_information", "forbidden_information", "decision_time"])
    write_csv("v5e_cash_and_reentry_policy.csv", cash_rows, ["policy_id", "rule", "allowed", "blocked"])
    write_csv("v5e_t_plus_one_governance.csv", t_rows, ["rule_id", "requirement", "audit_field", "required_value"])
    write_csv("v5e_pm_admission_decision.csv", admission_rows, ["candidate", "pm_decision", "reason", "next_required"])
    write_csv("v5e_next_quant_spec_queue.csv", next_queue, ["priority", "task_name", "scope", "inputs", "blocked_actions"])
    write_csv("v5e_blockers.csv", blocker_rows, ["blocker_id", "severity", "status", "description", "impact", "next_action"])
    (OUT / "v5e_agent_execution_rules.md").write_text(rules_md, encoding="utf-8")

    print(f"generated {len(summary['outputs'])} files in {OUT}")
    print(summary["next_gate"])


if __name__ == "__main__":
    main()
