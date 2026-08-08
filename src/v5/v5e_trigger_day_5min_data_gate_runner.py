from __future__ import annotations

import csv
import json
from bisect import bisect_left
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "current"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
FORMAL_DIR = Path("v5e_formal_validation_forward_packet") / "current"
CASH_DIR = Path("v5e_cash_drag_robustness_packet") / "current"
V5D_GATE_DIR = Path("v5d_baostock_5min_data_gate")
V5D_CURRENT = V5D_GATE_DIR / "current"
V5D_STANDARDIZED_DIR = V5D_GATE_DIR / "data_standardized"
V5D_INDEX = V5D_CURRENT / "v5d_baostock_5min_standardized_index.csv"
V5D_CLOSEOUT = Path("v5d_closeout") / "current" / "v5d_closeout_summary.json"
V5E_STANDARDIZED_INDEX = OUT_DIR / "v5e_exit_5min_standardized_index.csv"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)

MAIN_CANDIDATE = "v5e_combined_main_profit_lock_plus_trailing"
SECONDARY_CANDIDATE = "v5e_profit_lock_main_20pct_sell50"
TARGET_VERSIONS = [MAIN_CANDIDATE, SECONDARY_CANDIDATE]
REQUIRED_FIELDS = ["open", "high", "low", "close", "volume", "amount", "time"]
REQUIRED_BAR_TIMES = ["09:35", "09:40", "10:00", "14:55"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_trigger_day_5min_data_gate(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_exit_5min_blockers.csv", blockers)
        summary = _summary(
            status="blocked_missing_required_input",
            decision="blocked_until_required_inputs_available",
            fatal_blockers=blockers,
        )
        _write_json(out / "v5e_trigger_day_5min_data_gate_summary.json", summary)
        return summary

    exits = _read_df(root / LOOP_DIR / "v5e_exit_action_log.csv")
    trading_days = _trading_days(root)
    code_sleeve = _code_sleeve_map(root)
    minute_index = _minute_index(root)

    requirements = _execution_window_requirements(exits, trading_days, code_sleeve)
    coverage_rows, quality_rows = _coverage_audit(root, requirements, minute_index)
    available_rows = [row for row in coverage_rows if row["coverage_status"] == "available"]
    missing_rows = [row for row in coverage_rows if row["coverage_status"] != "available"]
    fetch_plan = _fetch_plan(requirements, missing_rows)
    fetch_queue = _fetch_queue(missing_rows)
    blockers = _data_blockers(missing_rows)
    reuse_interface = _v5d_reuse_interface(coverage_rows, blockers)
    decision = _pm_decision(coverage_rows)

    _write_csv(out / "v5e_exit_execution_window_requirement.csv", requirements)
    _write_csv(out / "v5e_exit_5min_coverage_audit.csv", coverage_rows)
    _write_csv(out / "v5e_exit_5min_missing_windows.csv", missing_rows)
    _write_csv(out / "v5e_exit_5min_available_windows.csv", available_rows)
    _write_csv(out / "v5e_exit_5min_field_quality_audit.csv", quality_rows)
    _write_csv(out / "v5e_exit_5min_fetch_plan.csv", fetch_plan)
    _write_csv(out / "v5e_exit_5min_fetch_queue.csv", fetch_queue)
    _write_csv(out / "v5e_exit_5min_blockers.csv", blockers)
    _write_csv(out / "v5e_v5d_reuse_interface.csv", reuse_interface)
    (out / "v5e_trigger_day_5min_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        status="completed_trigger_day_5min_execution_data_gate",
        decision=decision,
        fatal_blockers=[],
        requirement_count=len(requirements),
        coverage_rows=coverage_rows,
        available_count=len(available_rows),
        missing_count=len(missing_rows),
        fetch_queue_count=len(fetch_queue),
    )
    _write_json(out / "v5e_trigger_day_5min_data_gate_summary.json", summary)
    (out / "v5e_trigger_day_5min_data_gate_report.md").write_text(
        _report(summary, fetch_plan, blockers),
        encoding="utf-8",
    )
    return summary


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        FORMAL_DIR / "v5e_formal_validation_summary.json",
        CASH_DIR / "v5e_cash_drag_robustness_summary.json",
        CASH_DIR / "v5e_pm_gate_decision.csv",
        CASH_DIR / "v5e_next_agent_queue.csv",
        LOOP_DIR / "v5e_exit_action_log.csv",
        LOOP_DIR / "v5e_trigger_log.csv",
        LOOP_DIR / "v5e_unfilled_log.csv",
        LOOP_DIR / "v5e_cash_drag_log.csv",
        LOOP_DIR / "v5e_variant_metrics.csv",
        V5D_CURRENT / "v5d_baostock_5min_data_gate_summary.json",
        V5D_INDEX,
        V5D_STANDARDIZED_DIR,
        V5D_CLOSEOUT,
        REPAIRED_RUN / "daily_returns.csv",
        REPAIRED_RUN / "rebalance_signals.csv",
    ]
    rows: list[dict[str, Any]] = []
    for path in required:
        if not (root / path).exists():
            rows.append(
                {
                    "blocker_id": "missing_required_input",
                    "severity": "fatal",
                    "status": "blocking",
                    "path": str(path),
                    "description": "Required V5e/V5d/repaired startup input is missing.",
                }
            )
    return rows


def _execution_window_requirements(
    exits: pd.DataFrame,
    trading_days: list[str],
    code_sleeve: dict[str, str],
) -> list[dict[str, Any]]:
    exits = exits[exits["version_id"].isin(TARGET_VERSIONS)].copy()
    exits["execution_date"] = exits["execution_date"].astype(str)
    exits["trigger_date"] = exits["trigger_date"].astype(str)
    rows: list[dict[str, Any]] = []
    for i, row in exits.reset_index(drop=True).iterrows():
        dates = _execution_dates(str(row["execution_date"]), trading_days)
        code = str(row["code"])
        action_id = f"{row['version_id']}|{row['trigger_date']}|{row['execution_date']}|{code}|{i + 1}"
        rows.append(
            {
                "action_id": action_id,
                "version_id": row["version_id"],
                "trigger_date": row["trigger_date"],
                "decision_visible_time": "after_daily_close",
                "execution_date": dates[0],
                "fallback_date_1": dates[1],
                "fallback_date_2": dates[2],
                "code": code,
                "sleeve": code_sleeve.get(code, "unknown"),
                "side": "sell",
                "expected_action": _expected_action(row),
                "required_5min_window": f"{dates[0]}..{dates[2]}",
                "required_fields": ";".join(REQUIRED_FIELDS),
                "required_bar_times": ";".join(REQUIRED_BAR_TIMES + ["last_bar"]),
                "trigger_source": "daily_close_only",
                "minute_trigger_allowed": False,
            }
        )
    return rows


def _execution_dates(execution_date: str, trading_days: list[str]) -> list[str]:
    idx = bisect_left(trading_days, execution_date)
    if idx >= len(trading_days):
        return [execution_date, "", ""]
    if trading_days[idx] != execution_date and idx > 0:
        idx = bisect_left(trading_days, execution_date)
    dates = trading_days[idx : idx + 3]
    while len(dates) < 3:
        dates.append("")
    return dates


def _expected_action(row: pd.Series) -> str:
    amount = _float(row.get("amount", 0.0))
    value = _float(row.get("value", 0.0))
    if amount > 0 or value > 0:
        return "partial_sell_or_full_exit_per_v5e_daily_proxy"
    return "sell_attempt"


def _coverage_audit(
    root: Path,
    requirements: list[dict[str, Any]],
    minute_index: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coverage_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    for req in requirements:
        for window_label, date_col in [
            ("execution_date", "execution_date"),
            ("fallback_date_1", "fallback_date_1"),
            ("fallback_date_2", "fallback_date_2"),
        ]:
            trade_date = str(req[date_col])
            if not trade_date:
                coverage_rows.append(_coverage_row(req, window_label, trade_date, "missing_calendar_date"))
                continue
            index_row = minute_index.get((req["code"], trade_date))
            if not index_row:
                coverage_rows.append(_coverage_row(req, window_label, trade_date, "missing_local_5min_file"))
                quality_rows.append(_quality_missing(req, window_label, trade_date, "file_not_in_v5d_standardized_index"))
                continue
            path = _resolve_path(root, str(index_row["path"]))
            if not path.exists():
                coverage_rows.append(
                    _coverage_row(req, window_label, trade_date, "missing_local_5min_file", path=str(path))
                )
                quality_rows.append(_quality_missing(req, window_label, trade_date, "indexed_file_not_found"))
                continue
            quality = _inspect_minute_file(path)
            quality_row = {
                "action_id": req["action_id"],
                "version_id": req["version_id"],
                "code": req["code"],
                "sleeve": req["sleeve"],
                "window_label": window_label,
                "trade_date": trade_date,
                "path": str(path),
                **quality,
            }
            quality_rows.append(quality_row)
            status = "available" if quality["field_quality_status"] == "pass" else "field_quality_failed"
            coverage_rows.append(
                _coverage_row(
                    req,
                    window_label,
                    trade_date,
                    status,
                    path=str(path),
                    row_count=quality["row_count"],
                    field_quality_status=quality["field_quality_status"],
                    missing_fields=quality["missing_fields"],
                    missing_bar_times=quality["missing_bar_times"],
                    tradability_interpretation=quality["tradability_interpretation"],
                )
            )
    return coverage_rows, quality_rows


def _coverage_row(
    req: dict[str, Any],
    window_label: str,
    trade_date: str,
    status: str,
    path: str = "",
    row_count: int = 0,
    field_quality_status: str = "not_checked",
    missing_fields: str = "",
    missing_bar_times: str = "",
    tradability_interpretation: str = "unknown_missing_data",
) -> dict[str, Any]:
    return {
        "action_id": req["action_id"],
        "version_id": req["version_id"],
        "trigger_date": req["trigger_date"],
        "code": req["code"],
        "sleeve": req["sleeve"],
        "side": "sell",
        "window_label": window_label,
        "trade_date": trade_date,
        "coverage_status": status,
        "path": path,
        "row_count": row_count,
        "required_fields": ";".join(REQUIRED_FIELDS),
        "missing_fields": missing_fields,
        "required_bar_times": ";".join(REQUIRED_BAR_TIMES + ["last_bar"]),
        "missing_bar_times": missing_bar_times,
        "volume_amount_nonempty": status == "available",
        "can_use_for_execution_price_proxy": status == "available",
        "tradability_interpretation": tradability_interpretation,
        "strategy_blocker": False,
        "data_gate_blocker": status != "available",
    }


def _quality_missing(req: dict[str, Any], window_label: str, trade_date: str, reason: str) -> dict[str, Any]:
    return {
        "action_id": req["action_id"],
        "version_id": req["version_id"],
        "code": req["code"],
        "sleeve": req["sleeve"],
        "window_label": window_label,
        "trade_date": trade_date,
        "path": "",
        "field_quality_status": "missing_file",
        "row_count": 0,
        "missing_fields": ";".join(REQUIRED_FIELDS),
        "present_bar_times": "",
        "missing_bar_times": ";".join(REQUIRED_BAR_TIMES + ["last_bar"]),
        "last_bar_time": "",
        "ohlc_positive": False,
        "volume_amount_nonempty": False,
        "volume_amount_nonnegative": False,
        "tradability_interpretation": reason,
    }


def _inspect_minute_file(path: Path) -> dict[str, Any]:
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - defensive audit path
        return {
            "field_quality_status": "read_error",
            "row_count": 0,
            "missing_fields": ";".join(REQUIRED_FIELDS),
            "present_bar_times": "",
            "missing_bar_times": ";".join(REQUIRED_BAR_TIMES + ["last_bar"]),
            "last_bar_time": "",
            "ohlc_positive": False,
            "volume_amount_nonempty": False,
            "volume_amount_nonnegative": False,
            "tradability_interpretation": f"read_error:{exc}",
        }
    missing_fields = [field for field in REQUIRED_FIELDS if field not in df.columns]
    times = set()
    if "time" in df.columns:
        times = {str(value)[:5] for value in df["time"].dropna().tolist()}
    missing_times = [time for time in REQUIRED_BAR_TIMES if time not in times]
    last_bar_time = max(times) if times else ""
    if not last_bar_time:
        missing_times.append("last_bar")
    ohlc_positive = True
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns or not (pd.to_numeric(df[col], errors="coerce") > 0).all():
            ohlc_positive = False
    volume_amount_nonempty = all(
        col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().all()
        for col in ["volume", "amount"]
    )
    volume_amount_nonnegative = all(
        col in df.columns and (pd.to_numeric(df[col], errors="coerce").fillna(-1) >= 0).all()
        for col in ["volume", "amount"]
    )
    zero_volume = "volume" in df.columns and pd.to_numeric(df["volume"], errors="coerce").fillna(0).sum() == 0
    status = "pass"
    if missing_fields or missing_times or not ohlc_positive or not volume_amount_nonempty or not volume_amount_nonnegative:
        status = "fail"
    tradability = "available_for_execution_price_proxy"
    if zero_volume:
        tradability = "zero_volume_possible_suspension_or_no_trade"
        status = "fail"
    return {
        "field_quality_status": status,
        "row_count": int(len(df)),
        "missing_fields": ";".join(missing_fields),
        "present_bar_times": ";".join(sorted(times)),
        "missing_bar_times": ";".join(missing_times),
        "last_bar_time": last_bar_time,
        "ohlc_positive": ohlc_positive,
        "volume_amount_nonempty": volume_amount_nonempty,
        "volume_amount_nonnegative": volume_amount_nonnegative,
        "tradability_interpretation": tradability,
    }


def _fetch_plan(requirements: list[dict[str, Any]], missing_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dates = sorted({row["trade_date"] for row in missing_rows if row["trade_date"]})
    codes = sorted({row["code"] for row in missing_rows})
    all_req_dates = sorted(
        {row[col] for row in requirements for col in ["execution_date", "fallback_date_1", "fallback_date_2"] if row[col]}
    )
    return [
        {
            "plan_id": "v5e_trigger_day_execution_5min_baostock_fetch_plan",
            "source_preference": "BaoStock 5min",
            "frequency": "5min",
            "adjustflag": "3_unadjusted",
            "date_range_all_exit_windows": f"{min(all_req_dates) if all_req_dates else ''}..{max(all_req_dates) if all_req_dates else ''}",
            "missing_date_range": f"{min(dates) if dates else ''}..{max(dates) if dates else ''}",
            "universe_scope": "only_v5e_exit_action_codes_and_execution_fallback_dates",
            "full_holding_period_fetch": False,
            "untriggered_date_fetch": False,
            "involved_stock_count": len(codes),
            "missing_stock_date_tasks": len({(row["code"], row["trade_date"]) for row in missing_rows}),
            "expected_output_raw_dir": "v5e_trigger_day_5min_execution_data_gate/data_raw/",
            "expected_output_standardized_dir": "v5e_trigger_day_5min_execution_data_gate/data_standardized/",
            "retry_policy": "retry_failed_code_date_once_then_record_blocker",
            "blocker_condition": "requires_user_authorization_before_baostock_network_fetch",
            "minute_data_used_for_trigger": False,
        }
    ]


def _fetch_queue(missing_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    for row in sorted(missing_rows, key=lambda r: (r["trade_date"], r["code"])):
        key = (row["code"], row["trade_date"])
        if not row["trade_date"] or key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "queue_id": f"fetch_{len(rows) + 1:05d}",
                "code": row["code"],
                "bs_code": _to_bs_code(row["code"]),
                "fetch_start_date": row["trade_date"],
                "fetch_end_date": row["trade_date"],
                "frequency": "5min",
                "adjustflag": "3_unadjusted",
                "source": "BaoStock",
                "reason": "missing_v5e_exit_execution_window",
                "network_fetch_authorized": False,
                "raw_output_dir": "v5e_trigger_day_5min_execution_data_gate/data_raw/",
                "standardized_output_dir": "v5e_trigger_day_5min_execution_data_gate/data_standardized/",
            }
        )
    return rows


def _data_blockers(missing_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not missing_rows:
        return []
    unique_codes = sorted({row["code"] for row in missing_rows})
    unique_dates = sorted({row["trade_date"] for row in missing_rows if row["trade_date"]})
    return [
        {
            "blocker_id": "missing_v5e_trigger_day_5min_execution_windows",
            "severity": "data_gate",
            "status": "requires_fetch_authorization_before_execution_proxy_test",
            "missing_window_rows": len(missing_rows),
            "missing_stock_date_tasks": len({(row["code"], row["trade_date"]) for row in missing_rows}),
            "missing_stock_count": len(unique_codes),
            "missing_date_count": len(unique_dates),
            "sample_missing_codes": ";".join(unique_codes[:20]),
            "sample_missing_dates": ";".join(unique_dates[:20]),
            "description": "Local V5d BaoStock 5min files do not fully cover V5e exit-action T+1/T+2/T+3 execution windows.",
        }
    ]


def _v5d_reuse_interface(
    coverage_rows: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    available = sum(1 for row in coverage_rows if row["coverage_status"] == "available")
    total = len(coverage_rows)
    return [
        {
            "interface_id": "v5e_daily_exit_to_v5d_execution_governance",
            "v5e_responsibility": "daily_close_exit_trigger_and_T_plus_1_sell_intent",
            "v5d_responsibility": "5min_execution_price_proxy_unfilled_governance_D0_D1_D2_after_exit_signal",
            "minute_data_used_for_trigger": False,
            "reuse_l2_size_aware": True,
            "reuse_l3_default_exception": True,
            "reuse_l4_completion": True,
            "coverage_ready": available == total and total > 0,
            "requires_baostock_fetch_before_reuse": bool(blockers),
            "notes": "Reuse is allowed after trigger-day execution windows are fetched and standardized; no V5d rule change is implied.",
        }
    ]


def _pm_decision(coverage_rows: list[dict[str, Any]]) -> str:
    if not coverage_rows:
        return "blocked_until_required_inputs_available"
    available = sum(1 for row in coverage_rows if row["coverage_status"] == "available")
    if available == len(coverage_rows):
        return "coverage_pass_ready_for_execution_proxy_test"
    if available == 0:
        return "blocked_until_user_authorizes_baostock_fetch"
    return "partial_coverage_generate_fetch_queue"


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    requirement_count: int = 0,
    coverage_rows: list[dict[str, Any]] | None = None,
    available_count: int = 0,
    missing_count: int = 0,
    fetch_queue_count: int = 0,
) -> dict[str, Any]:
    coverage_rows = coverage_rows or []
    total = len(coverage_rows)
    unique_missing_codes = sorted({row["code"] for row in coverage_rows if row["coverage_status"] != "available"})
    unique_missing_dates = sorted({row["trade_date"] for row in coverage_rows if row["coverage_status"] != "available" and row["trade_date"]})
    coverage_rate = (available_count / total) if total else 0.0
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_trigger_day_5min_execution_data_gate",
        "status": status,
        "pm_decision": decision,
        "scope": "trigger_day_execution_windows_only",
        "full_holding_period_checked": False,
        "daily_trigger_unchanged": True,
        "minute_data_used_for_trigger": False,
        "engineering_backtest_run": False,
        "joinquant_started": False,
        "baostock_network_fetch_started": False,
        "accepted": False,
        "v57f_replacement": False,
        "v57f_core_modified": False,
        "erc_modified": False,
        "v5d_modified": False,
        "target_versions": TARGET_VERSIONS,
        "exit_action_count": requirement_count,
        "required_window_rows": total,
        "available_window_rows": available_count,
        "missing_window_rows": missing_count,
        "coverage_rate": coverage_rate,
        "coverage_rate_pct": round(coverage_rate * 100, 4),
        "missing_stock_count": len(unique_missing_codes),
        "missing_date_count": len(unique_missing_dates),
        "sample_missing_codes": unique_missing_codes[:20],
        "sample_missing_dates": unique_missing_dates[:20],
        "fetch_queue_count": fetch_queue_count,
        "requires_user_authorization_for_baostock_fetch": missing_count > 0,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(summary: dict[str, Any], fetch_plan: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> str:
    blocker = blockers[0] if blockers else {}
    plan = fetch_plan[0] if fetch_plan else {}
    return "\n".join(
        [
            "# V5e Trigger-Day 5min Execution Data Gate",
            "",
            "## Scope",
            "- Checked only V5e exit-action execution windows: T+1, T+2, and T+3.",
            "- Did not check full holding-period 5min coverage.",
            "- Did not use 5min bars to trigger V5e exits.",
            "- Did not modify V57f, ERC, or V5d.",
            "",
            "## Coverage",
            f"- Exit actions checked: {summary['exit_action_count']}",
            f"- Required code-date windows: {summary['required_window_rows']}",
            f"- Available windows: {summary['available_window_rows']}",
            f"- Missing windows: {summary['missing_window_rows']}",
            f"- Coverage rate: {summary['coverage_rate_pct']}%",
            f"- PM decision: `{summary['pm_decision']}`",
            "",
            "## Missing Data",
            f"- Missing stock count: {summary['missing_stock_count']}",
            f"- Missing date count: {summary['missing_date_count']}",
            f"- Sample missing codes: {';'.join(summary['sample_missing_codes'])}",
            f"- Sample missing dates: {';'.join(summary['sample_missing_dates'])}",
            "",
            "## Fetch Plan",
            f"- Source: {plan.get('source_preference', '')}",
            f"- Frequency: {plan.get('frequency', '')}",
            f"- Adjust flag: {plan.get('adjustflag', '')}",
            f"- Missing stock-date tasks: {plan.get('missing_stock_date_tasks', 0)}",
            f"- Full holding-period fetch: {plan.get('full_holding_period_fetch', False)}",
            f"- Requires user authorization: {summary['requires_user_authorization_for_baostock_fetch']}",
            "",
            "## Blocker",
            f"- {blocker.get('blocker_id', 'none')}: {blocker.get('status', 'none')}",
            "",
            "## Next Step",
            "Authorize BaoStock 5min fetch for the generated V5e exit-action fetch queue, or keep the daily T+1 open proxy until minute execution evidence is needed.",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Trigger-Day 5min Data Gate Agent Rules",
            "",
            "- Audit only V5e exit-action T+1/T+2/T+3 execution windows.",
            "- Do not fetch full holding-period minute data.",
            "- Do not use 5min bars as profit-lock or trailing triggers.",
            "- Do not change V57f, ERC, V5d, V5e rules, or thresholds.",
            "- Do not run BaoStock network fetch without explicit user authorization.",
            "- Missing minute data is a data-gate blocker for execution proxy testing, not a model-acceptance decision.",
            "- V5e remains a review candidate, not accepted and not live-trading approved.",
            "",
        ]
    )


def _trading_days(root: Path) -> list[str]:
    daily = _read_df(root / REPAIRED_RUN / "daily_returns.csv")
    return sorted(daily["trade_date"].astype(str).unique().tolist())


def _code_sleeve_map(root: Path) -> dict[str, str]:
    signals = _read_df(root / REPAIRED_RUN / "rebalance_signals.csv")
    mapping: dict[str, str] = {}
    if "sector_id" not in signals.columns:
        return mapping
    for code, group in signals.groupby("code"):
        sectors = group["sector_id"].dropna().astype(str)
        mapping[str(code)] = sectors.mode().iloc[0] if not sectors.empty else "unknown"
    return mapping


def _minute_index(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for index_path, date_col in [(root / V5D_INDEX, "rebalance_date"), (root / V5E_STANDARDIZED_INDEX, "trade_date")]:
        if not index_path.exists():
            continue
        index = _read_df(index_path)
        if date_col not in index.columns:
            continue
        for _, row in index.iterrows():
            rows[(str(row["code"]), str(row[date_col]))] = row.to_dict()
    return rows


def _resolve_path(root: Path, path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return root / path


def _to_bs_code(code: str) -> str:
    ticker = code.split(".")[0]
    if code.endswith(".XSHG"):
        return f"sh.{ticker}"
    if code.endswith(".XSHE"):
        return f"sz.{ticker}"
    return code


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5e_trigger_day_5min_data_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
