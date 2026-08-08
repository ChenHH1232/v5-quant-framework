from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5d_baostock_5min_data_gate import normalize_baostock_frame


OUT_DIR = Path("v5f_spike_funded_mr_borrowing_independent_validation_gate") / "current"
RAW_DIR = Path("v5f_spike_funded_mr_borrowing_independent_validation_gate") / "data_raw" / "2020q4"
STD_DIR = Path("v5f_spike_funded_mr_borrowing_independent_validation_gate") / "data_standardized" / "2020q4"

BORROWING_SUMMARY = (
    Path("v5f_event_triggered_mean_reversion_borrowing_test")
    / "current"
    / "v5f_mr_borrowing_summary.json"
)
BORROWING_POLICY = (
    Path("v5f_event_triggered_mean_reversion_borrowing_test")
    / "current"
    / "v5f_mr_borrowing_funding_policy_comparison.csv"
)
PRE2021_GATE_SUMMARY = (
    Path("v5f_pre2021_repaired_multisleeve_data_gate")
    / "current"
    / "v5f_pre2021_data_gate_summary.json"
)
PRE2021_CANDIDATES = (
    Path("v5f_pre2021_repaired_multisleeve_data_gate")
    / "current"
    / "v5f_pre2021_candidate_signal_preview.csv"
)
PRE2021_BAOSTOCK_PROBE = (
    Path("v5f_pre2021_repaired_multisleeve_data_gate")
    / "current"
    / "v5f_baostock_2014_2020_5min_probe.csv"
)
WALK_FORWARD_SUMMARY = (
    Path("v5f_short_window_reversion_walk_forward_robustness")
    / "current"
    / "v5f_walk_forward_summary.json"
)
V5G05_SUMMARY = (
    Path("v5g_05_short_window_reversion_independent_validation_gate")
    / "current"
    / "v5g_05_short_window_validation_gate_summary.json"
)

VALIDATION_START = "2020-10-09"
VALIDATION_END = "2020-12-31"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003
BORROW_INTENSITY = 0.10
CAPS = [0.02, 0.05, 0.10]
HORIZONS = ["next1", "next2"]
POLICIES = ["spike_only_strict", "paired_drop_spike_net0", "pro_rata_non_drop"]
DROP_ABS_CUT = -0.01
SPIKE_ABS_CUT = 0.01

REQUIRED_INPUTS = [
    BORROWING_SUMMARY,
    BORROWING_POLICY,
    PRE2021_GATE_SUMMARY,
    PRE2021_CANDIDATES,
    PRE2021_BAOSTOCK_PROBE,
    WALK_FORWARD_SUMMARY,
]


def run_v5f_spike_funded_mr_borrowing_independent_validation_gate(
    root: Path = Path("."),
    *,
    allow_baostock_fetch: bool = True,
) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (root / RAW_DIR).mkdir(parents=True, exist_ok=True)
    (root / STD_DIR).mkdir(parents=True, exist_ok=True)

    missing = _missing_inputs(root)
    if missing:
        summary = _summary(
            "blocked_missing_required_input",
            "blocked_by_missing_required_input",
            missing,
        )
        _write_minimal(out, summary, missing)
        return summary

    borrowing_summary = _read_json(root / BORROWING_SUMMARY)
    pre2021_summary = _read_json(root / PRE2021_GATE_SUMMARY)
    walk_forward_summary = _read_json(root / WALK_FORWARD_SUMMARY)
    v5g05_summary = _read_optional_json(root / V5G05_SUMMARY)
    candidates = _validation_candidates(root)
    fetch_log = _ensure_minute_data(root, candidates, allow_baostock_fetch)
    features = _feature_panel(root, candidates, fetch_log)
    event_log, trade_log = _event_and_trade_logs(features)
    metrics = _validation_metrics(trade_log, features)
    policy = _policy_comparison(metrics, trade_log)
    sleeve = _sleeve_stability(trade_log)
    source_audit = _source_audit(
        borrowing_summary,
        pre2021_summary,
        walk_forward_summary,
        v5g05_summary,
        candidates,
        fetch_log,
        features,
    )
    governance = _governance_audit(source_audit, features, metrics)
    gaps = _validation_gaps(pre2021_summary, source_audit)
    decision = _pm_decision(metrics, governance, gaps)
    blockers = _blockers(governance, gaps)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])

    _write_csv(out / "v5f_spike_mr_validation_source_audit.csv", source_audit)
    _write_csv(out / "v5f_spike_mr_validation_2020q4_fetch_log.csv", fetch_log)
    _write_csv(out / "v5f_spike_mr_validation_feature_panel.csv", features)
    _write_csv(out / "v5f_spike_mr_validation_event_log.csv", event_log)
    _write_csv(out / "v5f_spike_mr_validation_trade_log.csv", trade_log)
    _write_csv(out / "v5f_spike_mr_validation_metrics.csv", metrics)
    _write_csv(out / "v5f_spike_mr_validation_funding_policy_comparison.csv", policy)
    _write_csv(out / "v5f_spike_mr_validation_sleeve_stability.csv", sleeve)
    _write_csv(out / "v5f_spike_mr_validation_governance_audit.csv", governance)
    _write_csv(out / "v5f_spike_mr_validation_gap_register.csv", gaps)
    _write_csv(out / "v5f_spike_mr_validation_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_spike_mr_validation_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_spike_mr_validation_blockers.csv", blockers)
    (out / "v5f_spike_mr_validation_report.md").write_text(
        _report(metrics, policy, sleeve, source_audit, decision, gaps),
        encoding="utf-8",
    )
    (out / "v5f_spike_mr_validation_agent_execution_rules.md").write_text(
        _rules(),
        encoding="utf-8",
    )

    best = metrics[0] if metrics else {}
    positive_limited = bool(
        best
        and float(best.get("net_incremental_return_pct_points", 0.0) or 0.0) > 0
        and float(best.get("win_rate", 0.0) or 0.0) >= 0.5
    )
    summary = _summary(
        "completed_v5f_spike_funded_mr_borrowing_independent_validation_gate",
        decision[0]["pm_gate_decision"],
        [],
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        validation_window_start=VALIDATION_START,
        validation_window_end=VALIDATION_END,
        validation_window_classification="pre2021_limited_independent_micro_validation_not_full_v57f_equivalent",
        independent_validation_pass=False,
        limited_2020q4_directional_pass=positive_limited,
        formal_promotion_allowed=False,
        accepted=False,
        live_trading_approved=False,
        v57f_core_modified=False,
        threshold_scan_used=False,
        full_market_selection_used=False,
        new_buy_signal_used=False,
        baostock_fetch_started=any(row.get("fetch_started") is True for row in fetch_log),
        candidate_count=len(candidates),
        feature_row_count=len(features),
        event_group_count=len(event_log),
        trade_group_count=len(trade_log),
        best_variant=best.get("version_id", ""),
        best_policy=best.get("funding_policy", ""),
        best_horizon=best.get("borrow_horizon", ""),
        best_net_incremental_return_pct_points=float(best.get("net_incremental_return_pct_points", 0.0) or 0.0),
        best_win_rate=float(best.get("win_rate", 0.0) or 0.0),
        blocker_count=len([row for row in blockers if row.get("status") != "not_blocking"]),
        validation_gap_count=len([row for row in gaps if row.get("blocks_formal_promotion") is True]),
    )
    _write_json(out / "v5f_spike_mr_validation_summary.json", summary)
    return summary


def _validation_candidates(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / PRE2021_CANDIDATES, dtype={"preview_date": str, "code": str})
    df = df[df["preview_date"].astype(str).eq(VALIDATION_START)].copy()
    if df.empty:
        return []
    df["target_weight"] = 1.0 / len(df)
    df["bs_code"] = df["code"].map(_jq_to_bs)
    return df[
        [
            "preview_date",
            "code",
            "bs_code",
            "sector_id",
            "selected_rank",
            "score",
            "target_weight",
            "preview_status",
            "governance_note",
        ]
    ].rename(columns={"preview_date": "validation_start_date", "sector_id": "sleeve"}).to_dict("records")


def _ensure_minute_data(root: Path, candidates: list[dict[str, Any]], allow_fetch: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    missing = [
        item
        for item in candidates
        if not _std_path(root, str(item["code"])).exists()
    ]
    if missing and allow_fetch:
        rows.extend(_fetch_baostock(root, missing))
    for item in candidates:
        code = str(item["code"])
        path = _std_path(root, code)
        row_count = 0
        status = "missing"
        if path.exists():
            try:
                row_count = len(pd.read_csv(path, usecols=["trade_date"]))
                status = "pass" if row_count else "empty"
            except Exception as exc:
                status = "read_error"
                rows.append(
                    {
                        "code": code,
                        "bs_code": item["bs_code"],
                        "fetch_start_date": VALIDATION_START,
                        "fetch_end_date": VALIDATION_END,
                        "status": status,
                        "row_count": 0,
                        "standardized_path": str(path.relative_to(root)),
                        "fetch_started": False,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:300],
                    }
                )
                continue
        if not any(str(row.get("code")) == code for row in rows):
            rows.append(
                {
                    "code": code,
                    "bs_code": item["bs_code"],
                    "fetch_start_date": VALIDATION_START,
                    "fetch_end_date": VALIDATION_END,
                    "status": status,
                    "row_count": row_count,
                    "standardized_path": str(path.relative_to(root)) if path.exists() else "",
                    "fetch_started": False,
                    "error_type": "" if status == "pass" else status,
                    "error_message": "",
                }
            )
    return sorted(rows, key=lambda row: str(row["code"]))


def _fetch_baostock(root: Path, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        import baostock as bs
    except Exception as exc:
        return [
            {
                "code": item["code"],
                "bs_code": item["bs_code"],
                "fetch_start_date": VALIDATION_START,
                "fetch_end_date": VALIDATION_END,
                "status": "baostock_import_failed",
                "row_count": 0,
                "standardized_path": "",
                "fetch_started": False,
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:300],
            }
            for item in candidates
        ]
    login = bs.login()
    if getattr(login, "error_code", "1") != "0":
        return [
            {
                "code": item["code"],
                "bs_code": item["bs_code"],
                "fetch_start_date": VALIDATION_START,
                "fetch_end_date": VALIDATION_END,
                "status": "baostock_login_failed",
                "row_count": 0,
                "standardized_path": "",
                "fetch_started": False,
                "error_type": getattr(login, "error_code", ""),
                "error_message": getattr(login, "error_msg", "")[:300],
            }
            for item in candidates
        ]
    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    rows: list[dict[str, Any]] = []
    try:
        for item in candidates:
            started = time.perf_counter()
            code = str(item["code"])
            bs_code = str(item["bs_code"])
            raw_path = _raw_path(root, code)
            std_path = _std_path(root, code)
            status = "error"
            row_count = 0
            error_type = ""
            error_message = ""
            try:
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    fields,
                    start_date=VALIDATION_START,
                    end_date=VALIDATION_END,
                    frequency="5",
                    adjustflag="3",
                )
                raw_rows: list[list[str]] = []
                while rs.error_code == "0" and rs.next():
                    raw_rows.append(rs.get_row_data())
                if rs.error_code != "0":
                    status = "query_error"
                    error_type = str(rs.error_code)
                    error_message = str(rs.error_msg)[:300]
                else:
                    raw_df = pd.DataFrame(raw_rows, columns=rs.fields)
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    std_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
                    std_df = normalize_baostock_frame(raw_df, code, bs_code, VALIDATION_START, VALIDATION_END)
                    std_df.to_csv(std_path, index=False, encoding="utf-8-sig")
                    row_count = int(len(std_df))
                    status = "pass" if row_count else "empty"
            except Exception as exc:  # pragma: no cover - external API defensive path
                error_type = type(exc).__name__
                error_message = str(exc)[:300]
            rows.append(
                {
                    "code": code,
                    "bs_code": bs_code,
                    "fetch_start_date": VALIDATION_START,
                    "fetch_end_date": VALIDATION_END,
                    "status": status,
                    "row_count": row_count,
                    "raw_path": str(raw_path.relative_to(root)) if raw_path.exists() else "",
                    "standardized_path": str(std_path.relative_to(root)) if std_path.exists() else "",
                    "fetch_started": True,
                    "elapsed_sec": round(time.perf_counter() - started, 3),
                    "error_type": error_type,
                    "error_message": error_message,
                }
            )
    finally:
        try:
            bs.logout()
        except Exception:
            pass
    return rows


def _feature_panel(root: Path, candidates: list[dict[str, Any]], fetch_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate_by_code = {str(item["code"]): item for item in candidates}
    ok_codes = {
        str(row["code"])
        for row in fetch_log
        if str(row.get("status")) == "pass"
    }
    rows: list[dict[str, Any]] = []
    for code in sorted(ok_codes):
        path = _std_path(root, code)
        if not path.exists():
            continue
        item = candidate_by_code[code]
        df = pd.read_csv(path, dtype={"trade_date": str, "time": str})
        if df.empty:
            continue
        for col in ["open", "high", "low", "close", "volume", "amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        for trade_date, day in df.groupby("trade_date", sort=True):
            parsed = _parse_minute_day(day)
            if not parsed:
                continue
            parsed.update(
                {
                    "trade_date": str(trade_date),
                    "code": code,
                    "sleeve": str(item["sleeve"]),
                    "selected_rank": item["selected_rank"],
                    "score": item["score"],
                    "target_weight": item["target_weight"],
                    "validation_pool": "pre2021_2020q4_repaired_multisleeve_candidate_preview",
                    "full_v57f_equivalent": False,
                    "new_buy_signal_used": False,
                    "accepted": False,
                }
            )
            rows.append(parsed)
    if not rows:
        return []
    df = pd.DataFrame(rows).sort_values(["code", "trade_date"]).reset_index(drop=True)
    enriched: list[pd.DataFrame] = []
    for _, group in df.groupby("code", sort=True):
        group = group.sort_values("trade_date").reset_index(drop=True)
        group["next_day_close"] = group["day_close"].shift(-1)
        group["next_2d_close"] = group["day_close"].shift(-2)
        group["next1_date"] = group["trade_date"].shift(-1)
        group["next2_date"] = group["trade_date"].shift(-2)
        group["next1_from_1000"] = group.apply(lambda row: _ret(row["next_day_close"], row["close_1000"]), axis=1)
        group["next2_from_1000"] = group.apply(lambda row: _ret(row["next_2d_close"], row["close_1000"]), axis=1)
        enriched.append(group)
    df = pd.concat(enriched, ignore_index=True)
    df["is_drop_abs"] = pd.to_numeric(df["r_0935_1000"], errors="coerce") <= DROP_ABS_CUT
    df["is_spike_abs"] = pd.to_numeric(df["r_0935_1000"], errors="coerce") >= SPIKE_ABS_CUT
    return df.to_dict("records")


def _parse_minute_day(day: pd.DataFrame) -> dict[str, Any]:
    day = day.sort_values("time").reset_index(drop=True)
    by_time = {str(row["time"]): row for _, row in day.iterrows()}
    close_0935 = _time_close(by_time, "09:35:00")
    close_1000 = _time_close(by_time, "10:00:00")
    amount = pd.to_numeric(day["amount"], errors="coerce").fillna(0.0)
    volume = pd.to_numeric(day["volume"], errors="coerce").fillna(0.0)
    vwap = float(amount.sum() / volume.sum()) if volume.sum() else _safe_float(day.iloc[-1]["close"])
    return {
        "bar_count": int(len(day)),
        "first_bar_time": str(day.iloc[0]["time"]),
        "last_bar_time": str(day.iloc[-1]["time"]),
        "day_open": _safe_float(day.iloc[0]["open"]),
        "day_close": _safe_float(day.iloc[-1]["close"]),
        "close_0935": close_0935,
        "close_1000": close_1000,
        "close_1455": _time_close(by_time, "14:55:00"),
        "vwap": vwap,
        "r_0935_1000": _ret(close_1000, close_0935),
    }


def _event_and_trade_logs(features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not features:
        return [], []
    df = pd.DataFrame(features)
    rows: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    for (trade_date, sleeve), group in df.groupby(["trade_date", "sleeve"], sort=True):
        for horizon in HORIZONS:
            ret_col = f"{horizon}_from_1000"
            close_col = f"{horizon}_date"
            drops = group[group["is_drop_abs"] & group[ret_col].notna() & group[close_col].notna()].copy()
            if drops.empty:
                continue
            sleeve_total = float(pd.to_numeric(group["target_weight"], errors="coerce").fillna(0.0).sum())
            desired_by_drop = pd.to_numeric(drops["target_weight"], errors="coerce").fillna(0.0) * BORROW_INTENSITY
            desired_total = float(desired_by_drop.sum())
            for policy_name in POLICIES:
                for cap in CAPS:
                    trade = _single_trade_group(
                        group,
                        drops,
                        desired_by_drop,
                        policy_name,
                        cap,
                        horizon,
                        ret_col,
                        close_col,
                        sleeve_total,
                    )
                    rows.append(
                        {
                            "event_group_id": f"{policy_name}|cap{int(cap*100)}|{horizon}|{trade_date}|{sleeve}",
                            "trade_date": trade_date,
                            "sleeve": sleeve,
                            "funding_policy": policy_name,
                            "borrow_cap_pct_of_sleeve": cap,
                            "borrow_horizon": horizon,
                            "drop_event_count": int(len(drops)),
                            "spike_source_count": int((group["is_spike_abs"] & ~group["code"].astype(str).isin(set(drops["code"].astype(str)))).sum()),
                            "desired_borrow_weight": desired_total,
                            "actual_borrow_weight": trade["actual_borrow_weight"] if trade else 0.0,
                            "event_executed": trade is not None,
                            "skip_reason": "" if trade else "no_eligible_same_sleeve_funding_source_or_missing_return",
                            "drop_threshold_source": "fixed_abs_minus_1pct_no_training",
                            "spike_threshold_source": "fixed_abs_plus_1pct_no_training",
                            "fixed_budget_reserved": False,
                            "same_sleeve_only": True,
                            "accepted": False,
                        }
                    )
                    if trade:
                        trades.append(trade)
    return rows, trades


def _single_trade_group(
    group: pd.DataFrame,
    drops: pd.DataFrame,
    desired_by_drop: pd.Series,
    policy_name: str,
    cap: float,
    horizon: str,
    ret_col: str,
    close_col: str,
    sleeve_total: float,
) -> dict[str, Any] | None:
    drop_codes = set(drops["code"].astype(str))
    not_drop = ~group["code"].astype(str).isin(drop_codes)
    if policy_name in {"spike_only_strict", "paired_drop_spike_net0"}:
        sources = group[not_drop & group["is_spike_abs"] & group[ret_col].notna()].copy()
    elif policy_name == "pro_rata_non_drop":
        sources = group[not_drop & ~group["is_drop_abs"] & group[ret_col].notna()].copy()
    else:
        sources = pd.DataFrame()
    if sources.empty:
        return None
    desired_total = float(desired_by_drop.sum())
    source_available = float(pd.to_numeric(sources["target_weight"], errors="coerce").fillna(0.0).sum()) * BORROW_INTENSITY
    group_cap = cap * sleeve_total
    actual_borrow = min(desired_total, source_available, group_cap)
    if actual_borrow <= 0:
        return None
    target_weights = desired_by_drop * (actual_borrow / desired_total)
    target_avg_return = float((target_weights * pd.to_numeric(drops[ret_col], errors="coerce")).sum() / target_weights.sum())
    funding_avg_return = _weighted_return(sources, ret_col)
    if funding_avg_return is None:
        return None
    gross = actual_borrow * (target_avg_return - funding_avg_return)
    commission = actual_borrow * COMMISSION_RATE * 2.0
    net = gross - commission
    version = f"independent2020q4_{policy_name}_cap{int(cap*100)}_{horizon}"
    return {
        "version_id": version,
        "funding_policy": policy_name,
        "borrow_cap_pct_of_sleeve": cap,
        "borrow_horizon": horizon,
        "open_date": str(group.iloc[0]["trade_date"]),
        "close_date": _mode_date(drops[close_col]),
        "sleeve": str(group.iloc[0]["sleeve"]),
        "drop_event_count": int(len(drops)),
        "funding_source_count": int(len(sources)),
        "target_avg_return": target_avg_return,
        "funding_avg_return": funding_avg_return,
        "desired_borrow_weight": desired_total,
        "actual_borrow_weight": actual_borrow,
        "gross_incremental_return": gross,
        "commission_drag": commission,
        "net_incremental_return": net,
        "same_sleeve_funding": True,
        "temporary_borrow": True,
        "fixed_budget_reserved": False,
        "new_buy_signal_used": False,
        "accepted": False,
    }


def _validation_metrics(trades: list[dict[str, Any]], features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    feature_df = pd.DataFrame(features)
    feature_days = int(feature_df["trade_date"].nunique()) if not feature_df.empty else 0
    rows: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        net = pd.to_numeric(group["net_incremental_return"], errors="coerce")
        spread = pd.to_numeric(group["target_avg_return"], errors="coerce") - pd.to_numeric(group["funding_avg_return"], errors="coerce")
        rows.append(
            {
                "version_id": version,
                "funding_policy": str(group.iloc[0]["funding_policy"]),
                "borrow_cap_pct_of_sleeve": group.iloc[0]["borrow_cap_pct_of_sleeve"],
                "borrow_horizon": str(group.iloc[0]["borrow_horizon"]),
                "validation_window": "2020Q4",
                "feature_day_count": feature_days,
                "trade_group_count": int(len(group)),
                "active_borrow_days": int(group["open_date"].nunique()),
                "sleeve_count": int(group["sleeve"].nunique()),
                "net_incremental_return_sum": float(net.sum()),
                "net_incremental_return_pct_points": float(net.sum() * 100),
                "avg_target_minus_funding_return": float(spread.mean()),
                "median_target_minus_funding_return": float(spread.median()),
                "win_rate": float((net > 0).mean()) if len(net) else 0.0,
                "total_actual_borrow_weight": float(pd.to_numeric(group["actual_borrow_weight"], errors="coerce").sum()),
                "fixed_budget_reserved": False,
                "same_sleeve_only": True,
                "formal_independent_pass": False,
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda row: float(row["net_incremental_return_pct_points"]), reverse=True)


def _policy_comparison(metrics: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in metrics:
        rows.append(
            {
                "version_id": row["version_id"],
                "funding_policy": row["funding_policy"],
                "borrow_horizon": row["borrow_horizon"],
                "borrow_cap_pct_of_sleeve": row["borrow_cap_pct_of_sleeve"],
                "trade_group_count": row["trade_group_count"],
                "net_incremental_return_pct_points": row["net_incremental_return_pct_points"],
                "win_rate": row["win_rate"],
                "reading": _metric_reading(row),
            }
        )
    return rows


def _sleeve_stability(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows: list[dict[str, Any]] = []
    for (version, sleeve), group in df.groupby(["version_id", "sleeve"], sort=True):
        net = pd.to_numeric(group["net_incremental_return"], errors="coerce")
        rows.append(
            {
                "version_id": version,
                "funding_policy": str(group.iloc[0]["funding_policy"]),
                "borrow_horizon": str(group.iloc[0]["borrow_horizon"]),
                "sleeve": sleeve,
                "trade_group_count": int(len(group)),
                "active_borrow_days": int(group["open_date"].nunique()),
                "net_incremental_return_pct_points": float(net.sum() * 100),
                "win_rate": float((net > 0).mean()) if len(net) else 0.0,
                "stability_read": "positive" if float(net.sum()) > 0 else "negative_or_flat",
            }
        )
    return sorted(rows, key=lambda row: float(row["net_incremental_return_pct_points"]), reverse=True)


def _source_audit(
    borrowing_summary: dict[str, Any],
    pre2021_summary: dict[str, Any],
    walk_forward_summary: dict[str, Any],
    v5g05_summary: dict[str, Any],
    candidates: list[dict[str, Any]],
    fetch_log: list[dict[str, Any]],
    features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fetch_pass = sum(1 for row in fetch_log if row.get("status") == "pass")
    fetch_total = len(fetch_log)
    feature_dates = sorted({str(row.get("trade_date")) for row in features})
    return [
        {
            "source_id": "v5f_event_triggered_borrowing_backtest_scope",
            "status": "available_positive_in_sample",
            "observed": borrowing_summary.get("best_delta_return_pct_points_vs_champion", ""),
            "classification": "2021_2026_backtest_scope_not_oos",
        },
        {
            "source_id": "v5f_short_window_walk_forward",
            "status": "available_internal_diagnostic",
            "observed": walk_forward_summary.get("pm_gate_decision", ""),
            "classification": "internal_rolling_diagnostic_not_oos",
        },
        {
            "source_id": "pre2021_repaired_multisleeve_pool",
            "status": pre2021_summary.get("pre2021_multisleeve_pool_status", ""),
            "observed": pre2021_summary.get("candidate_signal_preview_count", ""),
            "classification": "pre2021_candidate_preview_not_full_v57f_equivalent",
        },
        {
            "source_id": "pre2021_baostock_5min",
            "status": pre2021_summary.get("baostock_2014_2020_status", ""),
            "observed": pre2021_summary.get("baostock_probe_pass_count", ""),
            "classification": "2020_available_pre2020_not_confirmed",
        },
        {
            "source_id": "v5g05_independent_gate_prior",
            "status": v5g05_summary.get("pm_gate_decision", "not_available"),
            "observed": v5g05_summary.get("independent_validation_pass", ""),
            "classification": "prior_gate_blocks_promotion_if_independent_sample_missing",
        },
        {
            "source_id": "this_2020q4_candidate_pool",
            "status": "available" if candidates else "missing",
            "observed": len(candidates),
            "classification": "pre2021_limited_candidate_preview",
        },
        {
            "source_id": "this_2020q4_minute_fetch",
            "status": "pass" if fetch_total and fetch_pass == fetch_total else "partial_or_missing",
            "observed": f"{fetch_pass}/{fetch_total}",
            "classification": "limited_2020q4_minute_validation",
        },
        {
            "source_id": "this_2020q4_feature_panel",
            "status": "pass" if features else "missing",
            "observed": f"{len(features)} rows; {feature_dates[0] if feature_dates else ''} to {feature_dates[-1] if feature_dates else ''}",
            "classification": "limited_2020q4_feature_panel",
        },
    ]


def _governance_audit(
    source_audit: list[dict[str, Any]],
    features: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fetch_ok = next((row for row in source_audit if row["source_id"] == "this_2020q4_minute_fetch"), {}).get("status") == "pass"
    feature_ok = bool(features)
    metrics_ok = bool(metrics)
    return [
        {"audit_id": "backtest_scope_not_used_as_oos", "status": "pass", "detail": "2021-05-01 to 2026-05-31 remains historical backtest scope."},
        {"audit_id": "validation_window_pre2021", "status": "pass", "detail": f"{VALIDATION_START} to {VALIDATION_END}"},
        {"audit_id": "minute_fetch_coverage", "status": "pass" if fetch_ok else "fail", "detail": fetch_ok},
        {"audit_id": "feature_panel_nonempty", "status": "pass" if feature_ok else "fail", "detail": len(features)},
        {"audit_id": "metrics_nonempty", "status": "pass" if metrics_ok else "fail", "detail": len(metrics)},
        {"audit_id": "fixed_abs_threshold_no_training", "status": "pass", "detail": "Uses fixed +/-1% shock because 2019 5min thresholds are unavailable."},
        {"audit_id": "same_sleeve_only", "status": "pass", "detail": True},
        {"audit_id": "no_fixed_mean_reversion_budget", "status": "pass", "detail": True},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": True},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": True},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _validation_gaps(pre2021_summary: dict[str, Any], source_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "gap_id": "pre2020_5min_not_confirmed",
            "status": "open",
            "blocks_formal_promotion": True,
            "detail": pre2021_summary.get("baostock_2014_2020_status", ""),
        },
        {
            "gap_id": "only_one_pre2021_validation_cycle",
            "status": "open",
            "blocks_formal_promotion": True,
            "detail": "Only 2020Q4 candidate preview can be minute-tested from current local evidence.",
        },
        {
            "gap_id": "pre2021_preview_not_full_v57f_equivalent",
            "status": "open",
            "blocks_formal_promotion": True,
            "detail": "Pre-2021 repaired pool is a candidate preview; full V57f baseline NAV equivalence is not achieved.",
        },
        {
            "gap_id": "prior_year_sleeve_threshold_unavailable_for_2020",
            "status": "open",
            "blocks_formal_promotion": True,
            "detail": "2019 5min bars are unavailable from BaoStock probe; used fixed absolute shock floor instead of trained prior-year same-sleeve threshold.",
        },
    ]


def _pm_decision(
    metrics: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failed = [row for row in governance if row.get("status") == "fail"]
    best = metrics[0] if metrics else {}
    best_net = float(best.get("net_incremental_return_pct_points", 0.0) or 0.0)
    best_win = float(best.get("win_rate", 0.0) or 0.0)
    formal_gaps = [row for row in gaps if row.get("blocks_formal_promotion") is True]
    if failed:
        decision = "blocked_by_pre2021_minute_data_or_feature_issue"
        validation_pass = False
        verdict = "blocked"
    elif best_net > 0 and best_win >= 0.5:
        decision = "limited_2020q4_positive_keep_forward_validation_not_candidate"
        validation_pass = False
        verdict = "directionally_positive_but_not_formal_independent_pass"
    else:
        decision = "limited_2020q4_negative_or_mixed_keep_diagnostic"
        validation_pass = False
        verdict = "not_stable_enough"
    return [
        {
            "pm_gate_decision": decision,
            "independent_validation_pass": validation_pass,
            "formal_promotion_allowed": False,
            "limited_2020q4_best_variant": best.get("version_id", ""),
            "limited_2020q4_best_net_incremental_return_pct_points": best_net,
            "limited_2020q4_best_win_rate": best_win,
            "formal_gap_count": len(formal_gaps),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "verdict": verdict,
            "next_step": "continue_forward_paper_or_source_full_pre2021_5min_before_candidate_review",
        }
    ]


def _blockers(governance: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "blocker_id": row["audit_id"],
            "severity": "fatal",
            "status": "blocking",
            "detail": row["detail"],
        }
        for row in governance
        if row.get("status") == "fail"
    ]
    rows.extend(
        {
            "blocker_id": row["gap_id"],
            "severity": "research",
            "status": "blocking_formal_promotion",
            "detail": row["detail"],
        }
        for row in gaps
        if row.get("blocks_formal_promotion") is True
    )
    if rows:
        return rows
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "detail": "No blocker."}]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "keep_internal_subsleeve_mom12_70_30_primary_forward_paper",
            "allowed": True,
            "reason": "Primary V5f model remains the validated value-momentum champion.",
        },
        {
            "priority": 2,
            "next_task": "v5f_spike_funded_mr_borrowing_forward_paper_observation",
            "allowed": decision == "limited_2020q4_positive_keep_forward_validation_not_candidate",
            "reason": "Use future real signals to accumulate independent observations without accepting the rule.",
        },
        {
            "priority": 3,
            "next_task": "source_pre2020_5min_for_full_pre2021_validation",
            "allowed": True,
            "reason": "Needed before formal candidate review of short-window borrowing.",
        },
        {
            "priority": 4,
            "next_task": "promote_spike_funded_borrowing_to_candidate",
            "allowed": False,
            "reason": "Formal independent validation has not passed.",
        },
    ]


def _report(
    metrics: list[dict[str, Any]],
    policy: list[dict[str, Any]],
    sleeve: list[dict[str, Any]],
    source_audit: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> str:
    best = metrics[0] if metrics else {}
    lines = [
        "# V5f Spike-Funded MR Borrowing Independent Validation Gate",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Formal independent validation pass: `{decision[0]['independent_validation_pass']}`",
        f"- Limited validation window: `{VALIDATION_START}` to `{VALIDATION_END}`.",
        "- Backtest window `2021-05-01` to `2026-05-31` is not treated as OOS.",
        "- Status: not accepted; not live approved; V57f core unchanged.",
        "",
        "## Limited 2020Q4 Result",
        "",
        f"- Best variant: `{best.get('version_id', '')}`",
        f"- Best net incremental return: `{float(best.get('net_incremental_return_pct_points', 0.0) or 0.0):.4f}` pct points.",
        f"- Best win rate: `{float(best.get('win_rate', 0.0) or 0.0):.2%}`.",
        "",
        "## Top Policies",
        "",
    ]
    for row in policy[:8]:
        lines.append(
            f"- `{row['version_id']}`: net `{float(row['net_incremental_return_pct_points']):.4f}` pct, win `{float(row['win_rate']):.2%}`, trades `{row['trade_group_count']}`, reading `{row['reading']}`."
        )
    lines.extend(["", "## Sleeve Stability", ""])
    for row in sleeve[:8]:
        lines.append(
            f"- `{row['version_id']}` / `{row['sleeve']}`: net `{float(row['net_incremental_return_pct_points']):.4f}` pct, win `{float(row['win_rate']):.2%}`."
        )
    lines.extend(["", "## Evidence Level", ""])
    for row in source_audit:
        lines.append(f"- `{row['source_id']}`: `{row['status']}` / {row['classification']} / observed `{row['observed']}`.")
    lines.extend(["", "## Open Gaps", ""])
    for row in gaps:
        lines.append(f"- `{row['gap_id']}`: {row['detail']}")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Spike-Funded MR Borrowing Validation Rules",
            "",
            "- Do not use 2021-05-01 to 2026-05-31 as OOS validation.",
            "- Use only V57f repaired/pre-2021 candidate pool; no full-market selection.",
            "- Borrow only from same-sleeve spike names into same-sleeve drop names.",
            "- No fixed mean-reversion budget, no new buy signal, no V57f core change.",
            "- 2020Q4 is a limited micro-validation, not a full independent pass.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _metric_reading(row: dict[str, Any]) -> str:
    net = float(row.get("net_incremental_return_pct_points", 0.0) or 0.0)
    win = float(row.get("win_rate", 0.0) or 0.0)
    if net > 0 and win >= 0.5:
        return "directionally_positive_limited_sample"
    if net > 0:
        return "positive_sum_low_win_rate"
    return "negative_or_flat"


def _time_close(by_time: dict[str, Any], target: str) -> float | None:
    if target in by_time:
        return _safe_float(by_time[target]["close"])
    available = sorted(time_value for time_value in by_time if time_value <= target)
    if not available:
        return None
    return _safe_float(by_time[available[-1]]["close"])


def _ret(end: Any, start: Any) -> float | None:
    end_value = _safe_float(end)
    start_value = _safe_float(start)
    if end_value is None or start_value in (None, 0.0):
        return None
    return end_value / start_value - 1.0


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
        if pd.isna(out):
            return None
        return out
    except Exception:
        return None


def _weighted_return(df: pd.DataFrame, ret_col: str) -> float | None:
    tmp = df[df[ret_col].notna()].copy()
    if tmp.empty:
        return None
    weights = pd.to_numeric(tmp["target_weight"], errors="coerce").fillna(0.0)
    returns = pd.to_numeric(tmp[ret_col], errors="coerce")
    if float(weights.sum()) == 0.0:
        return float(returns.mean())
    return float((weights * returns).sum() / weights.sum())


def _mode_date(series: pd.Series) -> str:
    mode = series.dropna().astype(str).mode()
    return str(mode.iloc[0]) if len(mode) else ""


def _raw_path(root: Path, code: str) -> Path:
    return root / RAW_DIR / f"{code.replace('.', '_')}_5min_raw.csv"


def _std_path(root: Path, code: str) -> Path:
    return root / STD_DIR / f"{code.replace('.', '_')}_5min_standardized.csv"


def _jq_to_bs(code: str) -> str:
    plain = code.split(".")[0]
    if code.endswith(".XSHG"):
        return f"sh.{plain}"
    if code.endswith(".XSHE"):
        return f"sz.{plain}"
    raise ValueError(f"Unsupported code format: {code}")


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
        }
        for path in REQUIRED_INPUTS
        if not (root / path).exists()
    ]


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_spike_funded_mr_borrowing_independent_validation_gate",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "full_market_selection_used": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("severity") == "fatal"]),
        "fatal_blockers": [row for row in blockers if row.get("severity") == "fatal"],
    }
    payload.update(extra)
    return payload


def _write_minimal(out: Path, summary: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    _write_json(out / "v5f_spike_mr_validation_summary.json", summary)
    _write_csv(out / "v5f_spike_mr_validation_blockers.csv", blockers)
    for name in [
        "v5f_spike_mr_validation_source_audit.csv",
        "v5f_spike_mr_validation_2020q4_fetch_log.csv",
        "v5f_spike_mr_validation_feature_panel.csv",
        "v5f_spike_mr_validation_event_log.csv",
        "v5f_spike_mr_validation_trade_log.csv",
        "v5f_spike_mr_validation_metrics.csv",
        "v5f_spike_mr_validation_funding_policy_comparison.csv",
        "v5f_spike_mr_validation_sleeve_stability.csv",
        "v5f_spike_mr_validation_governance_audit.csv",
        "v5f_spike_mr_validation_gap_register.csv",
        "v5f_spike_mr_validation_pm_gate_decision.csv",
        "v5f_spike_mr_validation_next_agent_queue.csv",
    ]:
        _write_csv(out / name, [])
    (out / "v5f_spike_mr_validation_report.md").write_text("# Blocked\n", encoding="utf-8")
    (out / "v5f_spike_mr_validation_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    print(
        json.dumps(
            run_v5f_spike_funded_mr_borrowing_independent_validation_gate(Path(".")),
            ensure_ascii=False,
            indent=2,
        )
    )
