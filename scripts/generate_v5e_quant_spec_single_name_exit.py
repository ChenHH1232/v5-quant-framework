from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\hh\codex\v5")
OUT = ROOT / "v5e_quant_spec_single_name_exit" / "current"
REPAIRED_RUN = (
    ROOT
    / "v5_startup_warmup_price_repair"
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)


def read_json(rel: str) -> dict:
    with (ROOT / rel).open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def read_csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f), [])


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return max(sum(1 for _ in f) - 1, 0)


def write_csv(name: str, rows: list[dict], fieldnames: list[str]) -> None:
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(name: str, data: dict) -> None:
    with (OUT / name).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def file_audit(file_id: str, path: Path, required: list[str], pit: str, use: str) -> dict:
    fields = read_csv_header(path)
    missing = [x for x in required if x not in fields]
    return {
        "data_item": file_id,
        "path": str(path.relative_to(ROOT)) if path.exists() else str(path.relative_to(ROOT)),
        "exists": "yes" if path.exists() else "no",
        "row_count": count_rows(path),
        "required_fields": ";".join(required),
        "available_fields": ";".join(fields),
        "missing_fields": ";".join(missing),
        "field_complete": "yes" if path.exists() and not missing else "no",
        "pit_status": pit,
        "use_classification": use,
        "severity": "pass" if path.exists() and not missing else "blocker",
        "note": "ready for V5e spec/limited engineering" if path.exists() and not missing else "missing required daily engineering input",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    pm = read_json("v5e_holding_period_exit_pm_review/current/v5e_pm_review_summary.json")
    startup = read_json("v5_startup_warmup_price_repair/current/v5_startup_warmup_price_repair_summary.json")
    v5c = read_json("v5c_closeout/current/v5c_closeout_summary.json")
    v5d = read_json("v5d_closeout/current/v5d_closeout_summary.json")
    repaired_summary = read_json(
        "v5_startup_warmup_price_repair/current/runs/v57f_warmup_repaired_daily_backtest/"
        "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/summary.json"
    )

    rule_rows = [
        {
            "rule_id": "single_name_profit_lock_daily_confirmed",
            "rule_role": "single-name holding-period fixed profit lock",
            "trigger_state": "current holding has positive holding-period return versus rebalance reference price",
            "trigger_formula": "holding_return_t = prior_close_t / reference_price - 1; trigger if holding_return_t >= profit_lock_threshold",
            "visibility_rule": "computed after T close using only T close once the daily bar is complete; earliest execution T+1",
            "primary_threshold": "profit_lock_threshold = +20%",
            "conservative_pressure_threshold": "profit_lock_threshold = +30%",
            "threshold_status": "pre_registered_not_optimized",
            "default_action": "sell 50% of current shares rounded down to board lot; if residual would violate lot rule, sell executable board-lot amount only",
            "pressure_action": "sell 33% of current shares rounded down to board lot",
            "cash_policy": "sale proceeds remain portfolio cash until next official V57f rebalance",
            "reentry_policy": "no reentry until next official V57f rebalance",
            "not_allowed": "no same-day trigger execution from future close; no 5min prediction; no threshold scan",
        },
        {
            "rule_id": "single_name_trailing_profit_protection",
            "rule_role": "single-name trailing protection after visible profit",
            "trigger_state": "current holding first achieved visible profit, then pulls back from prior known peak close",
            "trigger_formula": "peak_return_t = max(prior_closes_since_entry) / reference_price - 1; drawdown_from_peak_t = prior_close_t / max(prior_closes_since_entry) - 1; trigger if peak_return_t >= +15% and drawdown_from_peak_t <= -8%",
            "visibility_rule": "computed after T close from closes observed through T; earliest execution T+1",
            "primary_threshold": "profit_state_threshold = +15%; trailing_drawdown_threshold = -8%",
            "conservative_pressure_threshold": "profit_state_threshold = +20%; trailing_drawdown_threshold = -10%",
            "threshold_status": "pre_registered_not_optimized",
            "default_action": "sell 50% of current shares rounded down to board lot; no duplicate sale if profit-lock already executed same day",
            "pressure_action": "sell 33% of current shares rounded down to board lot",
            "cash_policy": "sale proceeds remain portfolio cash until next official V57f rebalance",
            "reentry_policy": "no reentry until next official V57f rebalance",
            "not_allowed": "no stop-loss on losing stocks; no use of same-day intraday high/low; no 5min prediction",
        },
        {
            "rule_id": "no_reentry_until_next_rebalance",
            "rule_role": "governance rule",
            "trigger_state": "any V5e exit action creates an exit lock flag for the stock",
            "trigger_formula": "exit_lock[code] = true from V5e execution date through the day before next official V57f rebalance",
            "visibility_rule": "based on V5e exit log and pre-defined V57f rebalance calendar",
            "primary_threshold": "not parameterized",
            "conservative_pressure_threshold": "not parameterized",
            "threshold_status": "fixed_governance_not_optimized",
            "default_action": "block V5e or discretionary buyback before next official rebalance; allow V57f official rebalance to reset target",
            "pressure_action": "same as primary",
            "cash_policy": "cash remains idle and cash drag must be reported",
            "reentry_policy": "only next V57f official rebalance may restore exposure if stock is selected/targeted",
            "not_allowed": "no same-day sell-buyback; no re-risking before official rebalance",
        },
    ]

    threshold_rows = [
        {
            "policy_id": "main_rule",
            "profit_lock_threshold": "+20%",
            "profit_lock_sell_fraction": "50%",
            "trailing_profit_state_threshold": "+15%",
            "trailing_drawdown_threshold": "-8%",
            "trailing_sell_fraction": "50%",
            "threshold_status": "pre_registered_not_optimized",
            "why_explainable": "V57f is a quarterly high-dividend/low-vol holding strategy; +15% to +20% is a large single-name move within a cycle, and -8% is a visible pullback beyond small daily noise.",
            "why_not_adjust_by_history": "Future engineering may test this single fixed rule for robustness only; it must not be tuned to maximize 2021-2026 return.",
        },
        {
            "policy_id": "conservative_pressure_rule",
            "profit_lock_threshold": "+30%",
            "profit_lock_sell_fraction": "33%",
            "trailing_profit_state_threshold": "+20%",
            "trailing_drawdown_threshold": "-10%",
            "trailing_sell_fraction": "33%",
            "threshold_status": "pre_registered_not_optimized_pressure_check",
            "why_explainable": "A stricter pressure rule tests whether governance conclusions depend on an aggressively early exit, without creating a parameter grid.",
            "why_not_adjust_by_history": "This is not a candidate selector; if results differ, PM reviews fragility rather than picking the higher-return threshold.",
        },
    ]

    trade_rows = [
        {
            "rule_id": "single_name_profit_lock_daily_confirmed",
            "trigger_date": "T, after daily close is complete",
            "decision_visible_date": "T after close / next batch process",
            "execution_earliest_date": "T+1",
            "execution_price_policy": "T+1 daily open proxy for first limited engineering; V5d L2/L3/L4 may later govern execution if available",
            "sell_fraction": "main: 50%; conservative pressure: 33%; rounded down to board lot",
            "cash_policy": "cash until next official V57f rebalance; do not reallocate",
            "reentry_policy": "no reentry until next official V57f rebalance",
            "conflict_resolution": "if trailing rule also triggers, consolidate to one final exit action capped by current shares",
            "t_plus_one_compliance": "no same-day sale from newly bought shares; no intraday T",
            "interaction_with_regular_rebalance": "regular V57f rebalance overrides and resets official target weights",
        },
        {
            "rule_id": "single_name_trailing_profit_protection",
            "trigger_date": "T, after daily close is complete",
            "decision_visible_date": "T after close / next batch process",
            "execution_earliest_date": "T+1",
            "execution_price_policy": "T+1 daily open proxy for first limited engineering; 5min only execution governance later",
            "sell_fraction": "main: 50%; conservative pressure: 33%; rounded down to board lot",
            "cash_policy": "cash until next official V57f rebalance; do not reallocate",
            "reentry_policy": "no reentry until next official V57f rebalance",
            "conflict_resolution": "cannot trigger on losing stocks; if profit-lock already exited same day, do not double-sell beyond current holdings",
            "t_plus_one_compliance": "must not exit shares bought on same day",
            "interaction_with_regular_rebalance": "regular V57f rebalance can restore or remove target exposure",
        },
        {
            "rule_id": "no_reentry_until_next_rebalance",
            "trigger_date": "execution date of any V5e sell",
            "decision_visible_date": "same as V5e sell log visible date",
            "execution_earliest_date": "not applicable",
            "execution_price_policy": "not applicable",
            "sell_fraction": "not applicable",
            "cash_policy": "cash remains idle; cash drag explicitly measured",
            "reentry_policy": "hard block until next official V57f rebalance",
            "conflict_resolution": "V57f official rebalance is the only reset mechanism",
            "t_plus_one_compliance": "pre_rebalance_reentry_count must be zero",
            "interaction_with_regular_rebalance": "if selected at next official rebalance, restore according to V57f target; if not selected, remain out",
        },
    ]

    cash_rows = [
        {"state": "normal_holding", "cash_treatment": "no V5e cash action", "reentry_flag": "false", "reset_rule": "not applicable"},
        {"state": "profit_lock_partial_exit", "cash_treatment": "sell proceeds added to cash ledger", "reentry_flag": "true for exited quantity/name", "reset_rule": "next official V57f rebalance"},
        {"state": "trailing_protection_partial_exit", "cash_treatment": "sell proceeds added to cash ledger", "reentry_flag": "true for exited quantity/name", "reset_rule": "next official V57f rebalance"},
        {"state": "unfilled_exit_order", "cash_treatment": "no cash credited until actual fill", "reentry_flag": "pending; no buyback action allowed", "reset_rule": "execution handling delegated to V5d/L4 if later approved"},
        {"state": "regular_rebalance", "cash_treatment": "V57f target portfolio rebuilds from current cash/holdings", "reentry_flag": "reset by official V57f selection", "reset_rule": "official rebalance only"},
    ]

    trigger_rows = [
        {
            "rule_id": "single_name_profit_lock_daily_confirmed",
            "input": "prior/current completed daily close, reference price, current holding shares, next official rebalance date",
            "visible_when": "after T daily close is final",
            "may_trigger_exit": "yes",
            "execution_only": "no",
            "forbidden": "same-day future close before finalization; 5min trend; next rebalance constituents",
        },
        {
            "rule_id": "single_name_trailing_profit_protection",
            "input": "close series since entry through T, prior known peak close, reference price, current holding shares",
            "visible_when": "after T daily close is final",
            "may_trigger_exit": "yes",
            "execution_only": "no",
            "forbidden": "future full-cycle peak; same-day intraday high/low; stop-loss on losing stock",
        },
        {
            "rule_id": "no_reentry_until_next_rebalance",
            "input": "V5e exit log and official V57f rebalance calendar",
            "visible_when": "after V5e exit order is generated/executed according to ledger state",
            "may_trigger_exit": "governance only",
            "execution_only": "no",
            "forbidden": "manual/discretionary buyback before official rebalance",
        },
        {
            "rule_id": "v5d_execution_interface",
            "input": "T+1 open or later V5d order windows after a V5e exit decision exists",
            "visible_when": "execution stage only",
            "may_trigger_exit": "no",
            "execution_only": "yes",
            "forbidden": "using 5min走势 to decide whether to lock profit",
        },
    ]

    conflict_rows = [
        {"condition": "regular V57f rebalance date and V5e exit same date", "priority": "V57f official rebalance first", "resolution": "use V57f target rebuild; V5e cannot override official target on that date"},
        {"condition": "profit_lock and trailing protection both trigger for same stock", "priority": "single consolidated V5e exit", "resolution": "record both trigger reasons but execute one sell action capped by current executable holdings"},
        {"condition": "stock already V5e-exited before next rebalance", "priority": "no_reentry governance", "resolution": "block buyback; keep cash until next official rebalance"},
        {"condition": "stock paused or sell unavailable on execution day", "priority": "real tradability", "resolution": "record unfilled; do not fabricate fill; future D+1/D+2 handling belongs to V5d/L4"},
        {"condition": "sell quantity below board lot after rounding", "priority": "market lot rule", "resolution": "skip and log uneconomic/non-executable residual unless full position can be legally closed"},
        {"condition": "next V57f rebalance selects exited stock", "priority": "V57f official target", "resolution": "allow restoration to target according to V57f repaired schedule"},
        {"condition": "next V57f rebalance does not select exited stock", "priority": "V57f official target", "resolution": "remain out; cash handled by official rebalance process"},
    ]

    pit_rows = [
        {"audit_item": "profit_lock_close_visibility", "status": "pass_by_spec", "evidence": "trigger forms only after T close is complete", "blocked_pattern": "execute using T close before it is known"},
        {"audit_item": "trailing_peak_visibility", "status": "pass_by_spec", "evidence": "peak is computed from closes observed through decision date only", "blocked_pattern": "use future full-cycle high"},
        {"audit_item": "no_5min_trigger_prediction", "status": "pass_by_spec", "evidence": "5min bars classified as execution-only", "blocked_pattern": "use intraday走势 as exit trigger"},
        {"audit_item": "no_next_rebalance_lookahead", "status": "pass_by_spec", "evidence": "V5e exits cannot know next V57f selected names", "blocked_pattern": "sell early because future rebalance will drop stock"},
        {"audit_item": "no_loss_stop_disguise", "status": "pass_by_spec", "evidence": "trailing rule requires prior floating profit state", "blocked_pattern": "apply trailing rule to losing stocks"},
        {"audit_item": "threshold_optimization", "status": "pass_by_spec", "evidence": "one main rule plus one conservative pressure rule only", "blocked_pattern": "parameter grid or return-ranked selection"},
    ]

    v5d_rows = [
        {"interface_item": "responsibility_split", "v5e_role": "decide whether a holding should be reduced/exited from daily PIT signal", "v5d_role": "decide how the approved sell order is scheduled/executed", "status": "defined"},
        {"interface_item": "daily_open_proxy", "v5e_role": "first limited engineering can use T+1 daily open proxy", "v5d_role": "optional later replacement with L2/L3/L4 execution governance", "status": "ready_for_daily_engineering"},
        {"interface_item": "5min_trigger_forbidden", "v5e_role": "must not use 5min走势 for trigger", "v5d_role": "may use 5min only after exit order exists", "status": "hard_boundary"},
        {"interface_item": "initial_5min_gap", "v5e_role": "non-blocking for daily Quant spec", "v5d_role": "2021-05-06 D0/D1/D2 missing blocks full repaired V5d rerun", "status": "known_nonblocking_gap"},
        {"interface_item": "unfilled_exit_order", "v5e_role": "records intended exit and no-reentry pending state", "v5d_role": "handles paused/limit-down/unfilled retry if later approved", "status": "delegated_to_future_execution_spec"},
    ]

    data_rows = [
        file_audit(
            "repaired_v57f_rebalance_signals",
            REPAIRED_RUN / "rebalance_signals.csv",
            ["trade_date", "code", "target_weight", "rebalance_event_type"],
            "PIT-safe as output of repaired constructor; includes initial_rebalance_event",
            "trigger universe and regular rebalance calendar",
        ),
        file_audit(
            "repaired_v57f_holdings",
            REPAIRED_RUN / "holdings.csv",
            ["trade_date", "code", "amount", "close", "target_weight", "actual_weight"],
            "position state known after valuation date; for future engineering use prior-day holdings for T+1 orders",
            "eligible holdings and share amount",
        ),
        file_audit(
            "repaired_v57f_trades",
            REPAIRED_RUN / "trades.csv",
            ["trade_date", "code", "side", "amount", "price", "value", "commission"],
            "trade ledger after execution; cost/reference basis derived from executed fills",
            "cost basis and reference price",
        ),
        file_audit(
            "repaired_v57f_daily_returns_cash",
            REPAIRED_RUN / "daily_returns.csv",
            ["trade_date", "strategy_return", "strategy_nav", "portfolio_value", "cash", "cash_weight", "holding_count"],
            "daily state after close; trigger and cash accounting must respect visibility time",
            "cash ledger, NAV and cash drag",
        ),
        file_audit(
            "repaired_v57f_dividends",
            REPAIRED_RUN / "dividends.csv",
            ["trade_date", "code", "amount", "net_cash_per_share", "dividend_cash"],
            "cash dividend ledger available for NAV/cash correction; event-risk exits require separate PIT event chain",
            "cash accounting only for this spec",
        ),
        file_audit(
            "repaired_v57f_corporate_actions",
            REPAIRED_RUN / "corporate_actions.csv",
            ["trade_date", "code", "action", "old_amount", "new_amount"],
            "corporate action ledger available after action date",
            "share amount adjustment",
        ),
        file_audit(
            "repaired_v57f_order_health",
            REPAIRED_RUN / "rebalance_order_health.csv",
            ["trade_date", "order_health_status", "executed_order_count", "holding_count_after_rebalance"],
            "post-rebalance audit only",
            "regular rebalance health context",
        ),
    ]

    # Add repaired price files from manifest.
    manifest = ROOT / "v5_startup_warmup_price_repair/current/v5_warmup_repaired_price_manifest.csv"
    with manifest.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            data_rows.append(
                file_audit(
                    f"repaired_daily_ohlc_{row['sector_id']}",
                    ROOT / row["repaired_price_csv"],
                    ["date", "code", "open", "high", "low", "close", "volume", "money", "high_limit", "low_limit", "paused"],
                    "daily market data; trigger may use completed daily close only, tradability fields used for execution audit",
                    "daily trigger and T+1 tradability/execution proxy",
                )
            )

    blockers = []
    if any(r["severity"] == "blocker" for r in data_rows):
        blockers.append(
            {
                "blocker_id": "missing_required_daily_data",
                "severity": "fatal",
                "status": "blocking_limited_engineering_test",
                "description": "One or more required repaired daily data files or fields are missing.",
                "next_action": "repair local daily data gate before engineering",
            }
        )

    blockers.append(
        {
            "blocker_id": "v5d_initial_5min_data_gap",
            "severity": "warning_nonblocking_for_daily_v5e",
            "status": "not_blocking_limited_daily_engineering",
            "description": "2021-05-06 D0/D1/D2 5min data remains missing for repaired V5d execution chain.",
            "next_action": "only required if future V5e execution test delegates to V5d minute execution",
        }
    )

    blockers.append(
        {
            "blocker_id": "advanced_event_exit_data_gate",
            "severity": "warning_not_in_scope",
            "status": "not_blocking_single_name_daily_profit_lock_spec",
            "description": "Event/dividend-safety/FCF/valuation exits still need PIT announcement and visibility chains.",
            "next_action": "keep advanced exits in data-gate-only backlog",
        }
    )

    fatal_blockers = [b for b in blockers if b["severity"] == "fatal"]
    admission = "admit_to_limited_engineering_test" if not fatal_blockers else "blocked_until_data_gate_repaired"

    engineering_queue = [
        {
            "priority": 1,
            "task_name": "V5e limited engineering test: fixed single-name daily profit lock + trailing protection",
            "allowed_scope": "implement exactly main_rule and conservative_pressure_rule as pre-registered robustness check; do not scan",
            "required_inputs": "repaired holdings, trades, daily_returns, rebalance_signals, repaired OHLC, cash ledger",
            "blocked_actions": "parameter grid; historical return selection; V57f modification; accepted marking",
        },
        {
            "priority": 2,
            "task_name": "V5e no-reentry/cash ledger audit",
            "allowed_scope": "validate no same-cycle reentry, cash drag, T+1 compliance and regular rebalance reset",
            "required_inputs": "V5e exit log from limited engineering and repaired V57f rebalance calendar",
            "blocked_actions": "automatic reallocation or buyback before official rebalance",
        },
        {
            "priority": 3,
            "task_name": "Optional V5d execution interface audit",
            "allowed_scope": "only after V5e daily exit orders exist; use V5d L2/L3/L4 as execution governance",
            "required_inputs": "trigger-day execution data; initial 2021-05-06 D0/D1/D2 5min if needed",
            "blocked_actions": "5min trigger prediction or fake minute fills",
        },
    ]

    summary = {
        "schema_version": 1,
        "project": "v5e_quant_spec_single_name_exit",
        "status": "completed_quant_spec_no_backtest",
        "created_at_utc": created_at,
        "working_directory": str(ROOT),
        "source_pm_review_status": pm.get("status"),
        "startup_repair_status": startup.get("status"),
        "baseline_schedule": {
            "repaired_first_signal_date": startup["pre_post"]["repaired_first_signal_date"],
            "repaired_first_trade_date": startup["pre_post"]["repaired_first_trade_date"],
            "startup_gap_days_repaired": startup["pre_post"]["startup_gap_days_repaired"],
            "shadow_config": "config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json",
        },
        "current_task_actions": {
            "engineering_backtest_started": False,
            "parameter_scan_started": False,
            "joinquant_started": False,
            "network_fetch_started": False,
            "v57f_modified": False,
            "erc_modified": False,
            "v5d_modified": False,
            "accepted_marked": False,
        },
        "rules_defined": [
            "single_name_profit_lock_daily_confirmed",
            "single_name_trailing_profit_protection",
            "no_reentry_until_next_rebalance",
        ],
        "threshold_policy": {
            "main_rule": "profit_lock +20% sell 50%; trailing requires +15% peak profit and -8% pullback sell 50%",
            "conservative_pressure_rule": "profit_lock +30% sell 33%; trailing requires +20% peak profit and -10% pullback sell 33%",
            "status": "pre_registered_not_optimized",
            "parameter_grid": False,
        },
        "data_gate_status": "pass_with_warnings" if not fatal_blockers else "blocked",
        "fatal_blocker_count": len(fatal_blockers),
        "warning_count": len([b for b in blockers if b["severity"] != "fatal"]),
        "pm_quant_admission_result": admission,
        "next_gate": admission,
        "known_warnings": [
            "V5d initial 2021-05-06 D0/D1/D2 5min data gap remains non-blocking for daily V5e.",
            "Advanced event/dividend/FCF/valuation exits remain data-gate only.",
        ],
        "baseline_status_context": {
            "v57f": "frozen_formal_etf_candidate_not_accepted_not_live",
            "erc": v5c.get("erc_status", {}).get("status"),
            "v5d_l4": v5d.get("final_candidate_status", {}).get("l4_exception_governed_completion"),
            "repaired_backtest_signal_count": repaired_summary.get("signal_count"),
            "repaired_backtest_trade_count": repaired_summary.get("trade_count"),
        },
        "outputs": {
            "summary": "v5e_quant_spec_single_name_exit/current/v5e_quant_spec_summary.json",
            "report": "v5e_quant_spec_single_name_exit/current/v5e_quant_spec_report.md",
            "rule_spec": "v5e_quant_spec_single_name_exit/current/v5e_rule_spec.csv",
            "trigger_visibility_matrix": "v5e_quant_spec_single_name_exit/current/v5e_trigger_visibility_matrix.csv",
            "pre_registered_threshold_policy": "v5e_quant_spec_single_name_exit/current/v5e_pre_registered_threshold_policy.csv",
            "trade_action_policy": "v5e_quant_spec_single_name_exit/current/v5e_trade_action_policy.csv",
            "cash_reentry_policy": "v5e_quant_spec_single_name_exit/current/v5e_cash_reentry_policy.csv",
            "conflict_resolution_matrix": "v5e_quant_spec_single_name_exit/current/v5e_conflict_resolution_matrix.csv",
            "data_gate_audit": "v5e_quant_spec_single_name_exit/current/v5e_data_gate_audit.csv",
            "pit_leakage_audit": "v5e_quant_spec_single_name_exit/current/v5e_pit_leakage_audit.csv",
            "v5d_execution_interface": "v5e_quant_spec_single_name_exit/current/v5e_v5d_execution_interface.csv",
            "engineering_queue": "v5e_quant_spec_single_name_exit/current/v5e_engineering_queue.csv",
            "blockers": "v5e_quant_spec_single_name_exit/current/v5e_blockers.csv",
            "agent_execution_rules": "v5e_quant_spec_single_name_exit/current/v5e_agent_execution_rules.md",
        },
    }

    report = f"""# V5e Quant spec: single-name daily profit lock + trailing protection

## 结论

本次 V5e 第一阶段 Quant spec 已完成，范围只覆盖三条已获 PM review 准入的规则：

1. `single_name_profit_lock_daily_confirmed`
2. `single_name_trailing_profit_protection`
3. `no_reentry_until_next_rebalance`

本任务没有工程回测，没有调参，没有启动 JoinQuant，没有联网拉数据，也没有修改 V57f / ERC / V5d。所有阈值均标记为 `pre_registered_not_optimized`，不得根据历史收益调整。

## 基线

V5e 必须基于 repaired startup schedule / shadow config。当前 repaired first_signal / first_trade 为 `{startup["pre_post"]["repaired_first_signal_date"]}`，startup_gap 已从 `{startup["pre_post"]["startup_gap_days_old"]}` 天降到 `{startup["pre_post"]["startup_gap_days_repaired"]}` 天。原 V57f config 未覆盖，V57f core 逻辑未修改。

## 三条规则定义

### single_name_profit_lock_daily_confirmed

- 类型：单股持仓期固定利润锁定规则。
- 触发：T 日收盘后，使用已经完成的日线 close 计算持仓期收益。
- 主规则：持仓期收益达到 `+20%` 后，T+1 以 daily open 代理卖出当前可执行股数的 `50%`。
- 保守压力规则：持仓期收益达到 `+30%` 后，T+1 卖出 `33%`。
- 卖出后现金保留到下一次 V57f 正式调仓，不重配。
- 不允许用当日未完成 close、5 分钟走势或未来调仓结果。

### single_name_trailing_profit_protection

- 类型：单股浮盈后的回撤保护规则。
- 触发：必须先有浮盈状态，使用从建仓以来截至 T 日已经可见的最高收盘价锚点。
- 主规则：阶段峰值收益至少 `+15%`，且从该已知峰值回撤达到 `-8%`，T+1 卖出 `50%`。
- 保守压力规则：阶段峰值收益至少 `+20%`，回撤达到 `-10%`，T+1 卖出 `33%`。
- 该规则不能伪装成亏损止损，亏损股不得触发。

### no_reentry_until_next_rebalance

- 类型：治理规则。
- 任一 V5e 规则卖出后，该股票在下一次 V57f 正式调仓前不得重新买入。
- 如果下一次 V57f 正式调仓仍选中该股票，才允许按 V57f 目标恢复。
- 如果下一次 V57f 正式调仓未选中，则保持不持有。

## 数据门

repaired 日频数据门通过，带 warning：

- repaired holdings / trades / daily_returns / rebalance_signals 均存在。
- repaired daily OHLC 存在，且包含 open/high/low/close、paused、high_limit、low_limit。
- cash path 可从 repaired daily_returns 的 `cash` / `cash_weight` 读取。
- cost basis / reference price 可从 repaired trades 的成交价生成。
- dividends / corporate_actions 可用于现金和持仓数量校正。

warning：V5d 初始 `2021-05-06` D0/D1/D2 5 分钟数据仍缺，但这不阻塞 V5e 日频触发规则。5 分钟只能作为未来执行治理，不得作为止盈触发预测。

## 冲突处理

- V57f 正式调仓优先于 V5e overlay。
- V5e 退出不能提前知道下一次 V57f 调仓结果。
- 同一天 profit-lock 与 trailing protection 同时触发时，只执行一个最终 exit action，且不得超过当前持仓。
- 停牌、跌停或无法卖出时，记录 unfilled，不强造成交；后续 D+1/D+2 是否继续交给 V5d/L4。
- 卖出后在下一次正式调仓前不得买回。

## Admission result

下一门决策：`{admission}`。

允许进入 limited engineering test 的原因：

- repaired V57f daily path 可用；
- 触发规则 PIT 可解释；
- 阈值固定且未优化；
- 卖出后现金和 reentry 规则明确；
- T+1 规则明确；
- 不修改 V57f；
- 不需要未来数据；
- 不需要 5 分钟预测信号。

这只是允许后续开一个有限工程测试任务，不代表 V5e accepted，也不代表 V57f replacement。
"""

    agent_rules = """# V5e Quant Spec Agent Execution Rules

1. This packet is a Quant spec only; do not run engineering backtests from it.
2. Use repaired startup schedule / shadow config only.
3. Do not modify V57f, ERC, V5c, or V5d.
4. Do not start JoinQuant or fetch network data.
5. Do not scan thresholds or pick thresholds by historical returns.
6. The main rule and conservative pressure rule are pre-registered, not optimized.
7. V5e triggers use daily PIT information only; 5min data is execution-only.
8. All V5e sell proceeds remain cash until the next official V57f rebalance.
9. No same-day sell-buyback, no intraday T, no reentry before official rebalance.
10. V57f official rebalance overrides and resets V5e exit locks according to official targets.
11. Record unfilled exits; do not fabricate fills.
12. Do not mark V5e accepted, live-approved, or V57f replacement.
"""

    write_json("v5e_quant_spec_summary.json", summary)
    (OUT / "v5e_quant_spec_report.md").write_text(report, encoding="utf-8")
    write_csv("v5e_rule_spec.csv", rule_rows, list(rule_rows[0].keys()))
    write_csv("v5e_trigger_visibility_matrix.csv", trigger_rows, list(trigger_rows[0].keys()))
    write_csv("v5e_pre_registered_threshold_policy.csv", threshold_rows, list(threshold_rows[0].keys()))
    write_csv("v5e_trade_action_policy.csv", trade_rows, list(trade_rows[0].keys()))
    write_csv("v5e_cash_reentry_policy.csv", cash_rows, list(cash_rows[0].keys()))
    write_csv("v5e_conflict_resolution_matrix.csv", conflict_rows, list(conflict_rows[0].keys()))
    write_csv("v5e_data_gate_audit.csv", data_rows, list(data_rows[0].keys()))
    write_csv("v5e_pit_leakage_audit.csv", pit_rows, list(pit_rows[0].keys()))
    write_csv("v5e_v5d_execution_interface.csv", v5d_rows, list(v5d_rows[0].keys()))
    write_csv("v5e_engineering_queue.csv", engineering_queue, list(engineering_queue[0].keys()))
    write_csv("v5e_blockers.csv", blockers, list(blockers[0].keys()))
    (OUT / "v5e_agent_execution_rules.md").write_text(agent_rules, encoding="utf-8")

    print(f"generated {len(summary['outputs'])} files in {OUT}")
    print(admission)


if __name__ == "__main__":
    main()
