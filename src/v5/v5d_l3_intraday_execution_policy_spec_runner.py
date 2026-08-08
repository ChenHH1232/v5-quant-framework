from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5d_l3_intraday_execution_policy_spec") / "current"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"

REQUIRED_INPUTS = [
    Path("v5d_baostock_5min_data_gate") / "current" / "v5d_baostock_5min_data_gate_summary.json",
    Path("v5d_baostock_5min_data_gate") / "current" / "v5d_minute_execution_proxy_readiness.csv",
    Path("v5d_minute_execution_robustness") / "current" / "v5d_minute_execution_robustness_summary.json",
    Path("v5d_minute_execution_robustness") / "current" / "v5d_execution_proxy_comparison.csv",
    Path("v5d_order_scheduling_engineering_test") / "current" / "v5d_l2_engineering_summary.json",
    Path("v5d_l2_order_scheduling_pm_quant_review") / "current" / "v5d_l2_pm_quant_review_summary.json",
    Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "trades.csv",
    Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "rebalance_order_health.csv",
    Path("v5c_erc_formal_validation") / "current" / "v5c_erc_formal_validation_summary.json",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_boundary_matrix() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "open_volatility_delay",
            "governance_status": "allowed_for_engineering_spec",
            "target_order_scope": "buy_orders_only_primary; sell_orders_limited_delay_only",
            "allowed_information": "previous_close; opening_price; completed_09:35_bar; completed_09:40_bar_before_10:00_decision",
            "blocked_information": "full_day_high_low; close_to_close_return_known_after_day; future_5min_bars; final_intraday_path",
            "pit_safety": "safe_if_decision_timestamp_logged",
            "allowed_effect": "delay buy slice to next pre-registered L2 window when opening bars are abnormally wide",
            "blocked_effect": "cancel target order due to price forecast; delay sells indefinitely; choose window by historical return",
            "engineering_gate": "allowed",
            "notes": "Uses only already completed bars; intended to reduce fragile open fills, not predict intraday direction.",
        },
        {
            "rule_id": "price_band_limit_order",
            "governance_status": "allowed_for_engineering_spec",
            "target_order_scope": "buy_and_sell_orders",
            "allowed_information": "previous_close; opening_price; latest_completed_5min_bar; current_limit_up_down_status_if_available",
            "blocked_information": "optimized historical bands; full-day high/low; future rebound or breakdown",
            "pit_safety": "safe_if_band_fixed_and_timestamped",
            "allowed_effect": "submit conservative limit bands and log unfilled if not reached",
            "blocked_effect": "trend chasing; using price band as alpha signal; parameter scan",
            "engineering_gate": "allowed",
            "notes": "Band must be coarse and pre-registered; not a new timing signal.",
        },
        {
            "rule_id": "twap_default_with_exception",
            "governance_status": "allowed_for_engineering_spec",
            "target_order_scope": "all_l2_size_aware_orders",
            "allowed_information": "L2 schedule; completed bars at decision time; pause/limit/missing-bar state",
            "blocked_information": "future bars; realized best bar; return-ranked window choice",
            "pit_safety": "safe",
            "allowed_effect": "default L2 TWAP/size-aware schedule, altered only for abnormal execution states",
            "blocked_effect": "selecting historically best minute proxy",
            "engineering_gate": "allowed_first_priority",
            "notes": "This is the cleanest L3 baseline because exceptions are execution-health driven.",
        },
        {
            "rule_id": "sell_first_cash_release",
            "governance_status": "allowed_for_engineering_spec",
            "target_order_scope": "sell_orders_then_buy_orders",
            "allowed_information": "target deltas; current holdings; available cash; completed sell fills",
            "blocked_information": "post-sell price path used to decide whether to buy",
            "pit_safety": "safe",
            "allowed_effect": "buy slices wait for realized sell cash or available cash budget",
            "blocked_effect": "timing sell/buy based on intraday prediction; long sell delay",
            "engineering_gate": "allowed",
            "notes": "Carries over L2 cash discipline and avoids cash-shortfall false fills.",
        },
        {
            "rule_id": "close_cleanup",
            "governance_status": "allowed_for_engineering_spec",
            "target_order_scope": "remaining_unfilled_orders",
            "allowed_information": "remaining target delta; completed fills; 14:30 and 14:55 available bars; limit/pause state",
            "blocked_information": "next-day outcome; forced synthetic fill",
            "pit_safety": "safe",
            "allowed_effect": "attempt final pre-registered cleanup then stop and log unfilled",
            "blocked_effect": "force fill; cross-day retry without separate gate",
            "engineering_gate": "allowed",
            "notes": "Maintains order-health audit trail.",
        },
        {
            "rule_id": "no_intraday_T_policy",
            "governance_status": "required_hard_gate",
            "target_order_scope": "all_orders",
            "allowed_information": "current holdings before rebalance; target deltas; same-day buy ledger",
            "blocked_information": "intraday alpha; bottom-position high-sell-low-buy signals",
            "pit_safety": "safe",
            "allowed_effect": "block any same-day buy-then-sell or sell-then-buy round-trip design",
            "blocked_effect": "T0-like execution; bottom-position trading; high-sell-low-buy",
            "engineering_gate": "required",
            "notes": "L3 handles target-order execution only, not trading around the position.",
        },
        {
            "rule_id": "unfilled_order_governance",
            "governance_status": "required_hard_gate",
            "target_order_scope": "all_unfilled_or_partially_filled_orders",
            "allowed_information": "order status; bar availability; pause/limit state; price-band status; close cleanup status",
            "blocked_information": "fabricated fill; hidden missing execution",
            "pit_safety": "safe",
            "allowed_effect": "classify and preserve all unfilled reasons",
            "blocked_effect": "hide unfilled; backfill execution price; silently carry order",
            "engineering_gate": "required",
            "notes": "Required for PM review of L3 order health.",
        },
        {
            "rule_id": "intraday_trend_following_or_pattern_recognition",
            "governance_status": "blocked",
            "target_order_scope": "not_allowed",
            "allowed_information": "",
            "blocked_information": "intraday trend labels; pattern signals; future path; full-day high/low",
            "pit_safety": "unsafe_or_needs_separate_research",
            "allowed_effect": "",
            "blocked_effect": "minute prediction; return-seeking timing model",
            "engineering_gate": "blocked",
            "notes": "Out of L3 execution-aware scope.",
        },
    ]


def build_candidate_specs() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "twap_default_with_exception",
            "priority": 1,
            "allowed_next_stage": "engineering_spec_then_local_paper_test",
            "rule_description": "Use L2 size-aware schedule as default; alter only for pause, limit, missing bar, price-band failure, or open-volatility exception.",
            "decision_times": "09:35;09:40;10:00;13:30;14:30;14:55",
            "inputs": "target orders; current positions; available cash; completed 5min bars; pause/limit/bar availability",
            "outputs": "order_submit_log; fill_proxy_log; exception_log; unfilled_log",
            "parameter_policy": "fixed coarse exception rules only; no scan",
            "pit_control": "each decision row records visible_bar_cutoff_time",
            "success_metric": "order health, fill coverage, cash-shortfall reduction, cost stability",
            "blocked_actions": "return-window selection; hidden unfilled; forecast timing",
        },
        {
            "rule_id": "open_volatility_delay",
            "priority": 2,
            "allowed_next_stage": "engineering_spec_then_local_paper_test",
            "rule_description": "If first one or two completed 5min bars are abnormally wide, delay buy slices to the next fixed window; sells remain sell-first with bounded delay.",
            "decision_times": "09:40 decision may use 09:35 bar; 10:00 decision may use completed bars up to 09:55",
            "inputs": "previous close; open; completed bar high/low/close; target side; remaining amount",
            "outputs": "delay_reason; original_window; new_window; visible_bar_cutoff_time",
            "parameter_policy": "coarse pre-registered volatility bucket; no historical return tuning",
            "pit_control": "no full-day high/low; no after-window bars",
            "success_metric": "reduced fragile open execution and logged exceptions",
            "blocked_actions": "using final intraday volatility; delaying sell orders indefinitely",
        },
        {
            "rule_id": "price_band_limit_order",
            "priority": 3,
            "allowed_next_stage": "engineering_spec_then_local_paper_test",
            "rule_description": "Use conservative limit bands around previous close/open/current completed bar to avoid extreme fills; untriggered orders retry only at pre-registered windows.",
            "decision_times": "each L2/L3 submit window",
            "inputs": "previous close; open; latest completed bar; side; limit-up/down status when available",
            "outputs": "limit_price; band_source; band_status; unfilled_reason_if_not_triggered",
            "parameter_policy": "coarse band levels defined before test; no scan",
            "pit_control": "band cannot reference future bars or end-of-day high/low",
            "success_metric": "extreme-fill avoidance and clear unfilled records",
            "blocked_actions": "chasing strength; avoiding buys because later price fell; parameter optimization",
        },
        {
            "rule_id": "sell_first_cash_release",
            "priority": 4,
            "allowed_next_stage": "engineering_spec_then_local_paper_test",
            "rule_description": "Process sell deltas first; buy deltas consume realized sell cash plus available cash only.",
            "decision_times": "all windows; sell queue before buy queue",
            "inputs": "target deltas; positions; cash; fill log",
            "outputs": "cash_release_log; buy_cash_budget_log; cash_shortfall_log",
            "parameter_policy": "fixed queue priority",
            "pit_control": "buy eligibility uses only realized cash at decision time",
            "success_metric": "lower cash shortfall and no false fills",
            "blocked_actions": "sell delay for timing; buy list changes after observing price path",
        },
        {
            "rule_id": "close_cleanup",
            "priority": 5,
            "allowed_next_stage": "engineering_spec_then_local_paper_test",
            "rule_description": "At final fixed windows attempt remaining orders if execution constraints allow; otherwise stop and log unfilled.",
            "decision_times": "14:30;14:55",
            "inputs": "remaining delta; latest completed bars; pause/limit/price-band state",
            "outputs": "cleanup_attempt_log; final_unfilled_log",
            "parameter_policy": "fixed final windows",
            "pit_control": "no next-day data and no synthetic fills",
            "success_metric": "complete audit trail for residual orders",
            "blocked_actions": "cross-day retry without gate; forced close print",
        },
        {
            "rule_id": "no_intraday_T_policy",
            "priority": 0,
            "allowed_next_stage": "hard_gate_for_all_engineering",
            "rule_description": "Disallow same-day trading around holdings; L3 only executes target deltas produced before the trading schedule.",
            "decision_times": "all windows",
            "inputs": "pre-rebalance holding ledger; target deltas; same-day buy ledger",
            "outputs": "tplus1_validation_log; blocked_order_if_any",
            "parameter_policy": "no parameters",
            "pit_control": "separate old holdings from same-day buys",
            "success_metric": "zero same-day buy/sell violations",
            "blocked_actions": "bottom-position T; high-sell-low-buy; sell newly bought shares",
        },
        {
            "rule_id": "unfilled_order_governance",
            "priority": 0,
            "allowed_next_stage": "hard_gate_for_all_engineering",
            "rule_description": "Classify each non-fill: paused, buy_limit_up, sell_limit_down, missing_bar, price_band_not_triggered, cash_shortfall, close_unfilled.",
            "decision_times": "all windows and end-of-day",
            "inputs": "order state; market state; cash state; bar state",
            "outputs": "unfilled_reason; severity; carry_policy; review_required flag",
            "parameter_policy": "fixed reason taxonomy",
            "pit_control": "no hidden fills or retroactive repairs",
            "success_metric": "complete order-health review table",
            "blocked_actions": "hide unfilled; fabricate fills; silently roll forward",
        },
    ]


def build_visibility_audit() -> list[dict[str, Any]]:
    return [
        {
            "decision_time": "pre_open",
            "visible_5min_bars": "none_current_day",
            "visible_daily_data": "previous close and prior disclosed data only",
            "allowed_decisions": "build target order list from already frozen V57f/ERC target signals",
            "blocked_decisions": "use opening price or same-day bar before available",
            "pit_status": "safe",
        },
        {
            "decision_time": "09:35_after_bar_complete",
            "visible_5min_bars": "09:35 bar only after completion",
            "visible_daily_data": "previous close; opening price once known",
            "allowed_decisions": "sell-first first slice; detect pause/limit/missing bar; compute first open volatility state",
            "blocked_decisions": "use 09:40 or later bars",
            "pit_status": "safe_if_timestamped",
        },
        {
            "decision_time": "09:40_after_bar_complete",
            "visible_5min_bars": "09:35 and 09:40 completed bars",
            "visible_daily_data": "previous close; opening price",
            "allowed_decisions": "delay buy to 10:00 if pre-registered open-volatility exception triggers",
            "blocked_decisions": "use 10:00+ bars or full-day range",
            "pit_status": "safe_if_timestamped",
        },
        {
            "decision_time": "10:00_after_bar_complete",
            "visible_5min_bars": "all completed bars through 10:00",
            "visible_daily_data": "previous close; opening price",
            "allowed_decisions": "continue default TWAP or retry failed buys based on actual non-fill reasons",
            "blocked_decisions": "select 10:00 because it was historically best",
            "pit_status": "safe_if_timestamped",
        },
        {
            "decision_time": "13:30_after_bar_complete",
            "visible_5min_bars": "morning completed bars and 13:30 after completion",
            "visible_daily_data": "previous close; opening price",
            "allowed_decisions": "continue scheduled buy/sell and price-band retry",
            "blocked_decisions": "infer afternoon trend from future bars",
            "pit_status": "safe_if_timestamped",
        },
        {
            "decision_time": "14:30_after_bar_complete",
            "visible_5min_bars": "completed bars through 14:30",
            "visible_daily_data": "previous close; opening price",
            "allowed_decisions": "prepare close cleanup for remaining orders",
            "blocked_decisions": "use 14:55 or close bar before available",
            "pit_status": "safe_if_timestamped",
        },
        {
            "decision_time": "14:55_after_bar_complete",
            "visible_5min_bars": "completed bars through 14:55",
            "visible_daily_data": "previous close; opening price",
            "allowed_decisions": "final cleanup attempt then log unfilled",
            "blocked_decisions": "force fill at close or cross-day retry without separate gate",
            "pit_status": "safe_if_timestamped",
        },
    ]


def build_allowed_blocked() -> list[dict[str, Any]]:
    return [
        {"action": "l3_default_twap_with_exception_engineering_spec", "status": "allowed", "reason": "execution-health exception handling around L2 size-aware policy"},
        {"action": "l3_open_volatility_delay_engineering_spec", "status": "allowed", "reason": "uses only completed early bars and fixed windows"},
        {"action": "l3_price_band_limit_order_engineering_spec", "status": "allowed", "reason": "coarse fixed bands can reduce extreme execution without changing target holdings"},
        {"action": "l3_sell_first_cash_release_engineering_spec", "status": "allowed", "reason": "cash discipline and reduced false fills"},
        {"action": "l3_close_cleanup_unfilled_logging", "status": "allowed", "reason": "required order-health governance"},
        {"action": "intraday_T", "status": "blocked", "reason": "outside V5d L3 and conflicts with T+1 / no-T governance"},
        {"action": "trend_chasing_or_pattern_recognition", "status": "blocked", "reason": "would become intraday prediction model"},
        {"action": "use_full_day_high_low", "status": "blocked", "reason": "future-function risk at intraday decision time"},
        {"action": "parameter_scan_or_return_selection", "status": "blocked", "reason": "L3 cannot be chosen by historical return"},
        {"action": "modify_v57f_or_erc_targets", "status": "blocked", "reason": "V57f frozen and ERC candidate only"},
        {"action": "require_1min_data_as_hard_precondition", "status": "blocked", "reason": "5min data is enough to define first L3 spec; 1min optional later for queue realism"},
    ]


def build_data_requirements() -> list[dict[str, Any]]:
    return [
        {"data_item": "target_order_list", "required": "yes", "source": "V57f/ERC rebalance signals and target deltas", "pit_requirement": "generated before intraday schedule; no target mutation", "available_now": "yes"},
        {"data_item": "5min_bar_ohlcv_amount", "required": "yes", "source": "BaoStock 5min unadjusted data", "pit_requirement": "only completed bars visible at decision timestamp", "available_now": "yes"},
        {"data_item": "previous_close_and_open", "required": "yes", "source": "daily price and current-day first bar/open", "pit_requirement": "open usable only after market open", "available_now": "yes"},
        {"data_item": "limit_up_down_status", "required": "preferred", "source": "daily limit fields or executable proxy", "pit_requirement": "same-day status at decision timestamp; no forced fill", "available_now": "partial"},
        {"data_item": "pause_or_missing_bar_state", "required": "yes", "source": "5min bar availability and daily paused field when available", "pit_requirement": "logged at decision timestamp", "available_now": "yes"},
        {"data_item": "cash_and_fill_ledger", "required": "yes", "source": "L2/L3 paper matching engine", "pit_requirement": "append-only within day", "available_now": "engineering_needed"},
        {"data_item": "same_day_buy_lot_ledger", "required": "yes", "source": "L3 engine", "pit_requirement": "distinguish old holdings from same-day bought shares", "available_now": "engineering_needed"},
        {"data_item": "order_health_log", "required": "yes", "source": "L3 engine", "pit_requirement": "unfilled reasons must not be backfilled", "available_now": "engineering_needed"},
        {"data_item": "1min_or_order_book_data", "required": "no", "source": "future broker/QMT/JQ/Tushare if opened", "pit_requirement": "optional queue-depth validation only", "available_now": "not_required"},
    ]


def build_next_queue() -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "l3_engineering_001",
            "priority": 1,
            "task": "implement_l3_default_twap_with_exception_engineering_runner",
            "allowed_scope": "L2 size-aware target orders only; exception handling for pause, limit, missing bar, cash shortfall, and price-band non-trigger",
            "blocked_scope": "return selection; T; target mutation; 1min dependency",
            "expected_outputs": "daily paper fills; order health; exception log; unfilled log; PIT visibility audit",
        },
        {
            "queue_id": "l3_engineering_002",
            "priority": 2,
            "task": "implement_open_volatility_delay_diagnostic",
            "allowed_scope": "buy-slice delay based only on completed early 5min bars",
            "blocked_scope": "full-day high/low; optimized thresholds; sell delay for timing",
            "expected_outputs": "delay log; affected order list; order health comparison without return-based selection",
        },
        {
            "queue_id": "l3_engineering_003",
            "priority": 3,
            "task": "implement_price_band_limit_order_diagnostic",
            "allowed_scope": "fixed coarse price-band status and unfilled classification",
            "blocked_scope": "band parameter scan; trend chasing; hidden non-fills",
            "expected_outputs": "band trigger log; price-band unfilled reasons; slippage/cost diagnostic",
        },
        {
            "queue_id": "l3_engineering_004",
            "priority": 4,
            "task": "implement_sell_first_cash_release_and_close_cleanup_validation",
            "allowed_scope": "cash release, buy budget, final cleanup, unfilled logging",
            "blocked_scope": "cross-day retry without separate gate; forced fills",
            "expected_outputs": "cash ledger; cleanup log; no-T validation",
        },
    ]


def build_agent_rules_md() -> str:
    return "\n".join(
        [
            "# V5d L3 Agent Execution Rules",
            "",
            "- V57f and ERC target holdings are inputs only; do not modify them.",
            "- L3 may only schedule already determined target orders.",
            "- Every intraday decision must record `decision_time` and `visible_bar_cutoff_time`.",
            "- Current-window decisions may use only bars completed before that decision.",
            "- Do not use full-day high/low, close, VWAP, TWAP, or later bars unless the decision occurs after they are known.",
            "- Do not run parameter scans or choose rules by historical return.",
            "- Do not implement intraday T, bottom-position trading, trend following, or pattern recognition.",
            "- Same-day buys must be separately tagged from old holdings.",
            "- Every non-fill must be preserved with a fixed reason code.",
            "- If a proposed rule needs 1min data to be defined, stop and write a blocker rather than approximating.",
            "- This packet is a research/spec gate only, not accepted strategy approval.",
            "",
        ]
    )


def build_report(summary: dict[str, Any], candidate_rows: list[dict[str, Any]], blocked_rows: list[dict[str, Any]]) -> str:
    allowed = [row for row in candidate_rows if row["allowed_next_stage"] != "hard_gate_for_all_engineering"]
    lines = [
        "# V5d L3 Intraday Execution-Aware Policy Spec",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: execution scheduling spec only; no backtest, no T, no V57f/ERC changes.",
        "- L3 can use only information visible at the intraday decision timestamp.",
        "- 1min data is not a hard prerequisite for this spec.",
        "",
        "## Allowed Engineering Rules",
        "",
    ]
    for row in allowed:
        lines.append(f"- `{row['rule_id']}`: {row['rule_description']}")
    lines.extend(["", "## Hard Gates", "", "- `no_intraday_T_policy`: zero same-day buy/sell violations required.", "- `unfilled_order_governance`: all non-fills must be classified and logged."])
    lines.extend(["", "## Blocked Ideas", ""])
    for row in blocked_rows:
        lines.append(f"- `{row['action']}`: {row['reason']}")
    lines.extend(["", "## PM Read", "", "L3 is worth engineering as an execution-health layer, not as a minute alpha layer. First priority is default TWAP with exception handling because it preserves L2 size-aware governance while making pause/limit/missing-bar/cash states explicit."])
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in REQUIRED_INPUTS if not path.exists()]
    if blockers:
        write_csv(OUT_DIR / "v5d_l3_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l3_intraday_execution_policy_spec", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l3_intraday_execution_policy_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    data_gate = read_json(REQUIRED_INPUTS[0])
    robustness = read_json(REQUIRED_INPUTS[2])
    l2_summary = read_json(REQUIRED_INPUTS[4])
    l2_pm = read_json(REQUIRED_INPUTS[5])
    erc = read_json(REQUIRED_INPUTS[8])
    boundary_rows = build_boundary_matrix()
    candidate_rows = build_candidate_specs()
    visibility_rows = build_visibility_audit()
    allowed_blocked = build_allowed_blocked()
    data_requirements = build_data_requirements()
    next_queue = build_next_queue()
    blocked_actions = [row for row in allowed_blocked if row["status"] == "blocked"]

    write_csv(OUT_DIR / "v5d_l3_rule_boundary_matrix.csv", boundary_rows)
    write_csv(OUT_DIR / "v5d_l3_candidate_rule_specs.csv", candidate_rows)
    write_csv(OUT_DIR / "v5d_l3_intraday_signal_visibility_audit.csv", visibility_rows)
    write_csv(OUT_DIR / "v5d_l3_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(OUT_DIR / "v5d_l3_data_requirements.csv", data_requirements)
    write_csv(OUT_DIR / "v5d_l3_next_engineering_queue.csv", next_queue)
    write_csv(OUT_DIR / "v5d_l3_blockers.csv", [], ["blocker_id", "severity", "description"])
    (OUT_DIR / "v5d_l3_agent_execution_rules.md").write_text(build_agent_rules_md(), encoding="utf-8")

    summary = {
        "schema_version": 1,
        "project": "v5d_l3_intraday_execution_policy_spec",
        "status": "completed_l3_spec_ready_for_engineering",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "intraday_T_allowed": False,
        "minute_prediction_model_started": False,
        "historical_return_selection_used": False,
        "data_gate_status": data_gate.get("status"),
        "l2_engineering_status": l2_summary.get("status"),
        "l2_pm_status": l2_pm.get("status"),
        "l2_policy_status": l2_pm.get("policy_decision"),
        "erc_status": erc.get("candidate_status"),
        "minute_execution_sensitive": robustness.get("minute_execution_sensitive"),
        "one_minute_data_required_now": False,
        "allowed_engineering_rules": [
            "twap_default_with_exception",
            "open_volatility_delay",
            "price_band_limit_order",
            "sell_first_cash_release",
            "close_cleanup",
            "unfilled_order_governance",
            "no_intraday_T_policy",
        ],
        "blocked_rule_families": [
            "intraday_T",
            "trend_chasing",
            "pattern_recognition",
            "full_day_high_low_use",
            "parameter_scan",
            "return_selection",
            "target_holding_mutation",
        ],
        "blocker_count": 0,
        "next_gate": "l3_default_twap_with_exception_engineering_spec",
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l3_intraday_execution_policy_summary.json"),
            "report": str(OUT_DIR / "v5d_l3_intraday_execution_policy_report.md"),
            "boundary_matrix": str(OUT_DIR / "v5d_l3_rule_boundary_matrix.csv"),
            "candidate_specs": str(OUT_DIR / "v5d_l3_candidate_rule_specs.csv"),
            "visibility_audit": str(OUT_DIR / "v5d_l3_intraday_signal_visibility_audit.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_l3_allowed_blocked_actions.csv"),
            "data_requirements": str(OUT_DIR / "v5d_l3_data_requirements.csv"),
            "next_engineering_queue": str(OUT_DIR / "v5d_l3_next_engineering_queue.csv"),
            "agent_execution_rules": str(OUT_DIR / "v5d_l3_agent_execution_rules.md"),
        },
    }
    (OUT_DIR / "v5d_l3_intraday_execution_policy_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l3_intraday_execution_policy_report.md").write_text(build_report(summary, candidate_rows, blocked_actions), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
