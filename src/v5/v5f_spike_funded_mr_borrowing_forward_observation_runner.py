from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5d_baostock_5min_data_gate import normalize_baostock_frame


OUT_DIR = Path("v5f_spike_funded_mr_borrowing_forward_observation") / "current"
RAW_DIR = Path("v5f_spike_funded_mr_borrowing_forward_observation") / "data_raw" / "202607"
STD_DIR = Path("v5f_spike_funded_mr_borrowing_forward_observation") / "data_standardized" / "202607"

PRIMARY_FORWARD_SUMMARY = (
    Path("v5f_internal_subsleeve_forward_paper_tracking")
    / "current"
    / "v5f_internal_subsleeve_forward_summary.json"
)
BORROWING_SUMMARY = (
    Path("v5f_event_triggered_mean_reversion_borrowing_test")
    / "current"
    / "v5f_mr_borrowing_summary.json"
)
INDEPENDENT_VALIDATION_SUMMARY = (
    Path("v5f_spike_funded_mr_borrowing_independent_validation_gate")
    / "current"
    / "v5f_spike_mr_validation_summary.json"
)
INDEPENDENT_VALIDATION_GAPS = (
    Path("v5f_spike_funded_mr_borrowing_independent_validation_gate")
    / "current"
    / "v5f_spike_mr_validation_gap_register.csv"
)
THRESHOLDS = (
    Path("v5f_short_window_reversion_walk_forward_robustness")
    / "current"
    / "v5f_sleeve_specific_thresholds.csv"
)
PAPER_SIGNALS = (
    Path("paper_trading_signals")
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
    / "2026-07-19"
    / "basket_rebalance_signals.csv"
)

PRIMARY = "internal_subsleeve_mom12_70_30"
OBSERVATION_ID = "spike_funded_mr_borrowing_observe_only"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
PAPER_SIGNAL_PACKET_DATE = "2026-07-19"
PAPER_REBALANCE_DATE = "2026-07-01"
OBSERVATION_START = "2026-07-20"
OBSERVATION_END = "2026-07-31"
COMMISSION_RATE = 0.0003
BORROW_INTENSITY = 0.10
CAPS = [0.02, 0.05, 0.10]
HORIZONS = ["next1", "next2"]
POLICIES = ["paired_drop_spike_net0", "spike_only_strict"]

REQUIRED = [
    PRIMARY_FORWARD_SUMMARY,
    BORROWING_SUMMARY,
    INDEPENDENT_VALIDATION_SUMMARY,
    INDEPENDENT_VALIDATION_GAPS,
    THRESHOLDS,
    PAPER_SIGNALS,
]


def run_v5f_spike_funded_mr_borrowing_forward_observation(
    root: Path = Path("."),
    *,
    allow_baostock_fetch: bool = True,
) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (root / RAW_DIR).mkdir(parents=True, exist_ok=True)
    (root / STD_DIR).mkdir(parents=True, exist_ok=True)

    manifest = _input_manifest(root)
    missing = [row for row in manifest if row["required"] and not row["exists"]]
    if missing:
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", missing)
        _write_minimal(out, summary, manifest, missing)
        return summary

    primary_summary = _read_json(root / PRIMARY_FORWARD_SUMMARY)
    borrowing_summary = _read_json(root / BORROWING_SUMMARY)
    validation_summary = _read_json(root / INDEPENDENT_VALIDATION_SUMMARY)
    validation_gaps = _read_csv(root / INDEPENDENT_VALIDATION_GAPS)
    paper_targets = _paper_targets(root)
    thresholds = _thresholds_2026(root)
    fetch_log = _ensure_minute_data(root, paper_targets, allow_baostock_fetch)
    features = _feature_panel(root, paper_targets, thresholds, fetch_log)
    event_log, trade_log = _event_and_trade_logs(features)
    daily = _daily_observation(features, event_log, trade_log)
    metrics = _metrics(trade_log, features)
    sleeve = _sleeve_observation(trade_log)
    source = _source_evidence(primary_summary, borrowing_summary, validation_summary, validation_gaps, paper_targets, fetch_log, features)
    status = _candidate_status(primary_summary, borrowing_summary, validation_summary, metrics)
    schema = _observation_schema()
    template = _daily_template()
    allowed = _allowed_blocked_actions()
    governance = _governance_audit(primary_summary, validation_summary, source, thresholds, metrics)
    decision = _pm_decision(metrics, governance)
    blockers = _blockers(governance, validation_gaps, metrics)
    queue = _next_queue(decision[0]["pm_gate_decision"])

    _write_csv(out / "v5f_spike_mr_forward_input_manifest.csv", manifest)
    _write_csv(out / "v5f_spike_mr_forward_candidate_status.csv", status)
    _write_csv(out / "v5f_spike_mr_forward_observation_schema.csv", schema)
    _write_csv(out / "v5f_spike_mr_forward_daily_observation_template.csv", template)
    _write_csv(out / "v5f_spike_mr_forward_paper_target_universe.csv", paper_targets)
    _write_csv(out / "v5f_spike_mr_forward_thresholds.csv", thresholds)
    _write_csv(out / "v5f_spike_mr_forward_fetch_log.csv", fetch_log)
    _write_csv(out / "v5f_spike_mr_forward_feature_panel.csv", features)
    _write_csv(out / "v5f_spike_mr_forward_event_log.csv", event_log)
    _write_csv(out / "v5f_spike_mr_forward_observation_trade_log.csv", trade_log)
    _write_csv(out / "v5f_spike_mr_forward_daily_observation_log.csv", daily)
    _write_csv(out / "v5f_spike_mr_forward_metrics.csv", metrics)
    _write_csv(out / "v5f_spike_mr_forward_sleeve_observation.csv", sleeve)
    _write_csv(out / "v5f_spike_mr_forward_source_evidence_matrix.csv", source)
    _write_csv(out / "v5f_spike_mr_forward_allowed_blocked_actions.csv", allowed)
    _write_csv(out / "v5f_spike_mr_forward_governance_audit.csv", governance)
    _write_csv(out / "v5f_spike_mr_forward_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_spike_mr_forward_next_agent_queue.csv", queue)
    _write_csv(out / "v5f_spike_mr_forward_blockers.csv", blockers)
    (out / "v5f_spike_mr_forward_report.md").write_text(
        _report(status, metrics, sleeve, source, decision, blockers),
        encoding="utf-8",
    )
    (out / "v5f_spike_mr_forward_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = metrics[0] if metrics else {}
    summary = _summary(
        "completed_v5f_spike_funded_mr_borrowing_forward_observation",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        observation_id=OBSERVATION_ID,
        paper_signal_packet_date=PAPER_SIGNAL_PACKET_DATE,
        paper_rebalance_date=PAPER_REBALANCE_DATE,
        observation_start=OBSERVATION_START,
        observation_end=OBSERVATION_END,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        paper_only=True,
        accepted=False,
        live_trading_approved=False,
        deployment_approved=False,
        candidate_promoted=False,
        independent_validation_pass=False,
        forward_observation_started=True,
        baostock_fetch_started=any(row.get("fetch_started") is True for row in fetch_log),
        paper_target_count=len(paper_targets),
        feature_row_count=len(features),
        event_group_count=len(event_log),
        observation_trade_group_count=len(trade_log),
        best_observation_variant=best.get("version_id", ""),
        best_observation_policy=best.get("funding_policy", ""),
        best_observation_horizon=best.get("borrow_horizon", ""),
        best_observation_net_pct_points=float(best.get("net_incremental_return_pct_points", 0.0) or 0.0),
        best_observation_win_rate=float(best.get("win_rate", 0.0) or 0.0),
        research_blocker_count=len([row for row in blockers if row.get("severity") == "research"]),
    )
    _write_json(out / "v5f_spike_mr_forward_summary.json", summary)
    return summary


def _paper_targets(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / PAPER_SIGNALS, dtype={"trade_date": str, "code": str})
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "paper_signal_packet_date": PAPER_SIGNAL_PACKET_DATE,
                "paper_rebalance_date": str(row.get("trade_date") or PAPER_REBALANCE_DATE),
                "code": str(row["code"]),
                "bs_code": _jq_to_bs(str(row["code"])),
                "sleeve": str(row["sector_id"]),
                "selected_rank": row.get("selected_rank", ""),
                "target_weight": _safe_float(row.get("target_weight")) or 0.0,
                "score": _safe_float(row.get("score")),
                "source": str(PAPER_SIGNALS),
                "paper_only": True,
                "accepted": False,
            }
        )
    return rows


def _thresholds_2026(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / THRESHOLDS, dtype={"test_year": str})
    df = df[
        df["scheme"].astype(str).eq("anchored_prior_years")
        & df["test_year"].astype(str).eq("2026")
        & df["status"].astype(str).eq("pass")
    ].copy()
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "threshold_id": row["threshold_id"],
                "scheme": row["scheme"],
                "test_year": row["test_year"],
                "sleeve": row["sleeve"],
                "train_start": row["train_start"],
                "train_end": row["train_end"],
                "train_row_count": int(float(row["train_row_count"])),
                "drop_cut_r_0935_1000": float(row["drop_cut_r_0935_1000"]),
                "spike_cut_r_0935_1000": float(row["spike_cut_r_0935_1000"]),
                "threshold_source": "anchored_prior_years_train_end_2025_12_31",
                "uses_forward_202607_data": False,
                "accepted": False,
            }
        )
    return rows


def _ensure_minute_data(root: Path, paper_targets: list[dict[str, Any]], allow_fetch: bool) -> list[dict[str, Any]]:
    missing = [row for row in paper_targets if not _std_path(root, str(row["code"])).exists()]
    fetch_rows: list[dict[str, Any]] = []
    if missing and allow_fetch:
        fetch_rows.extend(_fetch_baostock(root, missing))
    output = []
    for row in paper_targets:
        code = str(row["code"])
        path = _std_path(root, code)
        status = "missing"
        row_count = 0
        if path.exists():
            try:
                row_count = len(pd.read_csv(path, usecols=["trade_date"]))
                status = "pass" if row_count else "empty"
            except Exception as exc:
                status = "read_error"
                output.append(
                    {
                        "code": code,
                        "bs_code": row["bs_code"],
                        "fetch_start_date": OBSERVATION_START,
                        "fetch_end_date": OBSERVATION_END,
                        "status": status,
                        "row_count": 0,
                        "standardized_path": str(path.relative_to(root)),
                        "fetch_started": False,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:300],
                    }
                )
                continue
        existing_fetch = next((item for item in fetch_rows if str(item.get("code")) == code), None)
        if existing_fetch:
            output.append(existing_fetch)
        else:
            output.append(
                {
                    "code": code,
                    "bs_code": row["bs_code"],
                    "fetch_start_date": OBSERVATION_START,
                    "fetch_end_date": OBSERVATION_END,
                    "status": status,
                    "row_count": row_count,
                    "standardized_path": str(path.relative_to(root)) if path.exists() else "",
                    "fetch_started": False,
                    "error_type": "" if status == "pass" else status,
                    "error_message": "",
                }
            )
    return sorted(output, key=lambda item: str(item["code"]))


def _fetch_baostock(root: Path, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        import baostock as bs
    except Exception as exc:
        return [_fetch_failure(row, "baostock_import_failed", type(exc).__name__, str(exc)) for row in targets]
    login = bs.login()
    if getattr(login, "error_code", "1") != "0":
        return [_fetch_failure(row, "baostock_login_failed", getattr(login, "error_code", ""), getattr(login, "error_msg", "")) for row in targets]
    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    rows: list[dict[str, Any]] = []
    try:
        for item in targets:
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
                    start_date=OBSERVATION_START,
                    end_date=OBSERVATION_END,
                    frequency="5",
                    adjustflag="3",
                )
                data: list[list[str]] = []
                while rs.error_code == "0" and rs.next():
                    data.append(rs.get_row_data())
                if rs.error_code != "0":
                    status = "query_error"
                    error_type = str(rs.error_code)
                    error_message = str(rs.error_msg)[:300]
                else:
                    raw_df = pd.DataFrame(data, columns=rs.fields)
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    std_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
                    std_df = normalize_baostock_frame(raw_df, code, bs_code, OBSERVATION_START, OBSERVATION_END)
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
                    "fetch_start_date": OBSERVATION_START,
                    "fetch_end_date": OBSERVATION_END,
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


def _fetch_failure(row: dict[str, Any], status: str, error_type: str, error_message: str) -> dict[str, Any]:
    return {
        "code": row["code"],
        "bs_code": row["bs_code"],
        "fetch_start_date": OBSERVATION_START,
        "fetch_end_date": OBSERVATION_END,
        "status": status,
        "row_count": 0,
        "standardized_path": "",
        "fetch_started": False,
        "error_type": error_type,
        "error_message": error_message[:300],
    }


def _feature_panel(
    root: Path,
    paper_targets: list[dict[str, Any]],
    thresholds: list[dict[str, Any]],
    fetch_log: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    target_by_code = {str(row["code"]): row for row in paper_targets}
    threshold_by_sleeve = {str(row["sleeve"]): row for row in thresholds}
    ok_codes = {str(row["code"]) for row in fetch_log if row.get("status") == "pass"}
    rows: list[dict[str, Any]] = []
    for code in sorted(ok_codes):
        path = _std_path(root, code)
        if not path.exists():
            continue
        target = target_by_code[code]
        threshold = threshold_by_sleeve.get(str(target["sleeve"]), {})
        df = pd.read_csv(path, dtype={"trade_date": str, "time": str})
        if df.empty:
            continue
        for col in ["open", "high", "low", "close", "volume", "amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        for trade_date, day in df.groupby("trade_date", sort=True):
            parsed = _parse_day(day)
            if not parsed:
                continue
            parsed.update(
                {
                    "trade_date": str(trade_date),
                    "code": code,
                    "sleeve": target["sleeve"],
                    "selected_rank": target["selected_rank"],
                    "target_weight": target["target_weight"],
                    "score": target["score"],
                    "drop_cut_r_0935_1000": threshold.get("drop_cut_r_0935_1000", ""),
                    "spike_cut_r_0935_1000": threshold.get("spike_cut_r_0935_1000", ""),
                    "threshold_source": threshold.get("threshold_source", ""),
                    "paper_only": True,
                    "new_buy_signal_used": False,
                    "accepted": False,
                }
            )
            rows.append(parsed)
    if not rows:
        return []
    df = pd.DataFrame(rows).sort_values(["code", "trade_date"]).reset_index(drop=True)
    groups = []
    for _, group in df.groupby("code", sort=True):
        group = group.sort_values("trade_date").reset_index(drop=True)
        group["next_day_close"] = group["day_close"].shift(-1)
        group["next_2d_close"] = group["day_close"].shift(-2)
        group["next1_date"] = group["trade_date"].shift(-1)
        group["next2_date"] = group["trade_date"].shift(-2)
        group["next1_from_1000"] = group.apply(lambda row: _ret(row["next_day_close"], row["close_1000"]), axis=1)
        group["next2_from_1000"] = group.apply(lambda row: _ret(row["next_2d_close"], row["close_1000"]), axis=1)
        groups.append(group)
    df = pd.concat(groups, ignore_index=True)
    df["is_drop"] = pd.to_numeric(df["r_0935_1000"], errors="coerce") <= pd.to_numeric(df["drop_cut_r_0935_1000"], errors="coerce")
    df["is_spike"] = pd.to_numeric(df["r_0935_1000"], errors="coerce") >= pd.to_numeric(df["spike_cut_r_0935_1000"], errors="coerce")
    return df.to_dict("records")


def _parse_day(day: pd.DataFrame) -> dict[str, Any]:
    day = day.sort_values("time").reset_index(drop=True)
    if day.empty:
        return {}
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
    events: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    for (trade_date, sleeve), group in df.groupby(["trade_date", "sleeve"], sort=True):
        for horizon in HORIZONS:
            ret_col = f"{horizon}_from_1000"
            close_col = f"{horizon}_date"
            drops = group[group["is_drop"] & group[ret_col].notna() & group[close_col].notna()].copy()
            if drops.empty:
                continue
            desired_by_drop = pd.to_numeric(drops["target_weight"], errors="coerce").fillna(0.0) * BORROW_INTENSITY
            desired_total = float(desired_by_drop.sum())
            sleeve_total = float(pd.to_numeric(group["target_weight"], errors="coerce").fillna(0.0).sum())
            for policy in POLICIES:
                for cap in CAPS:
                    trade = _single_trade_group(group, drops, desired_by_drop, policy, cap, horizon, ret_col, close_col, sleeve_total)
                    events.append(
                        {
                            "event_group_id": f"forward|{policy}|cap{int(cap*100)}|{horizon}|{trade_date}|{sleeve}",
                            "paper_date": trade_date,
                            "sleeve": sleeve,
                            "funding_policy": policy,
                            "borrow_cap_pct_of_sleeve": cap,
                            "borrow_horizon": horizon,
                            "drop_event_count": int(len(drops)),
                            "spike_source_count": int((group["is_spike"] & ~group["code"].astype(str).isin(set(drops["code"].astype(str)))).sum()),
                            "desired_borrow_weight": desired_total,
                            "actual_borrow_weight": trade["actual_borrow_weight"] if trade else 0.0,
                            "event_observed": True,
                            "observation_trade_pair_available": trade is not None,
                            "skip_reason": "" if trade else "no_eligible_same_sleeve_spike_funding_source_or_missing_return",
                            "paper_only": True,
                            "trade_order_allowed": False,
                            "accepted": False,
                        }
                    )
                    if trade:
                        trades.append(trade)
    return events, trades


def _single_trade_group(
    group: pd.DataFrame,
    drops: pd.DataFrame,
    desired_by_drop: pd.Series,
    policy: str,
    cap: float,
    horizon: str,
    ret_col: str,
    close_col: str,
    sleeve_total: float,
) -> dict[str, Any] | None:
    drop_codes = set(drops["code"].astype(str))
    sources = group[
        ~group["code"].astype(str).isin(drop_codes)
        & group["is_spike"]
        & group[ret_col].notna()
    ].copy()
    if sources.empty:
        return None
    desired_total = float(desired_by_drop.sum())
    source_available = float(pd.to_numeric(sources["target_weight"], errors="coerce").fillna(0.0).sum()) * BORROW_INTENSITY
    actual_borrow = min(desired_total, source_available, cap * sleeve_total)
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
    version = f"forward202607_{policy}_cap{int(cap*100)}_{horizon}"
    return {
        "version_id": version,
        "paper_open_date": str(group.iloc[0]["trade_date"]),
        "paper_close_date": _mode_date(drops[close_col]),
        "sleeve": str(group.iloc[0]["sleeve"]),
        "funding_policy": policy,
        "borrow_cap_pct_of_sleeve": cap,
        "borrow_horizon": horizon,
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
        "paper_only": True,
        "trade_order_allowed": False,
        "accepted": False,
    }


def _daily_observation(features: list[dict[str, Any]], events: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not features:
        return []
    feature_df = pd.DataFrame(features)
    event_df = pd.DataFrame(events)
    trade_df = pd.DataFrame(trades)
    rows: list[dict[str, Any]] = []
    for trade_date, group in feature_df.groupby("trade_date", sort=True):
        day_events = event_df[event_df["paper_date"].eq(trade_date)] if not event_df.empty else pd.DataFrame()
        day_trades = trade_df[trade_df["paper_open_date"].eq(trade_date)] if not trade_df.empty else pd.DataFrame()
        rows.append(
            {
                "paper_date": trade_date,
                "holding_count": int(group["code"].nunique()),
                "drop_stock_count": int(group["is_drop"].sum()),
                "spike_stock_count": int(group["is_spike"].sum()),
                "event_group_count": int(len(day_events)),
                "observation_trade_group_count": int(len(day_trades)),
                "net_observation_incremental_return": float(pd.to_numeric(day_trades.get("net_incremental_return", pd.Series(dtype=float)), errors="coerce").sum()) if not day_trades.empty else 0.0,
                "paper_only": True,
                "trade_order_allowed": False,
                "accepted": False,
            }
        )
    return rows


def _metrics(trades: list[dict[str, Any]], features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    feature_df = pd.DataFrame(features)
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
                "observation_window": f"{OBSERVATION_START}_{OBSERVATION_END}",
                "feature_day_count": int(feature_df["trade_date"].nunique()) if not feature_df.empty else 0,
                "trade_group_count": int(len(group)),
                "active_borrow_days": int(group["paper_open_date"].nunique()),
                "sleeve_count": int(group["sleeve"].nunique()),
                "net_incremental_return_sum": float(net.sum()),
                "net_incremental_return_pct_points": float(net.sum() * 100),
                "avg_target_minus_funding_return": float(spread.mean()),
                "win_rate": float((net > 0).mean()) if len(net) else 0.0,
                "paper_only": True,
                "formal_candidate": False,
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda item: float(item["net_incremental_return_pct_points"]), reverse=True)


def _sleeve_observation(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows = []
    for (version, sleeve), group in df.groupby(["version_id", "sleeve"], sort=True):
        net = pd.to_numeric(group["net_incremental_return"], errors="coerce")
        rows.append(
            {
                "version_id": version,
                "sleeve": sleeve,
                "funding_policy": str(group.iloc[0]["funding_policy"]),
                "borrow_horizon": str(group.iloc[0]["borrow_horizon"]),
                "trade_group_count": int(len(group)),
                "active_borrow_days": int(group["paper_open_date"].nunique()),
                "net_incremental_return_pct_points": float(net.sum() * 100),
                "win_rate": float((net > 0).mean()) if len(net) else 0.0,
                "paper_only": True,
            }
        )
    return sorted(rows, key=lambda item: float(item["net_incremental_return_pct_points"]), reverse=True)


def _source_evidence(
    primary_summary: dict[str, Any],
    borrowing_summary: dict[str, Any],
    validation_summary: dict[str, Any],
    validation_gaps: list[dict[str, str]],
    paper_targets: list[dict[str, Any]],
    fetch_log: list[dict[str, Any]],
    features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fetch_pass = sum(1 for row in fetch_log if row.get("status") == "pass")
    return [
        {
            "source_id": "v5f_primary_forward_line",
            "status": primary_summary.get("pm_gate_decision", ""),
            "classification": "primary_forward_paper_candidate",
            "observed": primary_summary.get("delta_return_pct_points_vs_repaired_baseline", ""),
        },
        {
            "source_id": "event_triggered_borrowing_backtest_scope",
            "status": borrowing_summary.get("pm_gate_decision", ""),
            "classification": "2021_2026_backtest_scope_not_oos",
            "observed": borrowing_summary.get("best_delta_return_pct_points_vs_champion", ""),
        },
        {
            "source_id": "limited_2020q4_independent_validation",
            "status": validation_summary.get("pm_gate_decision", ""),
            "classification": validation_summary.get("validation_window_classification", ""),
            "observed": validation_summary.get("best_net_incremental_return_pct_points", validation_summary.get("best_observation_net_pct_points", "")),
        },
        {
            "source_id": "validation_gaps",
            "status": "open",
            "classification": "blocks_candidate_promotion",
            "observed": len([row for row in validation_gaps if row.get("blocks_formal_promotion") == "True"]),
        },
        {
            "source_id": "202607_paper_targets",
            "status": "available" if paper_targets else "missing",
            "classification": "post_20260531_forward_paper_only",
            "observed": len(paper_targets),
        },
        {
            "source_id": "202607_forward_5min_fetch",
            "status": "pass" if fetch_log and fetch_pass == len(fetch_log) else "partial_or_missing",
            "classification": "post_20260531_forward_paper_only",
            "observed": f"{fetch_pass}/{len(fetch_log)}",
        },
        {
            "source_id": "202607_forward_feature_panel",
            "status": "pass" if features else "missing",
            "classification": "post_20260531_forward_paper_only",
            "observed": len(features),
        },
    ]


def _candidate_status(
    primary_summary: dict[str, Any],
    borrowing_summary: dict[str, Any],
    validation_summary: dict[str, Any],
    metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    best = metrics[0] if metrics else {}
    return [
        {
            "line_id": PRIMARY,
            "role": "primary_v5f_forward_paper_line",
            "status": "forward_paper_tracking_ready_not_accepted",
            "delta_return_pct_points_vs_repaired_baseline": primary_summary.get("delta_return_pct_points_vs_repaired_baseline", ""),
            "accepted": False,
            "live_trading_approved": False,
        },
        {
            "line_id": OBSERVATION_ID,
            "role": "secondary_observation_only",
            "status": "forward_paper_observation_only_not_candidate",
            "backtest_delta_vs_champion_pct_points": borrowing_summary.get("best_delta_return_pct_points_vs_champion", ""),
            "limited_2020q4_directional_pass": validation_summary.get("limited_2020q4_directional_pass", False),
            "forward_initial_best_net_pct_points": best.get("net_incremental_return_pct_points", ""),
            "candidate_promoted": False,
            "accepted": False,
            "live_trading_approved": False,
        },
    ]


def _observation_schema() -> list[dict[str, Any]]:
    fields = [
        ("paper_date", "Forward/paper observation date after 2026-05-31."),
        ("code", "Official V57f paper target stock only."),
        ("sleeve", "Original sleeve."),
        ("r_0935_1000", "Observed 09:35 to 10:00 5min return."),
        ("drop_cut_r_0935_1000", "PIT threshold trained through 2025-12-31."),
        ("spike_cut_r_0935_1000", "PIT threshold trained through 2025-12-31."),
        ("is_drop", "True when morning move is below same-sleeve drop threshold."),
        ("is_spike", "True when morning move is above same-sleeve spike threshold."),
        ("next1_from_1000", "Forward observation return, evaluation only."),
        ("next2_from_1000", "Forward observation return, evaluation only."),
        ("paper_only", "Always true."),
        ("trade_order_allowed", "Always false."),
    ]
    return [{"field": field, "definition": definition} for field, definition in fields]


def _daily_template() -> list[dict[str, Any]]:
    return [
        {
            "paper_date": "",
            "observation_id": OBSERVATION_ID,
            "holding_count": "",
            "drop_stock_count": "",
            "spike_stock_count": "",
            "event_group_count": "",
            "observation_trade_group_count": "",
            "paper_action": "observe_only",
            "trade_order_allowed": False,
            "accepted": False,
        }
    ]


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "record_forward_observation_event", "allowed": True, "blocked": False},
        {"action": "compare_event_target_vs_spike_funding_return", "allowed": True, "blocked": False},
        {"action": "create_trade_order", "allowed": False, "blocked": True},
        {"action": "change_v5f_weight", "allowed": False, "blocked": True},
        {"action": "reserve_fixed_mean_reversion_budget", "allowed": False, "blocked": True},
        {"action": "promote_to_candidate", "allowed": False, "blocked": True},
        {"action": "mark_accepted_or_live_approved", "allowed": False, "blocked": True},
        {"action": "use_202607_as_historical_backtest", "allowed": False, "blocked": True},
    ]


def _governance_audit(
    primary_summary: dict[str, Any],
    validation_summary: dict[str, Any],
    source: list[dict[str, Any]],
    thresholds: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_by_id = {row["source_id"]: row for row in source}
    return [
        _audit("primary_line_retained", primary_summary.get("primary_candidate") == PRIMARY, primary_summary.get("primary_candidate")),
        _audit("observation_line_not_candidate", not validation_summary.get("independent_validation_pass", True), validation_summary.get("independent_validation_pass")),
        _audit("post_20260531_forward_only", True, f"{OBSERVATION_START} to {OBSERVATION_END}"),
        _audit("backtest_scope_end_unchanged", True, BACKTEST_END),
        _audit("paper_targets_available", source_by_id.get("202607_paper_targets", {}).get("status") == "available", source_by_id.get("202607_paper_targets", {}).get("observed")),
        _audit("forward_5min_fetch_pass", source_by_id.get("202607_forward_5min_fetch", {}).get("status") == "pass", source_by_id.get("202607_forward_5min_fetch", {}).get("observed")),
        _audit("thresholds_pit_train_end_20251231", bool(thresholds) and all(row["uses_forward_202607_data"] is False for row in thresholds), "anchored prior years"),
        _audit("same_sleeve_only", True, True),
        _audit("no_fixed_mean_reversion_budget", True, True),
        _audit("no_trade_order", True, False),
        _audit("no_v57f_core_modified", True, False),
        _audit("accepted_false", True, False),
        _audit("live_trading_approved_false", True, False),
        _audit("formal_promotion_blocked", True, "open validation gaps remain"),
        _audit("metrics_nonempty_or_no_event_ok", True, len(metrics)),
    ]


def _audit(audit_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if ok else "fail", "detail": detail}


def _pm_decision(metrics: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] == "fail"]
    best = metrics[0] if metrics else {}
    if failed:
        decision = "blocked_by_forward_observation_data_or_governance_issue"
        verdict = "blocked"
    elif not metrics:
        decision = "forward_observation_started_no_events_yet_not_candidate"
        verdict = "started_wait_for_events"
    elif float(best.get("net_incremental_return_pct_points", 0.0) or 0.0) > 0:
        decision = "forward_observation_initial_positive_not_candidate"
        verdict = "initial_forward_events_positive_but_observe_only"
    else:
        decision = "forward_observation_initial_mixed_keep_diagnostic"
        verdict = "initial_forward_events_not_stable"
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": PRIMARY,
            "observation_id": OBSERVATION_ID,
            "best_forward_variant": best.get("version_id", ""),
            "best_forward_net_pct_points": best.get("net_incremental_return_pct_points", ""),
            "best_forward_win_rate": best.get("win_rate", ""),
            "forward_observation_started": decision != "blocked_by_forward_observation_data_or_governance_issue",
            "candidate_promoted": False,
            "accepted": False,
            "live_trading_approved": False,
            "trade_path_changed": False,
            "verdict": verdict,
        }
    ]


def _blockers(
    governance: list[dict[str, Any]],
    validation_gaps: list[dict[str, str]],
    metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]}
        for row in governance
        if row["status"] == "fail"
    ]
    rows.extend(
        {
            "blocker_id": row["gap_id"],
            "severity": "research",
            "status": "blocking_candidate_promotion",
            "detail": row["detail"],
        }
        for row in validation_gaps
        if row.get("blocks_formal_promotion") == "True"
    )
    rows.append(
        {
            "blocker_id": "forward_multi_cycle_evidence_missing",
            "severity": "research",
            "status": "blocking_candidate_promotion",
            "detail": f"Only current observation window {OBSERVATION_START} to {OBSERVATION_END}; metrics rows={len(metrics)}.",
        }
    )
    return rows


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "continue_internal_subsleeve_mom12_70_30_forward_paper_tracking",
            "allowed": True,
            "status": "primary_line",
        },
        {
            "priority": 2,
            "next_task": "append_spike_funded_mr_borrowing_forward_observations_daily",
            "allowed": decision != "blocked_by_forward_observation_data_or_governance_issue",
            "status": "observation_only",
        },
        {
            "priority": 3,
            "next_task": "closeout_after_multiple_forward_rebalance_cycles",
            "allowed": True,
            "status": "waiting_more_forward_evidence",
        },
        {
            "priority": 4,
            "next_task": "source_pre2020_5min_or_alternate_provider_for_formal_independent_validation",
            "allowed": True,
            "status": "optional_for_candidate_review",
        },
        {
            "priority": 5,
            "next_task": "promote_spike_funded_mr_borrowing_to_candidate",
            "allowed": False,
            "status": "blocked_until_independent_validation_passes",
        },
    ]


def _report(
    status: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    sleeve: list[dict[str, Any]],
    source: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5f Spike-Funded MR Borrowing Forward/Paper Observation",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Primary line: `{PRIMARY}` remains primary.",
        f"- Observation line: `{OBSERVATION_ID}` is observe-only, not candidate.",
        f"- Window: `{OBSERVATION_START}` to `{OBSERVATION_END}`; this is forward/paper, not historical backtest.",
        "- Accepted/live/deployment approved: `False`.",
        "",
        "## Status",
        "",
    ]
    for row in status:
        lines.append(f"- `{row['line_id']}`: `{row['status']}`.")
    lines.extend(["", "## Top Forward Observations", ""])
    if metrics:
        for row in metrics[:8]:
            lines.append(
                f"- `{row['version_id']}`: net `{float(row['net_incremental_return_pct_points']):.4f}` pct, win `{float(row['win_rate']):.2%}`, groups `{row['trade_group_count']}`."
            )
    else:
        lines.append("- No paired drop/spike observation trades yet.")
    lines.extend(["", "## Sleeve View", ""])
    for row in sleeve[:8]:
        lines.append(
            f"- `{row['sleeve']}` / `{row['version_id']}`: net `{float(row['net_incremental_return_pct_points']):.4f}` pct."
        )
    lines.extend(["", "## Evidence", ""])
    for row in source:
        lines.append(f"- `{row['source_id']}`: `{row['status']}` / {row['classification']} / observed `{row['observed']}`.")
    lines.extend(["", "## Promotion Blockers", ""])
    for row in blockers:
        if row["severity"] == "research":
            lines.append(f"- `{row['blocker_id']}`: {row['detail']}")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Spike-Funded MR Borrowing Forward Observation Rules",
            "",
            "- Keep `internal_subsleeve_mom12_70_30` as the V5f primary line.",
            "- This MR borrowing line is observe-only and not a candidate.",
            "- Use only official/paper V57f target holdings; no full-market selection.",
            "- Use 2026 thresholds trained through 2025-12-31; do not infer thresholds from 2026-07 returns.",
            "- No trade orders, no weight changes, no fixed MR budget, no accepted/live status.",
            "- Dates after 2026-05-31 are forward/paper evidence, not historical backtest.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {"path": str(path), "required": True, "exists": (root / path).exists(), "file_size_bytes": (root / path).stat().st_size if (root / path).exists() else ""}
        for path in REQUIRED
    ]


def _write_minimal(out: Path, summary: dict[str, Any], manifest: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> None:
    _write_json(out / "v5f_spike_mr_forward_summary.json", summary)
    _write_csv(out / "v5f_spike_mr_forward_input_manifest.csv", manifest)
    _write_csv(out / "v5f_spike_mr_forward_blockers.csv", blockers)
    for name in [
        "v5f_spike_mr_forward_candidate_status.csv",
        "v5f_spike_mr_forward_observation_schema.csv",
        "v5f_spike_mr_forward_daily_observation_template.csv",
        "v5f_spike_mr_forward_paper_target_universe.csv",
        "v5f_spike_mr_forward_thresholds.csv",
        "v5f_spike_mr_forward_fetch_log.csv",
        "v5f_spike_mr_forward_feature_panel.csv",
        "v5f_spike_mr_forward_event_log.csv",
        "v5f_spike_mr_forward_observation_trade_log.csv",
        "v5f_spike_mr_forward_daily_observation_log.csv",
        "v5f_spike_mr_forward_metrics.csv",
        "v5f_spike_mr_forward_sleeve_observation.csv",
        "v5f_spike_mr_forward_source_evidence_matrix.csv",
        "v5f_spike_mr_forward_allowed_blocked_actions.csv",
        "v5f_spike_mr_forward_governance_audit.csv",
        "v5f_spike_mr_forward_pm_gate_decision.csv",
        "v5f_spike_mr_forward_next_agent_queue.csv",
    ]:
        _write_csv(out / name, [])
    (out / "v5f_spike_mr_forward_report.md").write_text("# Blocked\n", encoding="utf-8")
    (out / "v5f_spike_mr_forward_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_spike_funded_mr_borrowing_forward_observation",
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
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }
    payload.update(extra)
    return payload


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
        if value is None or value == "":
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


def _jq_to_bs(code: str) -> str:
    plain = code.split(".")[0]
    if code.endswith(".XSHG"):
        return f"sh.{plain}"
    if code.endswith(".XSHE"):
        return f"sz.{plain}"
    raise ValueError(f"Unsupported code format: {code}")


def _raw_path(root: Path, code: str) -> Path:
    return root / RAW_DIR / f"{code.replace('.', '_')}_5min_raw.csv"


def _std_path(root: Path, code: str) -> Path:
    return root / STD_DIR / f"{code.replace('.', '_')}_5min_standardized.csv"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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
            run_v5f_spike_funded_mr_borrowing_forward_observation(Path(".")),
            ensure_ascii=False,
            indent=2,
        )
    )
