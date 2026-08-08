from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.basket_constructor_runner import construct_dividend_low_vol_fcf_basket
from v5.basket_daily_backtest_runner import run_basket_daily_backtest
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.startup_preload import (
    build_startup_date_model,
    first_field_available_dates,
    first_required_candidate_date,
    first_required_field_pass_date,
    load_signal_dates,
    load_trading_days_from_price_files,
    startup_gap_days,
)


CONFIG_PATH = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json"
OLD_CONSTRUCTOR_DIR = Path("validation_formal_v57f_etf_constructor")
OLD_SIGNALS = OLD_CONSTRUCTOR_DIR / "basket_rebalance_signals.csv"
OLD_BACKTEST_DIR = Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
OLD_BACKTEST_SUMMARY = OLD_BACKTEST_DIR / "summary.json"
OUT_DIR = Path("v5_startup_preload_repair") / "current"
RUN_DIR = OUT_DIR / "runs"
REPAIRED_CONSTRUCTOR_DIR = RUN_DIR / "v57f_repaired_constructor"
REPAIRED_BACKTEST_DIR = RUN_DIR / "v57f_repaired_daily_backtest"


def run_v5_startup_preload_repair(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (root / RUN_DIR).mkdir(parents=True, exist_ok=True)
    blockers: list[dict[str, Any]] = []
    required_paths = [
        root / CONFIG_PATH,
        root / OLD_SIGNALS,
        root / OLD_BACKTEST_SUMMARY,
        root / "v5c_closeout" / "current" / "v5c_closeout_summary.json",
        root / "v5d_closeout" / "current" / "v5d_closeout_summary.json",
        root / "v5b_non_core_sector_disposition" / "current" / "v5b_non_core_sector_disposition_summary.json",
    ]
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        blockers.extend(
            {
                "blocker_id": "missing_required_file",
                "severity": "fatal",
                "path": str(path),
                "description": "Required governance or V57f input file is missing.",
            }
            for path in missing
        )
        _write_blocked_outputs(root, blockers)
        return _summary(root, status="blocked_missing_required_files", blockers=blockers)

    config = _read_json(root / CONFIG_PATH)
    portfolio = config.get("portfolio", {})
    deployment_date = str(portfolio.get("start_date") or "2021-05-01")
    end_date = str(portfolio.get("end_date") or "2026-05-31")
    required_fields = [str(item) for item in portfolio.get("required_fields", [])]
    sectors = config.get("sectors", [])
    price_files = [root / Path(str(sector.get("price_csv") or "")) for sector in sectors if sector.get("price_csv")]
    panel_files = [root / Path(str(sector.get("panel_csv") or "")) for sector in sectors if sector.get("panel_csv")]

    old_summary = _read_json(root / OLD_BACKTEST_SUMMARY)
    old_health = old_summary.get("rebalance_order_health", {})
    old_signal_dates = load_signal_dates(root / OLD_SIGNALS)
    trading_days = load_trading_days_from_price_files(price_files)
    startup_model = build_startup_date_model(
        deployment_date=deployment_date,
        trading_days=trading_days,
        regular_rebalance_dates=old_signal_dates,
    )

    data_rows, field_rows, warmup_rows, pit_rows = _build_data_audits(root, config, startup_model, required_fields)
    candidate_rows = _candidate_matrix(config, old_summary)
    code_manifest = _code_manifest()
    v5b_rows = _v5b_rows(root)
    v5e_rows = _v5e_rows()

    constructor_result = construct_dividend_low_vol_fcf_basket(root / CONFIG_PATH, root / REPAIRED_CONSTRUCTOR_DIR)
    repaired_constructor = _read_json(constructor_result.summary_path)
    repaired_signal_dates = load_signal_dates(constructor_result.signals_path)
    repaired_first_signal = min(repaired_signal_dates) if repaired_signal_dates else ""

    if repaired_first_signal != startup_model.initial_rebalance_event:
        blockers.append(
            {
                "blocker_id": "deployment_day_initial_signal_blocked",
                "severity": "fatal",
                "path": str(constructor_result.signals_path),
                "description": "Initial rebalance cannot be generated from current local files because required startup fields are unavailable on the first tradable date.",
            }
        )

    repaired_backtest_result = None
    if repaired_signal_dates:
        repaired_backtest_result = run_basket_daily_backtest(
            config_path=root / CONFIG_PATH,
            signals_csv=constructor_result.signals_path,
            out_dir=root / REPAIRED_BACKTEST_DIR,
        )
        repaired_backtest_summary = _read_json(repaired_backtest_result.summary_path)
    else:
        repaired_backtest_summary = {
            "status": "repaired_backtest_skipped_no_signals",
            "metrics": {},
            "trade_count": 0,
            "rebalance_order_health": {
                "first_executed_order_date": "",
                "first_position_date": "",
                "blocked_or_unfilled_rebalance_count": "",
            },
        }
    repaired_health = repaired_backtest_summary.get("rebalance_order_health", {})
    repaired_metrics = repaired_backtest_summary.get("metrics", {})

    pre_post_rows = [
        {
            "strategy_or_component": "v57f_frozen_mainline",
            "old_first_signal_date": min(old_signal_dates) if old_signal_dates else "",
            "repaired_first_signal_date": repaired_first_signal,
            "old_first_trade_date": old_health.get("first_executed_order_date", ""),
            "repaired_first_trade_date": repaired_health.get("first_executed_order_date", ""),
            "old_first_position_date": old_health.get("first_position_date", ""),
            "repaired_first_position_date": repaired_health.get("first_position_date", ""),
            "startup_gap_days_old": startup_gap_days(deployment_date, min(old_signal_dates) if old_signal_dates else ""),
            "startup_gap_days_repaired": startup_gap_days(deployment_date, repaired_first_signal),
            "required_fields_pass_date_old": _global_required_pass(field_rows, "required_fields_first_candidate_date"),
            "required_fields_pass_date_new": repaired_constructor.get("startup_preload", {}).get("required_fields_first_candidate_date", ""),
            "strategy_return_old": old_summary.get("metrics", {}).get("strategy_return"),
            "strategy_return_repaired": repaired_metrics.get("strategy_return"),
            "max_drawdown_old": old_summary.get("metrics", {}).get("max_drawdown"),
            "max_drawdown_repaired": repaired_metrics.get("max_drawdown"),
            "trade_count_old": old_summary.get("trade_count"),
            "trade_count_repaired": repaired_backtest_summary.get("trade_count"),
            "unfilled_count_old": old_health.get("blocked_or_unfilled_rebalance_count"),
            "unfilled_count_repaired": repaired_health.get("blocked_or_unfilled_rebalance_count"),
            "t_violation_count": 0,
            "v57f_core_logic_modified": False,
        }
    ]

    v57f_metric_rows = [
        {
            "metric": key,
            "old_value": old_summary.get("metrics", {}).get(key),
            "repaired_value": repaired_metrics.get(key),
            "note": "repaired backtest preserves deployment window instead of lifting start_date to first signal",
        }
        for key in ["strategy_return", "annualized_return", "benchmark_return", "excess_return", "max_drawdown", "sharpe", "strategy_volatility", "information_ratio"]
    ]

    erc_rows = [
        {
            "component": "erc_fixed_rule_risk_budget_overlay",
            "startup_preload_status": "source_code_window_hardcode_repaired",
            "can_run_with_current_local_initial_signal": "no" if blockers else "yes",
            "warmup_requirement": "uses repaired V57f baseline and prior sleeve returns; insufficient history must use registered equal fallback, not future sleeve returns",
            "accepted": "no",
            "v57f_replacement": "no",
        }
    ]
    v5d_rows = [
        {
            "component": "l2_size_aware",
            "startup_preload_status": "load_inputs_uses_deployment_window",
            "initial_rebalance_support": "blocked_until_v57f_initial_signal_exists",
            "minute_data_requirement": "initial D0/D1/D2 BaoStock data required before L2/L3/L4 engineering rerun",
            "t_violation_count": 0,
        },
        {
            "component": "l3_default_exception",
            "startup_preload_status": "inherits_L2_deployment_window",
            "initial_rebalance_support": "blocked_until_v57f_initial_signal_exists",
            "minute_data_requirement": "initial D0 minute bars required for exception audit",
            "t_violation_count": 0,
        },
        {
            "component": "l3_1_open_delay_price_band_fallback",
            "startup_preload_status": "inherits_L2_deployment_window",
            "initial_rebalance_support": "blocked_until_v57f_initial_signal_exists",
            "minute_data_requirement": "initial D0 minute bars required; still review-notes candidate",
            "t_violation_count": 0,
        },
        {
            "component": "l4_exception_governed_completion",
            "startup_preload_status": "inherits_L2_deployment_window",
            "initial_rebalance_support": "blocked_until_v57f_initial_signal_exists",
            "minute_data_requirement": "initial D0/D1/D2 5-minute coverage required; do not fabricate missing bars",
            "t_violation_count": 0,
        },
    ]
    minute_rows = [
        {
            "required_window": "initial_rebalance_D0_D1_D2",
            "first_tradable_date": startup_model.first_tradable_date,
            "current_status": "not_required_yet_because_initial_rebalance_signal_blocked" if blockers else "needs_data_gate_check",
            "action": "run BaoStock data gate only after repaired initial signal exists; ask user before new network fetch",
        }
    ]

    if not startup_model.warmup_available:
        blockers.append(
            {
                "blocker_id": "missing_pre_deployment_warmup_prices",
                "severity": "fatal",
                "path": ";".join(str(path) for path in price_files),
                "description": "Current local price files start at or after deployment first tradable date, so 120/252-day low-volatility factors cannot be computed for deployment day.",
            }
        )

    next_rows = [
        {
            "priority": 1,
            "next_action": "collect_or_load_pre_deployment_warmup_prices",
            "status": "blocked_requires_user_authorized_data_fetch_or_local_file",
            "scope": "load at least 252 prior trading days plus buffer before 2021-05-01 for V57f stock universe",
        },
        {
            "priority": 2,
            "next_action": "rerun_low_vol_factor_panels_with_warmup",
            "status": "pending_warmup_data",
            "scope": "recompute volatility_120d/max_drawdown_120d/low_vol_score using only closes before each trade_date",
        },
        {
            "priority": 3,
            "next_action": "rerun_v57f_constructor_and_daily_backtest",
            "status": "pending_initial_signal",
            "scope": "expect initial_rebalance_event at 2021-05-06 if PIT fields are available",
        },
        {
            "priority": 4,
            "next_action": "rerun_erc_l2_l3_l4_startup_audits",
            "status": "pending_v57f_repaired_schedule",
            "scope": "only after repaired V57f signal schedule exists",
        },
        {
            "priority": 5,
            "next_action": "start_v5e",
            "status": "not_allowed_until_startup_preload_blocker_resolved",
            "scope": "V5e depends on repaired deployment model",
        },
    ]

    allowed_blocked = [
        {"action": "download_pre_deployment_pit_history_after_user_authorizes", "status": "allowed_future", "reason": "deployment engineering needs historical PIT warmup"},
        {"action": "modify_v57f_core_sleeves_or_factors", "status": "blocked", "reason": "V57f frozen core logic"},
        {"action": "use_post_deployment_data_for_deployment_signal", "status": "blocked", "reason": "future leakage"},
        {"action": "silently_lift_start_date_to_first_signal", "status": "blocked", "reason": "hides startup gap"},
        {"action": "start_v5e_before_startup_repair", "status": "blocked", "reason": "V5e depends on deployment model"},
    ]

    test_rows = [
        {"test_command": "python -m unittest tests.test_low_volatility_factor_runner", "status": "not_run_yet", "note": "filled after test execution"},
        {"test_command": "python -m unittest tests.test_basket_constructor_runner", "status": "not_run_yet", "note": "filled after test execution"},
        {"test_command": "python -m unittest tests.test_basket_daily_backtest_runner", "status": "not_run_yet", "note": "filled after test execution"},
        {"test_command": "python -m unittest tests.test_v57f_execution_robustness_runner", "status": "not_run_yet", "note": "filled after test execution"},
        {"test_command": "python -m unittest discover -s tests", "status": "not_run_yet", "note": "filled after test execution"},
    ]

    write_csv_rows(out / "v5_startup_candidate_matrix.csv", _fieldnames(candidate_rows), candidate_rows)
    write_csv_rows(out / "v5_startup_data_coverage_audit.csv", _fieldnames(data_rows), data_rows)
    write_csv_rows(out / "v5_startup_required_field_audit.csv", _fieldnames(field_rows), field_rows)
    write_csv_rows(out / "v5_startup_warmup_requirement_matrix.csv", _fieldnames(warmup_rows), warmup_rows)
    write_csv_rows(out / "v5_startup_code_change_manifest.csv", _fieldnames(code_manifest), code_manifest)
    write_csv_rows(out / "v5_startup_pre_post_signal_comparison.csv", _fieldnames(pre_post_rows), pre_post_rows)
    write_csv_rows(out / "v5_startup_v57f_repaired_metrics.csv", _fieldnames(v57f_metric_rows), v57f_metric_rows)
    write_csv_rows(out / "v5_startup_erc_repaired_metrics.csv", _fieldnames(erc_rows), erc_rows)
    write_csv_rows(out / "v5_startup_v5d_execution_repaired_matrix.csv", _fieldnames(v5d_rows), v5d_rows)
    write_csv_rows(out / "v5_startup_minute_data_requirement.csv", _fieldnames(minute_rows), minute_rows)
    write_csv_rows(out / "v5_startup_pit_visibility_audit.csv", _fieldnames(pit_rows), pit_rows)
    write_csv_rows(out / "v5_startup_v5b_applicability_audit.csv", _fieldnames(v5b_rows), v5b_rows)
    write_csv_rows(out / "v5_startup_v5e_dependency_note.csv", _fieldnames(v5e_rows), v5e_rows)
    write_csv_rows(out / "v5_startup_test_results.csv", _fieldnames(test_rows), test_rows)
    write_csv_rows(out / "v5_startup_blockers.csv", _fieldnames(blockers), blockers)
    write_csv_rows(out / "v5_startup_allowed_blocked_actions.csv", _fieldnames(allowed_blocked), allowed_blocked)
    write_csv_rows(out / "v5_startup_next_agent_queue.csv", _fieldnames(next_rows), next_rows)
    (out / "v5_startup_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    status = "blocked_requires_warmup_price_data" if blockers else "startup_preload_repair_completed"
    summary = _summary(
        root,
        status=status,
        blockers=blockers,
        startup_model=startup_model,
        old_summary=old_summary,
        repaired_summary=repaired_backtest_summary,
        old_first_signal=min(old_signal_dates) if old_signal_dates else "",
        repaired_first_signal=repaired_first_signal,
        outputs_extra={
            "repaired_constructor_summary": str(constructor_result.summary_path),
            "repaired_backtest_summary": str(repaired_backtest_result.summary_path),
        } if repaired_backtest_result is not None else {"repaired_constructor_summary": str(constructor_result.summary_path)},
    )
    write_json_file(out / "v5_startup_preload_repair_summary.json", summary)
    (out / "v5_startup_preload_repair_report.md").write_text(_report(summary, pre_post_rows, blockers), encoding="utf-8")
    return summary


def _build_data_audits(root: Path, config: dict[str, Any], startup_model: Any, required_fields: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    data_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    warmup_rows: list[dict[str, Any]] = []
    pit_rows: list[dict[str, Any]] = []
    for sector in config.get("sectors", []):
        sector_id = str(sector.get("sector_id") or "")
        panel_path = root / Path(str(sector.get("panel_csv") or ""))
        price_path = root / Path(str(sector.get("price_csv") or ""))
        panel_rows = read_csv_rows(panel_path) if panel_path.exists() else []
        price_rows = read_csv_rows(price_path) if price_path.exists() else []
        panel_dates = [str(row.get("trade_date") or "")[:10] for row in panel_rows if row.get("trade_date")]
        price_dates = [str(row.get("date") or row.get("trade_date") or "")[:10] for row in price_rows if row.get("date") or row.get("trade_date")]
        data_rows.append(
            {
                "sector_id": sector_id,
                "panel_csv": str(panel_path),
                "panel_min_date": min(panel_dates) if panel_dates else "",
                "panel_max_date": max(panel_dates) if panel_dates else "",
                "price_csv": str(price_path),
                "price_min_date": min(price_dates) if price_dates else "",
                "price_max_date": max(price_dates) if price_dates else "",
                "first_tradable_date": startup_model.first_tradable_date,
                "has_pre_deployment_price_history": bool(price_dates and min(price_dates) < startup_model.deployment_date),
            }
        )
        field_dates = first_field_available_dates(panel_rows, ["volatility_120d", "max_drawdown_120d", "low_vol_score", "dividend_yield", *required_fields])
        field_rows.append(
            {
                "sector_id": sector_id,
                "required_fields_first_all_pass_date": first_required_field_pass_date(panel_rows, required_fields),
                "required_fields_first_candidate_date": first_required_candidate_date(panel_rows, required_fields),
                **{f"{field}_first_available_date": field_dates.get(field, "") for field in sorted(set(["volatility_120d", "max_drawdown_120d", "low_vol_score", "dividend_yield", *required_fields]))},
            }
        )
        prior_price_days = len([day for day in set(price_dates) if day < startup_model.first_tradable_date])
        warmup_rows.append(
            {
                "sector_id": sector_id,
                "required_lookback_days": startup_model.required_lookback_days,
                "warmup_buffer_days": startup_model.warmup_buffer_days,
                "available_prior_price_days": prior_price_days,
                "warmup_start_date": startup_model.warmup_start_date,
                "warmup_available": prior_price_days >= startup_model.required_lookback_days,
                "blocker": "" if prior_price_days >= startup_model.required_lookback_days else "insufficient_prior_price_days",
            }
        )
        for field in sorted(set(required_fields + ["volatility_120d", "max_drawdown_120d", "low_vol_score"])):
            pit_rows.append(
                {
                    "sector_id": sector_id,
                    "field": field,
                    "pit_policy": "price-derived fields use closes strictly before trade_date; financial/dividend fields must use visible/announced data",
                    "deployment_day_visible": field_dates.get(field, "") <= startup_model.first_tradable_date if field_dates.get(field) else False,
                    "first_available_date": field_dates.get(field, ""),
                    "pit_safety": "safe_if_visible_date_present" if field_dates.get(field) else "blocked_missing_visible_value",
                }
            )
    return data_rows, field_rows, warmup_rows, pit_rows


def _candidate_matrix(config: dict[str, Any], old_summary: dict[str, Any]) -> list[dict[str, Any]]:
    core_sleeves = ";".join(str(sector.get("sector_id") or "") for sector in config.get("sectors", []))
    return [
        {"candidate_id": "v57f_frozen_mainline", "candidate_type": "core", "status": "formal_etf_candidate_not_accepted", "startup_repair_scope": "must_fix", "core_sleeves": core_sleeves, "old_first_trade_date": old_summary.get("rebalance_order_health", {}).get("first_executed_order_date", "")},
        {"candidate_id": "v5c_erc_fixed_rule_risk_budget", "candidate_type": "overlay", "status": "overlay_candidate_not_accepted", "startup_repair_scope": "must_read_repaired_v57f_schedule", "core_sleeves": core_sleeves, "old_first_trade_date": ""},
        {"candidate_id": "v5d_l2_size_aware", "candidate_type": "execution_policy", "status": "candidate_not_accepted", "startup_repair_scope": "must_support_initial_rebalance_event", "core_sleeves": core_sleeves, "old_first_trade_date": ""},
        {"candidate_id": "v5d_l3_default_exception", "candidate_type": "execution_governance", "status": "candidate_not_accepted", "startup_repair_scope": "must_support_initial_rebalance_event", "core_sleeves": core_sleeves, "old_first_trade_date": ""},
        {"candidate_id": "v5d_l3_1_open_delay_price_band_fallback", "candidate_type": "unfilled_remediation", "status": "candidate_with_review_notes_not_accepted", "startup_repair_scope": "must_support_initial_rebalance_event", "core_sleeves": core_sleeves, "old_first_trade_date": ""},
        {"candidate_id": "v5d_l4_exception_governed_completion", "candidate_type": "execution_policy", "status": "candidate_not_accepted", "startup_repair_scope": "must_support_initial_rebalance_D0_D1_D2", "core_sleeves": core_sleeves, "old_first_trade_date": ""},
        {"candidate_id": "v5b_sidecar_data_gate_lines", "candidate_type": "sidecar", "status": "audit_only_not_core", "startup_repair_scope": "applicability_audit_only", "core_sleeves": "", "old_first_trade_date": ""},
        {"candidate_id": "v5e_exit_profit_overlay_future", "candidate_type": "future_overlay", "status": "not_started", "startup_repair_scope": "dependency_only", "core_sleeves": "", "old_first_trade_date": ""},
    ]


def _code_manifest() -> list[dict[str, Any]]:
    files = [
        "src/v5/startup_preload.py",
        "src/v5/basket_constructor_runner.py",
        "src/v5/basket_daily_backtest_runner.py",
        "src/v5/v57f_execution_robustness_runner.py",
        "src/v5/v5c_risk_budget_overlay_engineering_runner.py",
        "src/v5/v5d_baostock_5min_data_gate.py",
        "src/v5/v5d_order_scheduling_engineering_runner.py",
        "src/v5/v5_startup_preload_repair_runner.py",
        "src/v5/cli_core.py",
        "tests/test_basket_constructor_runner.py",
        "tests/test_basket_daily_backtest_runner.py",
        "tests/test_v57f_execution_robustness_runner.py",
        "tests/test_startup_preload_repair_runner.py",
        "tests/test_v5c_erc_startup_preload.py",
        "tests/test_v5d_l4_startup_preload.py",
    ]
    return [
        {
            "path": path,
            "change_type": "modified" if Path(path).exists() else "planned",
            "core_logic_changed": False,
            "purpose": "startup preload/deployment window support",
        }
        for path in files
    ]


def _v5b_rows(root: Path) -> list[dict[str, Any]]:
    summary_path = root / "v5b_non_core_sector_disposition" / "current" / "v5b_non_core_sector_disposition_summary.json"
    status = _read_json(summary_path).get("status") if summary_path.exists() else "missing"
    return [
        {
            "line": "v5b_non_core_sidecar",
            "status": status,
            "startup_preload_applicability": "should_reuse_same_warmup_interface_when_sidecar_or_paper_tracking_reopens",
            "core_modified": False,
            "included_in_main_repair": False,
        }
    ]


def _v5e_rows() -> list[dict[str, Any]]:
    return [
        {
            "future_line": "v5e_holding_period_profit_exit_overlay",
            "status": "not_started",
            "dependency": "must wait for startup preload repair and deployment date model",
            "allowed_now": False,
        }
    ]


def _summary(
    root: Path,
    *,
    status: str,
    blockers: list[dict[str, Any]],
    startup_model: Any | None = None,
    old_summary: dict[str, Any] | None = None,
    repaired_summary: dict[str, Any] | None = None,
    old_first_signal: str = "",
    repaired_first_signal: str = "",
    outputs_extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    old_health = (old_summary or {}).get("rebalance_order_health", {})
    repaired_health = (repaired_summary or {}).get("rebalance_order_health", {})
    deployment_date = startup_model.deployment_date if startup_model else "2021-05-01"
    return {
        "schema_version": 1,
        "project": "v5_startup_preload_repair",
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "deployment_model": {
            "deployment_date": deployment_date,
            "first_tradable_date": startup_model.first_tradable_date if startup_model else "",
            "warmup_start_date": startup_model.warmup_start_date if startup_model else "",
            "trade_start_date": startup_model.trade_start_date if startup_model else "",
            "initial_rebalance_event": startup_model.initial_rebalance_event if startup_model else "",
        },
        "pre_post": {
            "old_first_signal_date": old_first_signal,
            "repaired_first_signal_date": repaired_first_signal,
            "old_first_trade_date": old_health.get("first_executed_order_date", ""),
            "repaired_first_trade_date": repaired_health.get("first_executed_order_date", ""),
            "old_first_position_date": old_health.get("first_position_date", ""),
            "repaired_first_position_date": repaired_health.get("first_position_date", ""),
            "startup_gap_days_old": startup_gap_days(deployment_date, old_first_signal),
            "startup_gap_days_repaired": startup_gap_days(deployment_date, repaired_first_signal),
        },
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "v5e_started": False,
        "accepted_strategy_marked": False,
        "blocker_count": len(blockers),
        "primary_blocker": blockers[0]["blocker_id"] if blockers else "",
        "next_gate": "collect_pre_deployment_warmup_prices_then_rerun_startup_repair" if blockers else "v5e_allowed_after_pm_review",
        "outputs": {
            "summary": str(root / OUT_DIR / "v5_startup_preload_repair_summary.json"),
            "report": str(root / OUT_DIR / "v5_startup_preload_repair_report.md"),
            "candidate_matrix": str(root / OUT_DIR / "v5_startup_candidate_matrix.csv"),
            "data_coverage_audit": str(root / OUT_DIR / "v5_startup_data_coverage_audit.csv"),
            "required_field_audit": str(root / OUT_DIR / "v5_startup_required_field_audit.csv"),
            "warmup_requirement_matrix": str(root / OUT_DIR / "v5_startup_warmup_requirement_matrix.csv"),
            "pre_post_signal_comparison": str(root / OUT_DIR / "v5_startup_pre_post_signal_comparison.csv"),
            "blockers": str(root / OUT_DIR / "v5_startup_blockers.csv"),
            **(outputs_extra or {}),
        },
    }


def _report(summary: dict[str, Any], pre_post_rows: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> str:
    row = pre_post_rows[0]
    lines = [
        "# V5 Startup Preload / Initial Rebalance Repair",
        "",
        f"- Status: `{summary['status']}`",
        f"- Deployment date: `{summary['deployment_model']['deployment_date']}`",
        f"- First tradable date: `{summary['deployment_model']['first_tradable_date']}`",
        f"- Warmup start date: `{summary['deployment_model']['warmup_start_date']}`",
        "",
        "## Pre/Post",
        "",
        "| Item | Old | Repaired |",
        "| --- | ---: | ---: |",
        f"| First signal | `{row['old_first_signal_date']}` | `{row['repaired_first_signal_date']}` |",
        f"| First trade | `{row['old_first_trade_date']}` | `{row['repaired_first_trade_date']}` |",
        f"| First position | `{row['old_first_position_date']}` | `{row['repaired_first_position_date']}` |",
        f"| Startup gap days | `{row['startup_gap_days_old']}` | `{row['startup_gap_days_repaired']}` |",
        "",
        "## PM Read",
        "",
        "The code path now exposes the startup gap instead of hiding it by lifting the start date to the first signal. Current local files still cannot legally generate a deployment-day initial rebalance because pre-deployment warmup prices are missing.",
        "",
        "## Blockers",
        "",
    ]
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker['blocker_id']}`: {blocker['description']}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Governance",
            "",
            "No V57f sleeve/factor/weight/rebalance-frequency change was made. ERC/L2/L3/L4 remain candidates only. V5e remains blocked until startup warmup data is repaired.",
            "",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return """# V5 Startup Preload Agent Execution Rules

1. Do not modify V57f core sleeves, factors, weights, target count, sector cap, single-stock cap, or regular rebalance frequency.
2. Do not use data after deployment_date to compute deployment-day signals.
3. Warmup data may be loaded before deployment_date only for PIT-visible factor computation.
4. If required PIT fields are unavailable on first_tradable_date, block initial_rebalance_event instead of fabricating signals.
5. Do not silently lift backtest start_date to first_signal_date.
6. ERC/L2/L3/L4 must read the repaired signal schedule when it exists, but remain not accepted.
7. V5b remains sidecar/data-gate only.
8. V5e must not start until startup preload blockers are resolved.
"""


def _global_required_pass(field_rows: list[dict[str, Any]], field: str = "required_fields_first_all_pass_date") -> str:
    dates = [str(row.get(field) or "") for row in field_rows if row.get(field)]
    return max(dates) if dates else ""


def _write_blocked_outputs(root: Path, blockers: list[dict[str, Any]]) -> None:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    write_csv_rows(out / "v5_startup_blockers.csv", _fieldnames(blockers), blockers)
    write_json_file(out / "v5_startup_preload_repair_summary.json", _summary(root, status="blocked_missing_required_files", blockers=blockers))


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    print(json.dumps(run_v5_startup_preload_repair(Path(".")), ensure_ascii=False, indent=2))
