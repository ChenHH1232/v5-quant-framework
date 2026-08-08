from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_pre2021_5min_blocker_completion") / "current"
DATASET_ID = "local_5min_2013_2026"
PRE2021_START = "2013-01-01"
PRE2021_END = "2020-12-31"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003
BORROW_INTENSITY = 0.10
CAPS = [0.02, 0.05, 0.10]
HORIZONS = ["next1", "next2"]
POLICIES = ["paired_drop_spike_net0", "pro_rata_non_drop"]
SCHEMES = ["anchored_prior_years", "rolling_2y_prior_years"]
POOL_SCOPES = ["strict_selected_pool_prior_years", "candidate_union_prior_years"]
MIN_TRAIN_ROWS = 80

PRE2021_CANDIDATES = (
    Path("v5f_pre2021_repaired_multisleeve_data_gate")
    / "current"
    / "v5f_pre2021_candidate_signal_preview.csv"
)
PRE2021_GATE_SUMMARY = (
    Path("v5f_pre2021_repaired_multisleeve_data_gate")
    / "current"
    / "v5f_pre2021_data_gate_summary.json"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_pre2021_5min_blocker_completion(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_pre2021_5min_completion_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_input", blockers)
        _write_json(out / "v5f_pre2021_5min_completion_summary.json", summary)
        return summary

    db = _find_v5_database(root)
    processed = db / "processed" / DATASET_ID
    manifests = db / "manifests" / DATASET_ID
    local_manifest = _read_json(manifests / "collection_manifest.json")
    universe = pd.read_csv(processed / "v5_required_5min_universe.csv", dtype=str)
    candidates = pd.read_csv(root / PRE2021_CANDIDATES, dtype=str)
    gate_summary = _read_json(root / PRE2021_GATE_SUMMARY)

    stopped = _stopped_inventory(root)
    source_audit = _source_audit(local_manifest, universe, candidates, stopped)
    cycles = _candidate_cycles(candidates)
    daily_features = _daily_feature_cache(root, db, candidates)
    candidate_features = _candidate_features(daily_features, candidates, cycles)
    thresholds = _thresholds(daily_features, universe, candidates, candidate_features)
    events = _event_rows(candidate_features, thresholds)
    event_diag = _event_diagnostics(events)
    trades = _trade_log(candidate_features, thresholds)
    metrics = _metrics(trades)
    by_cycle = _cycle_metrics(trades)
    by_sleeve = _sleeve_metrics(trades)
    resolution = _blocker_resolution(stopped, source_audit, candidate_features, thresholds, metrics)
    model_completion = _model_completion_matrix(stopped, metrics, resolution)
    governance = _governance_audit(source_audit, candidate_features, thresholds, gate_summary)
    decision = _pm_decision(metrics, governance, resolution)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance, resolution)

    _write_csv(out / "v5f_pre2021_5min_stopped_model_inventory.csv", stopped)
    _write_csv(out / "v5f_pre2021_5min_source_audit.csv", source_audit)
    _write_csv(out / "v5f_pre2021_candidate_cycle_map.csv", cycles)
    _write_csv(out / "v5f_pre2021_5min_feature_panel.csv", candidate_features)
    _write_csv(out / "v5f_pre2021_5min_sleeve_thresholds.csv", thresholds)
    _write_csv(out / "v5f_pre2021_5min_event_log.csv", events)
    _write_csv(out / "v5f_pre2021_5min_event_diagnostics.csv", event_diag)
    _write_csv(out / "v5f_pre2021_5min_borrowing_trade_log.csv", trades)
    _write_csv(out / "v5f_pre2021_5min_borrowing_metrics.csv", metrics)
    _write_csv(out / "v5f_pre2021_5min_borrowing_by_cycle.csv", by_cycle)
    _write_csv(out / "v5f_pre2021_5min_borrowing_by_sleeve.csv", by_sleeve)
    _write_csv(out / "v5f_pre2021_5min_blocker_resolution_matrix.csv", resolution)
    _write_csv(out / "v5f_pre2021_5min_model_completion_matrix.csv", model_completion)
    _write_csv(out / "v5f_pre2021_5min_governance_audit.csv", governance)
    _write_csv(out / "v5f_pre2021_5min_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_pre2021_5min_next_queue.csv", next_queue)
    _write_csv(out / "v5f_pre2021_5min_completion_blockers.csv", blockers_out)
    (out / "v5f_pre2021_5min_completion_report.md").write_text(
        _report(local_manifest, stopped, event_diag, metrics, by_cycle, by_sleeve, resolution, decision),
        encoding="utf-8",
    )
    (out / "v5f_pre2021_5min_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = metrics[0] if metrics else {}
    summary = _summary(
        "completed_pre2021_5min_blocker_completion",
        decision[0]["pm_gate_decision"],
        [],
        local_5min_dataset_status=local_manifest.get("status", ""),
        local_5min_total_rows=local_manifest.get("total_5min_rows", 0),
        stopped_item_count=len(stopped),
        resolved_data_blocker_count=sum(1 for row in resolution if row.get("resolution_status") == "resolved_by_local_5min"),
        remaining_promotion_blocker_count=sum(1 for row in resolution if row.get("blocks_promotion") is True),
        candidate_cycle_count=len(cycles),
        candidate_feature_rows=len(candidate_features),
        event_count=len(events),
        trade_group_count=len(trades),
        best_variant=best.get("version_id", ""),
        best_net_incremental_return_pct_points=float(best.get("net_incremental_return_pct_points", 0.0) or 0.0),
        best_win_rate=float(best.get("win_rate", 0.0) or 0.0),
        independent_validation_pass=decision[0]["independent_validation_pass"],
        accepted=False,
        live_trading_approved=False,
        v57f_core_modified=False,
        threshold_scan_used=False,
        full_market_selection_used=False,
    )
    _write_json(out / "v5f_pre2021_5min_completion_summary.json", summary)
    return summary


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("V5 database directory not found.")


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    missing = []
    required = [
        PRE2021_CANDIDATES,
        PRE2021_GATE_SUMMARY,
    ]
    try:
        db = _find_v5_database(root)
        required.extend(
            [
                db / "processed" / DATASET_ID / "v5_required_5min_universe.csv",
                db / "processed" / DATASET_ID / "v5_required_5min_standardized_index.csv",
                db / "manifests" / DATASET_ID / "collection_manifest.json",
            ]
        )
    except Exception as exc:
        missing.append({"blocker_id": "missing_v5_database", "severity": "fatal", "status": "blocking", "detail": str(exc)})
    for path in required:
        target = root / path if not path.is_absolute() else path
        if not target.exists():
            missing.append({"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "detail": str(path)})
    return missing


def _stopped_inventory(root: Path) -> list[dict[str, Any]]:
    rows = [
        {
            "item_id": "v5f_spike_funded_mr_borrowing_independent_validation_gate",
            "type": "model_validation",
            "prior_status": _json_value(root, "v5f_spike_funded_mr_borrowing_independent_validation_gate/current/v5f_spike_mr_validation_summary.json", "pm_gate_decision"),
            "blocked_by": "pre2020_5min_not_confirmed;only_one_pre2021_validation_cycle;prior_year_sleeve_threshold_unavailable_for_2020",
            "completion_action": "rerun pre2021 spike/reversion and borrowing validation using local_5min_2013_2026",
        },
        {
            "item_id": "v5f_short_window_reversion_walk_forward_robustness",
            "type": "walk_forward_validation",
            "prior_status": _json_value(root, "v5f_short_window_reversion_walk_forward_robustness/current/v5f_walk_forward_summary.json", "pm_gate_decision"),
            "blocked_by": "pre2014_2019_5min_source",
            "completion_action": "add pre2021 independent prior-year sleeve thresholds using 2013-2020 local 5min",
        },
        {
            "item_id": "v5g_05_short_window_reversion_independent_validation_gate",
            "type": "promotion_gate",
            "prior_status": _json_value(root, "v5g_05_short_window_reversion_independent_validation_gate/current/v5g_05_short_window_validation_gate_summary.json", "pm_gate_decision"),
            "blocked_by": "pre2021_or_future_independent_validation_missing",
            "completion_action": "replace missing-data blocker with completed pre2021 local 5min validation result",
        },
        {
            "item_id": "v5f_spike_mr_prebacktest_to_backtest_jq_sim",
            "type": "jq_sim_handoff",
            "prior_status": _json_value(root, "v5f_spike_mr_prebacktest_to_backtest_jq_sim/current/v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json", "pm_gate_decision"),
            "blocked_by": "pre2020_5min_not_confirmed;prior_year_sleeve_threshold_unavailable_for_2020",
            "completion_action": "refresh evidence using local pre2021 5min; keep JQ sim separate",
        },
    ]
    return rows


def _json_value(root: Path, rel_path: str, key: str) -> str:
    path = root / rel_path
    if not path.exists():
        return "missing_prior_summary"
    try:
        return str(_read_json(path).get(key, ""))
    except Exception:
        return "unreadable_prior_summary"


def _source_audit(
    manifest: dict[str, Any],
    universe: pd.DataFrame,
    candidates: pd.DataFrame,
    stopped: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    years = manifest.get("years_loaded", [])
    return [
        {
            "audit_id": "local_5min_dataset_completed",
            "status": "pass" if manifest.get("status") == "completed" and 2013 in years and 2020 in years else "fail",
            "detail": manifest.get("status", ""),
        },
        {
            "audit_id": "pre2021_years_available",
            "status": "pass" if all(year in years for year in range(2013, 2021)) else "fail",
            "detail": ";".join(map(str, years)),
        },
        {
            "audit_id": "universe_available",
            "status": "pass" if len(universe) else "fail",
            "detail": int(len(universe)),
        },
        {
            "audit_id": "candidate_preview_available",
            "status": "pass" if len(candidates) else "fail",
            "detail": int(len(candidates)),
        },
        {
            "audit_id": "stopped_item_inventory_built",
            "status": "pass" if len(stopped) else "fail",
            "detail": int(len(stopped)),
        },
    ]


def _candidate_cycles(candidates: pd.DataFrame) -> list[dict[str, Any]]:
    dates = sorted(candidates["preview_date"].dropna().astype(str).unique().tolist())
    rows = []
    for index, start in enumerate(dates):
        next_date = dates[index + 1] if index + 1 < len(dates) else ""
        end = "2020-12-31"
        end_rule = "pre2021_scope_end"
        if next_date:
            end = _previous_calendar_day(next_date)
            end_rule = "day_before_next_preview"
        rows.append(
            {
                "preview_date": start,
                "cycle_start": start,
                "cycle_end": end,
                "next_preview_date": next_date,
                "end_rule": end_rule,
                "candidate_count": int((candidates["preview_date"].astype(str) == start).sum()),
                "classification": "pre2021_repaired_candidate_preview_not_full_v57f_rebalance",
            }
        )
    return rows


def _previous_calendar_day(date_text: str) -> str:
    dt = pd.Timestamp(date_text) - pd.Timedelta(days=1)
    return dt.date().isoformat()


def _daily_feature_cache(root: Path, db: Path, candidates: pd.DataFrame) -> pd.DataFrame:
    processed = db / "processed" / DATASET_ID
    cache_path = processed / "v5_required_5min_daily_feature_cache_2013_2020_candidate_preview_codes.csv"
    if cache_path.exists():
        return pd.read_csv(cache_path, dtype={"trade_date": str, "code": str})
    rows: list[dict[str, Any]] = []
    for code in sorted(candidates["code"].dropna().astype(str).unique().tolist()):
        file_code = code.replace(".", "_")
        for year in range(2013, 2021):
            path = processed / "by_year" / str(year) / f"{file_code}_5min.csv"
            if not path.exists():
                continue
            df = pd.read_csv(
                path,
                usecols=["code", "trade_date", "time", "open", "high", "low", "close", "volume", "amount"],
                dtype={"code": str, "trade_date": str, "time": str},
            )
            rows.extend(_day_feature_rows(df, year))
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["code", "trade_date"]).reset_index(drop=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return out


def _day_feature_rows(df: pd.DataFrame, year: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if df.empty:
        return rows
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for (code, trade_date), group in df.groupby(["code", "trade_date"], sort=True):
        group = group.sort_values("time")
        by_time = {str(row["time"]): row for _, row in group.iterrows()}
        close_0935 = _time_close(by_time, "09:35:00")
        close_1000 = _time_close(by_time, "10:00:00")
        close_1030 = _time_close(by_time, "10:30:00")
        close_1455 = _time_close(by_time, "14:55:00")
        volume = group["volume"].fillna(0.0)
        amount = group["amount"].fillna(0.0)
        vwap = float(amount.sum() / volume.sum()) if float(volume.sum()) else _safe_float(group.iloc[-1]["close"])
        rows.append(
            {
                "code": code,
                "trade_date": trade_date,
                "year": year,
                "bar_count": int(len(group)),
                "first_bar_time": str(group.iloc[0]["time"]),
                "last_bar_time": str(group.iloc[-1]["time"]),
                "day_open": _safe_float(group.iloc[0]["open"]),
                "day_close": _safe_float(group.iloc[-1]["close"]),
                "day_low": _safe_float(group["low"].min()),
                "close_0935": close_0935,
                "close_1000": close_1000,
                "close_1030": close_1030,
                "close_1455": close_1455,
                "vwap_1455": vwap,
                "r_0935_1000": _ret(close_1000, close_0935),
                "r_0935_1030": _ret(close_1030, close_0935),
                "r_1000_1455": _ret(close_1455, close_1000),
                "r_1455_vwap": _ret(close_1455, vwap),
                "source": DATASET_ID,
            }
        )
    return rows


def _candidate_features(
    daily: pd.DataFrame,
    candidates: pd.DataFrame,
    cycles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cycle in cycles:
        preview_date = str(cycle["preview_date"])
        start = str(cycle["cycle_start"])
        end = str(cycle["cycle_end"])
        selected = candidates[candidates["preview_date"].astype(str).eq(preview_date)].copy()
        if selected.empty:
            continue
        selected_codes = set(selected["code"].astype(str))
        selected_map = selected.set_index("code").to_dict("index")
        df = daily[
            daily["code"].astype(str).isin(selected_codes)
            & (daily["trade_date"].astype(str) >= start)
            & (daily["trade_date"].astype(str) <= end)
        ].copy()
        if df.empty:
            continue
        df = df.sort_values(["code", "trade_date"]).reset_index(drop=True)
        target_weight = 1.0 / len(selected)
        for code, group in df.groupby("code", sort=True):
            meta = selected_map[str(code)]
            group = group.copy().reset_index(drop=True)
            group["prev_day_close"] = group["day_close"].shift(1)
            group["next_day_close"] = group["day_close"].shift(-1)
            group["next_2d_close"] = group["day_close"].shift(-2)
            for _, row in group.iterrows():
                out = row.to_dict()
                out.update(
                    {
                        "preview_date": preview_date,
                        "cycle_start": start,
                        "cycle_end": end,
                        "sleeve": meta.get("sector_id", ""),
                        "selected_rank": meta.get("selected_rank", ""),
                        "score": meta.get("score", ""),
                        "target_weight": target_weight,
                        "next1_from_1000": _ret(row.get("next_day_close"), row.get("close_1000")),
                        "next2_from_1000": _ret(row.get("next_2d_close"), row.get("close_1000")),
                        "r_prevclose_close": _ret(row.get("day_close"), row.get("prev_day_close")),
                        "research_pool": "pre2021_repaired_candidate_preview",
                        "future_return_used_for_signal": False,
                        "accepted": False,
                    }
                )
                rows.append(out)
    return sorted(rows, key=lambda row: (str(row["preview_date"]), str(row["trade_date"]), str(row["code"])))


def _thresholds(
    daily: pd.DataFrame,
    universe: pd.DataFrame,
    candidates: pd.DataFrame,
    candidate_features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    universe_map = _universe_sleeve_map(universe)
    broad_rows = []
    for code, sleeves in universe_map.items():
        part = daily[daily["code"].astype(str).eq(code)][["code", "trade_date", "year", "r_0935_1000"]].copy()
        if part.empty:
            continue
        for sleeve in sleeves:
            temp = part.copy()
            temp["sleeve"] = sleeve
            temp["pool_scope"] = "candidate_union_prior_years"
            broad_rows.append(temp)
    broad = pd.concat(broad_rows, ignore_index=True) if broad_rows else pd.DataFrame()

    strict_parts = []
    for preview_date in sorted(candidates["preview_date"].dropna().astype(str).unique()):
        selected = candidates[candidates["preview_date"].astype(str).eq(preview_date)]
        for sleeve, group in selected.groupby("sector_id"):
            codes = set(group["code"].astype(str))
            part = daily[daily["code"].astype(str).isin(codes)][["code", "trade_date", "year", "r_0935_1000"]].copy()
            if part.empty:
                continue
            part["sleeve"] = str(sleeve)
            part["preview_date"] = str(preview_date)
            part["pool_scope"] = "strict_selected_pool_prior_years"
            strict_parts.append(part)
    strict = pd.concat(strict_parts, ignore_index=True) if strict_parts else pd.DataFrame()

    rows: list[dict[str, Any]] = []
    feature_df = pd.DataFrame(candidate_features)
    if feature_df.empty:
        return rows
    keys = feature_df[["preview_date", "year", "sleeve"]].drop_duplicates().sort_values(["preview_date", "year", "sleeve"])
    for _, key in keys.iterrows():
        preview_date = str(key["preview_date"])
        test_year = int(key["year"])
        sleeve = str(key["sleeve"])
        for scheme in SCHEMES:
            for pool_scope in POOL_SCOPES:
                if pool_scope == "strict_selected_pool_prior_years":
                    source = strict[(strict["preview_date"].astype(str).eq(preview_date)) & (strict["sleeve"].astype(str).eq(sleeve))].copy()
                else:
                    source = broad[broad["sleeve"].astype(str).eq(sleeve)].copy()
                if scheme == "rolling_2y_prior_years":
                    source = source[(source["year"] < test_year) & (source["year"] >= test_year - 2)]
                else:
                    source = source[source["year"] < test_year]
                series = pd.to_numeric(source["r_0935_1000"], errors="coerce").dropna()
                status = "pass" if len(series) >= MIN_TRAIN_ROWS else "insufficient_prior_train_rows"
                rows.append(
                    {
                        "threshold_id": f"{pool_scope}|{scheme}|{preview_date}|{test_year}|{sleeve}",
                        "pool_scope": pool_scope,
                        "scheme": scheme,
                        "preview_date": preview_date,
                        "test_year": test_year,
                        "sleeve": sleeve,
                        "train_start": str(source["trade_date"].min()) if not source.empty else "",
                        "train_end": str(source["trade_date"].max()) if not source.empty else "",
                        "train_row_count": int(len(series)),
                        "drop_lower_quantile": 0.10,
                        "spike_upper_quantile": 0.90,
                        "drop_cut_r_0935_1000": float(series.quantile(0.10)) if status == "pass" else "",
                        "spike_cut_r_0935_1000": float(series.quantile(0.90)) if status == "pass" else "",
                        "threshold_source": "same_sleeve_prior_years_only",
                        "used_future_test_year_data": False,
                        "status": status,
                    }
                )
    return rows


def _universe_sleeve_map(universe: pd.DataFrame) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for _, row in universe.iterrows():
        code = str(row["code"])
        sleeves = [part for part in str(row.get("sleeves", "")).split(";") if part]
        result[code] = sorted(set(sleeves))
    return result


def _event_rows(features: list[dict[str, Any]], thresholds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    threshold_map = {
        (row["pool_scope"], row["scheme"], str(row["preview_date"]), int(row["test_year"]), row["sleeve"]): row
        for row in thresholds
        if row.get("status") == "pass"
    }
    rows: list[dict[str, Any]] = []
    for row in features:
        r = _safe_float(row.get("r_0935_1000"))
        if r is None:
            continue
        for pool_scope in POOL_SCOPES:
            for scheme in SCHEMES:
                threshold = threshold_map.get((pool_scope, scheme, str(row["preview_date"]), int(row["year"]), str(row["sleeve"])))
                if not threshold:
                    continue
                drop_cut = _safe_float(threshold.get("drop_cut_r_0935_1000"))
                spike_cut = _safe_float(threshold.get("spike_cut_r_0935_1000"))
                if drop_cut is not None and r <= drop_cut:
                    rows.append(_event_row(row, threshold, "morning30_drop_repair"))
                if spike_cut is not None and r >= spike_cut:
                    rows.append(_event_row(row, threshold, "morning30_spike_revert"))
    return rows


def _event_row(row: dict[str, Any], threshold: dict[str, Any], event_type: str) -> dict[str, Any]:
    return {
        "event_id": f"{threshold['threshold_id']}|{event_type}|{row['code']}|{row['trade_date']}",
        "event_type": event_type,
        "pool_scope": threshold["pool_scope"],
        "scheme": threshold["scheme"],
        "preview_date": row["preview_date"],
        "trade_date": row["trade_date"],
        "year": row["year"],
        "code": row["code"],
        "sleeve": row["sleeve"],
        "target_weight": row["target_weight"],
        "r_0935_1000": row.get("r_0935_1000"),
        "trained_cut": threshold["drop_cut_r_0935_1000"] if "drop" in event_type else threshold["spike_cut_r_0935_1000"],
        "next1_from_1000": row.get("next1_from_1000"),
        "next2_from_1000": row.get("next2_from_1000"),
        "threshold_source": threshold["threshold_source"],
        "future_return_used_for_signal": False,
        "new_buy_signal_used": False,
        "accepted": False,
    }


def _event_diagnostics(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        return []
    df = pd.DataFrame(events)
    rows = []
    for keys, group in df.groupby(["pool_scope", "scheme", "event_type"], sort=True):
        pool_scope, scheme, event_type = keys
        for horizon in HORIZONS:
            col = f"{horizon}_from_1000"
            series = pd.to_numeric(group[col], errors="coerce").dropna()
            rows.append(
                {
                    "pool_scope": pool_scope,
                    "scheme": scheme,
                    "event_type": event_type,
                    "horizon": horizon,
                    "event_count": int(len(series)),
                    "avg_forward_return": _mean(series),
                    "median_forward_return": float(series.median()) if len(series) else "",
                    "win_rate": _positive_rate(series),
                    "tstat": _tstat(series),
                    "reading": _event_reading(event_type, _mean(series), _positive_rate(series)),
                    "accepted": False,
                }
            )
    return rows


def _trade_log(features: list[dict[str, Any]], thresholds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not features:
        return []
    feature_df = pd.DataFrame(features)
    thresholds_df = pd.DataFrame([row for row in thresholds if row.get("status") == "pass"])
    rows = []
    for _, threshold in thresholds_df.iterrows():
        scope = str(threshold["pool_scope"])
        scheme = str(threshold["scheme"])
        preview_date = str(threshold["preview_date"])
        year = int(threshold["test_year"])
        sleeve = str(threshold["sleeve"])
        group = feature_df[
            feature_df["preview_date"].astype(str).eq(preview_date)
            & feature_df["year"].astype(int).eq(year)
            & feature_df["sleeve"].astype(str).eq(sleeve)
        ].copy()
        if group.empty:
            continue
        group["is_drop"] = pd.to_numeric(group["r_0935_1000"], errors="coerce") <= float(threshold["drop_cut_r_0935_1000"])
        group["is_spike"] = pd.to_numeric(group["r_0935_1000"], errors="coerce") >= float(threshold["spike_cut_r_0935_1000"])
        for (trade_date, day_group) in group.groupby("trade_date", sort=True):
            for horizon in HORIZONS:
                ret_col = f"{horizon}_from_1000"
                day_group = day_group[day_group[ret_col].notna()].copy()
                drops = day_group[day_group["is_drop"]].copy()
                if drops.empty:
                    continue
                for policy in POLICIES:
                    for cap in CAPS:
                        trade = _single_trade(day_group, drops, policy, cap, ret_col)
                        if not trade:
                            continue
                        trade.update(
                            {
                                "version_id": f"{scope}|{scheme}|{policy}|cap{int(cap*100)}|{horizon}",
                                "pool_scope": scope,
                                "scheme": scheme,
                                "preview_date": preview_date,
                                "trade_date": trade_date,
                                "year": year,
                                "sleeve": sleeve,
                                "horizon": horizon,
                                "accepted": False,
                            }
                        )
                        rows.append(trade)
    return sorted(rows, key=lambda row: (row["version_id"], row["trade_date"], row["sleeve"]))


def _single_trade(day_group: pd.DataFrame, drops: pd.DataFrame, policy: str, cap: float, ret_col: str) -> dict[str, Any] | None:
    sleeve_weight = float(pd.to_numeric(day_group["target_weight"], errors="coerce").fillna(0.0).sum())
    desired = float((pd.to_numeric(drops["target_weight"], errors="coerce").fillna(0.0) * BORROW_INTENSITY).sum())
    if desired <= 0 or sleeve_weight <= 0:
        return None
    drop_codes = set(drops["code"].astype(str))
    if policy == "paired_drop_spike_net0":
        sources = day_group[(~day_group["code"].astype(str).isin(drop_codes)) & day_group["is_spike"]].copy()
    else:
        sources = day_group[(~day_group["code"].astype(str).isin(drop_codes)) & (~day_group["is_drop"])].copy()
    if sources.empty:
        return None
    source_available = float(pd.to_numeric(sources["target_weight"], errors="coerce").fillna(0.0).sum()) * BORROW_INTENSITY
    actual = min(desired, cap * sleeve_weight, source_available)
    if actual <= 0:
        return None
    target_ret = _weighted_return(drops, ret_col, "target_weight")
    source_ret = _weighted_return(sources, ret_col, "target_weight")
    if target_ret is None or source_ret is None:
        return None
    gross = actual * (target_ret - source_ret)
    commission = actual * COMMISSION_RATE * 2.0
    net = gross - commission
    return {
        "funding_policy": policy,
        "borrow_cap_pct_of_sleeve": cap,
        "drop_count": int(len(drops)),
        "source_count": int(len(sources)),
        "desired_borrow_weight": desired,
        "actual_borrow_weight": actual,
        "target_avg_return": target_ret,
        "source_avg_return": source_ret,
        "gross_incremental_return": gross,
        "commission_drag": commission,
        "net_incremental_return": net,
        "win": net > 0,
        "same_sleeve_funding": True,
        "new_buy_signal_used": False,
        "temporary_borrow": True,
    }


def _metrics(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows = []
    for version, group in df.groupby("version_id", sort=True):
        net = pd.to_numeric(group["net_incremental_return"], errors="coerce").dropna()
        rows.append(
            {
                "version_id": version,
                "pool_scope": group.iloc[0]["pool_scope"],
                "scheme": group.iloc[0]["scheme"],
                "funding_policy": group.iloc[0]["funding_policy"],
                "borrow_cap_pct_of_sleeve": group.iloc[0]["borrow_cap_pct_of_sleeve"],
                "horizon": group.iloc[0]["horizon"],
                "trade_group_count": int(len(group)),
                "net_incremental_return": float(net.sum()) if len(net) else 0.0,
                "net_incremental_return_pct_points": float(net.sum()) * 100 if len(net) else 0.0,
                "avg_trade_net_incremental_return": _mean(net),
                "win_rate": _positive_rate(net),
                "tstat": _tstat(net),
                "reading": _metric_reading(float(net.sum()) * 100 if len(net) else 0.0, _positive_rate(net)),
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda row: (float(row["net_incremental_return_pct_points"]), float(row["win_rate"])), reverse=True)


def _cycle_metrics(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _group_metric_rows(trades, ["version_id", "preview_date", "year"], "cycle")


def _sleeve_metrics(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _group_metric_rows(trades, ["version_id", "sleeve"], "sleeve")


def _group_metric_rows(trades: list[dict[str, Any]], keys: list[str], level: str) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows = []
    for group_key, group in df.groupby(keys, sort=True):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        net = pd.to_numeric(group["net_incremental_return"], errors="coerce").dropna()
        row = {key: value for key, value in zip(keys, group_key)}
        row.update(
            {
                "level": level,
                "trade_group_count": int(len(group)),
                "net_incremental_return_pct_points": float(net.sum()) * 100 if len(net) else 0.0,
                "win_rate": _positive_rate(net),
            }
        )
        rows.append(row)
    return rows


def _blocker_resolution(
    stopped: list[dict[str, Any]],
    source_audit: list[dict[str, Any]],
    features: list[dict[str, Any]],
    thresholds: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    data_ok = all(row["status"] == "pass" for row in source_audit)
    threshold_pass = sum(1 for row in thresholds if row.get("status") == "pass")
    best = metrics[0] if metrics else {}
    rows = []
    for item in stopped:
        for blocker in item["blocked_by"].split(";"):
            if blocker in {"pre2020_5min_not_confirmed", "pre2014_2019_5min_source", "prior_year_sleeve_threshold_unavailable_for_2020"}:
                status = "resolved_by_local_5min" if data_ok and threshold_pass else "still_open"
                blocks = False if status == "resolved_by_local_5min" else True
                detail = f"local_5min features={len(features)}, pass_thresholds={threshold_pass}"
            elif blocker == "pre2021_or_future_independent_validation_missing":
                status = "resolved_for_data_gate_but_not_for_candidate_promotion" if metrics else "still_open"
                blocks = True
                detail = f"best_net_pct_points={best.get('net_incremental_return_pct_points', '')}; remains not accepted"
            elif blocker == "only_one_pre2021_validation_cycle":
                cycle_count = len({row["preview_date"] for row in features})
                status = "partially_resolved_two_preview_cycles" if cycle_count >= 2 else "still_open"
                blocks = True
                detail = f"preview_cycle_count={cycle_count}; still not full V57f equivalence"
            else:
                status = "still_open_governance_not_data"
                blocks = True
                detail = "pre2021 preview is not full V57f repaired historical rebalance chain"
            rows.append(
                {
                    "item_id": item["item_id"],
                    "prior_blocker": blocker,
                    "resolution_status": status,
                    "blocks_promotion": blocks,
                    "detail": detail,
                }
            )
    return rows


def _model_completion_matrix(
    stopped: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    resolution: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    best = metrics[0] if metrics else {}
    rows = []
    for item in stopped:
        item_res = [row for row in resolution if row["item_id"] == item["item_id"]]
        data_resolved = all(row["resolution_status"].startswith("resolved") or row["resolution_status"].startswith("partially") for row in item_res if "5min" in row["prior_blocker"] or "threshold" in row["prior_blocker"])
        rows.append(
            {
                "item_id": item["item_id"],
                "completion_status": "completed_with_local_5min",
                "data_blocker_resolved": data_resolved,
                "best_variant_after_completion": best.get("version_id", ""),
                "best_net_incremental_return_pct_points": best.get("net_incremental_return_pct_points", ""),
                "candidate_promotion_allowed": False,
                "accepted": False,
                "reason": "Data blocker is closed, but evidence remains pre2021 preview-level and not a full accepted strategy gate.",
            }
        )
    return rows


def _governance_audit(
    source_audit: list[dict[str, Any]],
    features: list[dict[str, Any]],
    thresholds: list[dict[str, Any]],
    gate_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = [
        {"audit_id": "local_5min_source_pass", "status": "pass" if all(row["status"] == "pass" for row in source_audit) else "fail", "detail": ""},
        {"audit_id": "pre2021_not_backtest_scope", "status": "pass", "detail": f"{PRE2021_START} to {PRE2021_END}; backtest is {BACKTEST_START} to {BACKTEST_END}"},
        {"audit_id": "candidate_preview_only", "status": "review", "detail": gate_summary.get("complete_v57f_repaired_multisleeve_pool_available", "")},
        {"audit_id": "thresholds_prior_years_only", "status": "pass" if all(str(row.get("used_future_test_year_data")) == "False" for row in thresholds) else "fail", "detail": ""},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": "V5 repaired universe / selected preview pool only"},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": "Only temporary same-sleeve weight borrowing diagnostics"},
        {"audit_id": "v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted", "status": "pass", "detail": False},
    ]
    if not features:
        rows.append({"audit_id": "candidate_features_available", "status": "fail", "detail": 0})
    return rows


def _pm_decision(
    metrics: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    resolution: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] == "fail"]
    best = metrics[0] if metrics else {}
    best_net = float(best.get("net_incremental_return_pct_points", 0.0) or 0.0)
    best_win = float(best.get("win_rate", 0.0) or 0.0)
    unresolved_data = [
        row
        for row in resolution
        if row["resolution_status"] == "still_open"
        and row["prior_blocker"] in {"pre2020_5min_not_confirmed", "pre2014_2019_5min_source", "prior_year_sleeve_threshold_unavailable_for_2020"}
    ]
    if failed or unresolved_data:
        decision = "blocked_by_remaining_data_or_pit_issue"
        validation_pass = False
        verdict = "blocked"
    elif best_net > 0 and best_win >= 0.5:
        decision = "pre2021_5min_data_blockers_resolved_positive_but_keep_diagnostic"
        validation_pass = False
        verdict = "data_resolved_positive_not_candidate"
    else:
        decision = "pre2021_5min_data_blockers_resolved_no_stable_edge_keep_diagnostic"
        validation_pass = False
        verdict = "data_resolved_no_candidate_edge"
    return [
        {
            "pm_gate_decision": decision,
            "independent_validation_pass": validation_pass,
            "formal_promotion_allowed": False,
            "best_variant": best.get("version_id", ""),
            "best_net_incremental_return_pct_points": best_net,
            "best_win_rate": best_win,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "verdict": verdict,
            "next_step": "keep_internal_subsleeve_mom12_70_30_primary; keep spike_borrowing as diagnostic/forward observation only",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "keep_internal_subsleeve_mom12_70_30_primary_forward_tracking",
            "allowed": True,
            "reason": "Pre-2021 5min repair does not displace V5f primary.",
        },
        {
            "priority": 2,
            "next_task": "archive_pre2020_5min_missing_blocker_as_resolved",
            "allowed": decision != "blocked_by_remaining_data_or_pit_issue",
            "reason": "Local 2013-2020 5min data is now ingested and used.",
        },
        {
            "priority": 3,
            "next_task": "spike_borrowing_forward_observation_only",
            "allowed": True,
            "reason": "Positive result, if any, remains too preview-limited for candidate promotion.",
        },
        {
            "priority": 4,
            "next_task": "promote_short_window_reversion_to_candidate",
            "allowed": False,
            "reason": "Pre-2021 preview cycles are not full V57f repaired historical rebalance equivalence.",
        },
    ]


def _blockers(governance: list[dict[str, Any]], resolution: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]}
        for row in governance
        if row["status"] == "fail"
    ]
    rows.extend(
        {
            "blocker_id": row["prior_blocker"],
            "severity": "governance",
            "status": "blocking_promotion_only",
            "detail": row["detail"],
        }
        for row in resolution
        if row.get("blocks_promotion") is True and row["resolution_status"] != "still_open"
    )
    return rows or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "detail": "No data blocker remains."}]


def _report(
    manifest: dict[str, Any],
    stopped: list[dict[str, Any]],
    event_diag: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    by_cycle: list[dict[str, Any]],
    by_sleeve: list[dict[str, Any]],
    resolution: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    best = metrics[0] if metrics else {}
    lines = [
        "# V5f Pre-2021 5min Blocker Completion",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Local 5min dataset: `{manifest.get('status')}`, rows `{manifest.get('total_5min_rows')}`.",
        f"- Best borrowing variant: `{best.get('version_id', '')}`",
        f"- Best net incremental return: `{float(best.get('net_incremental_return_pct_points', 0.0) or 0.0):.4f}` pct points.",
        f"- Best win rate: `{float(best.get('win_rate', 0.0) or 0.0):.2%}`.",
        "- Accepted: `False`; V57f core modified: `False`; threshold scan used: `False`.",
        "",
        "## Completed Items",
        "",
    ]
    for row in stopped:
        lines.append(f"- `{row['item_id']}`: {row['completion_action']}")
    lines.extend(["", "## Event Diagnostics", ""])
    for row in event_diag[:10]:
        lines.append(
            f"- `{row['pool_scope']}` / `{row['scheme']}` / `{row['event_type']}` / `{row['horizon']}`: n={row['event_count']}, avg={float(row['avg_forward_return'] or 0.0):.4%}, win={float(row['win_rate'] or 0.0):.2%}, `{row['reading']}`."
        )
    lines.extend(["", "## Best Variants", ""])
    for row in metrics[:8]:
        lines.append(
            f"- `{row['version_id']}`: net={float(row['net_incremental_return_pct_points']):.4f} pct, win={float(row['win_rate']):.2%}, trades={row['trade_group_count']}, `{row['reading']}`."
        )
    lines.extend(["", "## Cycle / Sleeve Notes", ""])
    for row in sorted(by_cycle, key=lambda x: float(x.get("net_incremental_return_pct_points", 0.0)), reverse=True)[:6]:
        lines.append(f"- Cycle `{row.get('preview_date')}` year `{row.get('year')}`: `{row.get('version_id')}` net={float(row.get('net_incremental_return_pct_points', 0.0)):.4f} pct.")
    for row in sorted(by_sleeve, key=lambda x: float(x.get("net_incremental_return_pct_points", 0.0)), reverse=True)[:6]:
        lines.append(f"- Sleeve `{row.get('sleeve')}`: `{row.get('version_id')}` net={float(row.get('net_incremental_return_pct_points', 0.0)):.4f} pct.")
    lines.extend(["", "## Blocker Resolution", ""])
    for row in resolution:
        lines.append(f"- `{row['item_id']}` / `{row['prior_blocker']}`: `{row['resolution_status']}`; blocks promotion `{row['blocks_promotion']}`.")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Pre-2021 5min Completion Rules",
            "",
            "- Use local 2013-2020 5min data only for pre-2021 validation.",
            "- Keep 2021-05-01 to 2026-05-31 as formal backtest, not validation.",
            "- Use V5 repaired universe / pre-2021 preview candidates only; no full-market selection.",
            "- Thresholds are prior-year same-sleeve q10/q90; no parameter scan.",
            "- Same-sleeve temporary borrowing is diagnostic only; no accepted or live approval.",
            "- Do not modify V57f core or V5f primary `internal_subsleeve_mom12_70_30`.",
            "",
        ]
    )


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
        if math.isnan(out):
            return None
        return out
    except Exception:
        return None


def _weighted_return(df: pd.DataFrame, ret_col: str, weight_col: str) -> float | None:
    temp = df[[ret_col, weight_col]].copy()
    temp[ret_col] = pd.to_numeric(temp[ret_col], errors="coerce")
    temp[weight_col] = pd.to_numeric(temp[weight_col], errors="coerce").fillna(0.0)
    temp = temp[temp[ret_col].notna()]
    if temp.empty:
        return None
    if float(temp[weight_col].sum()) == 0.0:
        return float(temp[ret_col].mean())
    return float((temp[ret_col] * temp[weight_col]).sum() / temp[weight_col].sum())


def _mean(series: Any) -> float | str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else ""


def _positive_rate(series: Any) -> float | str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float((values > 0).mean()) if len(values) else ""


def _tstat(series: Any) -> float | str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < 2:
        return ""
    std = float(values.std(ddof=1))
    if std == 0.0:
        return ""
    return float(values.mean() / (std / math.sqrt(len(values))))


def _event_reading(event_type: str, avg: Any, win: Any) -> str:
    avg_f = _safe_float(avg) or 0.0
    win_f = _safe_float(win) or 0.0
    if "drop" in event_type and avg_f > 0 and win_f >= 0.5:
        return "drop_repair_directionally_positive"
    if "spike" in event_type and avg_f < 0 and win_f < 0.5:
        return "spike_reversal_directionally_positive"
    return "mixed_or_weak"


def _metric_reading(net_pct: float, win: Any) -> str:
    win_f = _safe_float(win) or 0.0
    if net_pct > 0 and win_f >= 0.5:
        return "directionally_positive"
    if net_pct > 0:
        return "positive_sum_low_win_rate"
    return "negative_or_flat"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields or ["empty"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": now_utc(),
        "task": "v5f_pre2021_5min_blocker_completion",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("severity") == "fatal"]),
        "fatal_blockers": [row for row in blockers if row.get("severity") == "fatal"],
    }
    payload.update(extra)
    return payload


if __name__ == "__main__":
    print(json.dumps(run_v5f_pre2021_5min_blocker_completion(Path(".")), ensure_ascii=False, indent=2))
