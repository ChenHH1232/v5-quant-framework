from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_quality_value_mean_reversion_runner import (
    BACKTEST_END,
    BACKTEST_START,
    BASELINE,
    CHAMPION,
    REPAIRED_RUN,
    _max_drawdown,
    _safe_float,
)


OUT_DIR = Path("v5f_short_window_reversion_walk_forward_robustness") / "current"
FEATURES = (
    Path("v5f_short_window_reversion_diagnostic")
    / "current"
    / "v5f_short_window_reversion_minute_day_features.csv"
)
CHAMPION_DAILY = (
    Path("v5f_quality_value_mean_reversion")
    / "current"
    / "v5f_qv_mean_reversion_daily_returns.csv"
)
V4_ROOT = Path("D:/hh/codex/v4")

COMMISSION_RATE = 0.0003
OVERLAY_RELATIVE_WEIGHT = 0.10
SHOCK_QUANTILE_LOW = 0.10
SHOCK_QUANTILE_HIGH = 0.90
MIN_TRAIN_ROWS_PER_SLEEVE = 80

DROP_EVENT = "wf_morning30_drop_repair_next1_add10"
SPIKE_EVENT = "wf_morning30_spike_revert_next1_trim10"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_short_window_reversion_walk_forward(
    root: Path = Path("."),
    probe_baostock: bool = False,
) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_walk_forward_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_walk_forward_summary.json", summary)
        return summary

    features = _prepare_features(pd.read_csv(root / FEATURES, dtype={"trade_date": str, "code": str}))
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    champion_daily = pd.read_csv(root / CHAMPION_DAILY, dtype={"trade_date": str})
    champion_daily = champion_daily[champion_daily["version_id"].astype(str).eq(CHAMPION)].copy()

    data_audit = _data_source_audit(root, features)
    v4_audit = _v4_source_audit()
    fetch_feasibility = _baostock_pre2021_feasibility(probe_baostock)
    threshold_rows = _threshold_rows(features)
    events = _event_rows(features, threshold_rows)
    selected = _select_events(events)
    diagnostics = _event_diagnostics(selected)
    trades = _trade_log(selected, features)
    funding_audit = _funding_audit(trades)
    daily = _daily_returns(trades, baseline_daily, champion_daily)
    metrics = _metrics(daily, trades)
    yearly = _yearly(daily)
    sleeve = _sleeve_robustness(trades)
    threshold_stability = _threshold_stability(threshold_rows)
    pit = _pit_audit(threshold_rows)
    governance = _governance_audit(data_audit, selected, trades, fetch_feasibility)
    decision = _pm_decision(metrics, yearly, governance, fetch_feasibility)
    blockers_out = _blockers(governance, fetch_feasibility)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])

    _write_csv(out / "v5f_walk_forward_data_source_audit.csv", data_audit)
    _write_csv(out / "v5f_pre2021_v4_source_audit.csv", v4_audit)
    _write_csv(out / "v5f_pre2021_5min_fetch_feasibility.csv", fetch_feasibility)
    _write_csv(out / "v5f_sleeve_specific_thresholds.csv", threshold_rows)
    _write_csv(out / "v5f_sleeve_threshold_stability.csv", threshold_stability)
    _write_csv(out / "v5f_walk_forward_event_log.csv", selected)
    _write_csv(out / "v5f_walk_forward_event_diagnostics.csv", diagnostics)
    _write_csv(out / "v5f_walk_forward_trade_log.csv", trades)
    _write_csv(out / "v5f_walk_forward_funding_audit.csv", funding_audit)
    _write_csv(out / "v5f_walk_forward_daily_returns.csv", daily)
    _write_csv(out / "v5f_walk_forward_nav_metrics.csv", metrics)
    _write_csv(out / "v5f_walk_forward_yearly.csv", yearly)
    _write_csv(out / "v5f_walk_forward_sleeve_robustness.csv", sleeve)
    _write_csv(out / "v5f_walk_forward_pit_audit.csv", pit)
    _write_csv(out / "v5f_walk_forward_governance_audit.csv", governance)
    _write_csv(out / "v5f_walk_forward_pm_decision.csv", decision)
    _write_csv(out / "v5f_walk_forward_blockers.csv", blockers_out)
    _write_csv(out / "v5f_walk_forward_next_queue.csv", next_queue)
    (out / "v5f_walk_forward_report.md").write_text(
        _report(metrics, yearly, sleeve, threshold_stability, decision, fetch_feasibility),
        encoding="utf-8",
    )
    (out / "v5f_walk_forward_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best(metrics)
    summary = _summary(
        "completed_v5f_short_window_backtest_scope_internal_rolling_diagnostic",
        decision[0]["pm_gate_decision"],
        [],
        best_variant=best.get("version_id", ""),
        best_delta_vs_champion=float(best.get("delta_return_pct_points_vs_champion", 0.0) or 0.0),
        best_delta_vs_v57f=float(best.get("delta_return_pct_points_vs_v57f", 0.0) or 0.0),
        event_count=len(selected),
        trade_count=len(trades),
        threshold_source="prior_years_by_sleeve_only",
        backtest_scope_classification="historical_backtest_in_sample_engineering_window",
        oos_validation_used=False,
        rolling_validation_used=False,
        internal_rolling_diagnostic_used=True,
        baostock_probe_started=probe_baostock,
        pre2021_5min_status=_pre2021_status(fetch_feasibility),
    )
    _write_json(out / "v5f_walk_forward_summary.json", summary)
    return summary


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df[(df["trade_date"] >= BACKTEST_START) & (df["trade_date"] <= BACKTEST_END)].copy()
    df = df.sort_values(["code", "holding_start_date", "next_rebalance_date", "trade_date"]).reset_index(drop=True)
    for col in [
        "r_0935_1000",
        "r_0935_1030",
        "r_1000_1455",
        "r_prevclose_1455",
        "r_1455_vwap",
        "next1_from_1000",
        "next2_from_1000",
        "target_weight",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    cycle_cols = ["code", "holding_start_date", "next_rebalance_date"]
    df["next1_date"] = df.groupby(cycle_cols)["trade_date"].shift(-1)
    df["year"] = df["trade_date"].astype(str).str.slice(0, 4).astype(int)
    df["sleeve"] = df["sleeve"].astype(str)
    return df


def _threshold_rows(features: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    years = sorted(features["year"].dropna().astype(int).unique().tolist())
    sleeves = sorted(features["sleeve"].dropna().astype(str).unique().tolist())
    for scheme in ["anchored_prior_years", "rolling_2y_prior_years"]:
        for test_year in years:
            for sleeve in sleeves:
                if scheme == "anchored_prior_years":
                    train = features[(features["year"] < test_year) & (features["sleeve"].eq(sleeve))]
                else:
                    train = features[
                        (features["year"] < test_year)
                        & (features["year"] >= test_year - 2)
                        & (features["sleeve"].eq(sleeve))
                    ]
                train_series = pd.to_numeric(train["r_0935_1000"], errors="coerce").dropna()
                status = "pass" if len(train_series) >= MIN_TRAIN_ROWS_PER_SLEEVE else "insufficient_prior_train_rows"
                lower = float(train_series.quantile(SHOCK_QUANTILE_LOW)) if status == "pass" else math.nan
                upper = float(train_series.quantile(SHOCK_QUANTILE_HIGH)) if status == "pass" else math.nan
                rows.append(
                    {
                        "threshold_id": f"{scheme}|{test_year}|{sleeve}",
                        "scheme": scheme,
                        "test_year": test_year,
                        "sleeve": sleeve,
                        "train_start": str(train["trade_date"].min()) if not train.empty else "",
                        "train_end": str(train["trade_date"].max()) if not train.empty else "",
                        "train_row_count": int(len(train_series)),
                        "drop_lower_quantile": SHOCK_QUANTILE_LOW,
                        "spike_upper_quantile": SHOCK_QUANTILE_HIGH,
                        "drop_cut_r_0935_1000": lower,
                        "spike_cut_r_0935_1000": upper,
                        "threshold_source": "prior_years_same_sleeve_only",
                        "used_future_test_year_data": False,
                        "status": status,
                    }
                )
    return rows


def _event_rows(features: pd.DataFrame, thresholds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    threshold_map = {
        (row["scheme"], int(row["test_year"]), row["sleeve"]): row
        for row in thresholds
        if row["status"] == "pass"
    }
    rows: list[dict[str, Any]] = []
    for _, row in features.iterrows():
        year = int(row["year"])
        sleeve = str(row["sleeve"])
        r = _safe_float(row.get("r_0935_1000"))
        next1 = _safe_float(row.get("next1_from_1000"))
        next1_date = row.get("next1_date", "")
        if r is None or next1 is None or pd.isna(next1_date):
            continue
        for scheme in ["anchored_prior_years", "rolling_2y_prior_years"]:
            threshold = threshold_map.get((scheme, year, sleeve))
            if not threshold:
                continue
            lower = _safe_float(threshold.get("drop_cut_r_0935_1000"))
            upper = _safe_float(threshold.get("spike_cut_r_0935_1000"))
            if lower is not None and r <= lower:
                rows.append(_event_row(row, scheme, DROP_EVENT, r, next1, str(next1_date), lower, "below_sleeve_prior_q10"))
            if upper is not None and r >= upper:
                rows.append(_event_row(row, scheme, SPIKE_EVENT, r, next1, str(next1_date), upper, "above_sleeve_prior_q90"))
    return rows


def _event_row(
    row: pd.Series,
    scheme: str,
    event_type: str,
    trigger_return: float,
    next1_return: float,
    next1_date: str,
    trained_cut: float,
    trigger_reason: str,
) -> dict[str, Any]:
    return {
        "event_id": f"{scheme}|{event_type}|{row['code']}|{row['trade_date']}",
        "scheme": scheme,
        "event_type": event_type,
        "code": row["code"],
        "trade_date": row["trade_date"],
        "close_date": next1_date,
        "test_year": int(row["year"]),
        "sleeve": row["sleeve"],
        "holding_start_date": row["holding_start_date"],
        "next_rebalance_date": row["next_rebalance_date"],
        "target_weight": _safe_float(row.get("target_weight")) or 0.0,
        "trigger_return_r_0935_1000": trigger_return,
        "trained_sleeve_cut": trained_cut,
        "trigger_reason": trigger_reason,
        "next1_from_1000": next1_return,
        "observation_time": "10:00:00",
        "threshold_source": "prior_years_same_sleeve_only",
        "new_buy_signal_allowed": False,
        "accepted": False,
    }


def _select_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    variants = {
        "wf_anchored_drop_add10_next1": ("anchored_prior_years", {DROP_EVENT}),
        "wf_anchored_spike_trim10_next1": ("anchored_prior_years", {SPIKE_EVENT}),
        "wf_anchored_symmetric_shock_next1": ("anchored_prior_years", {DROP_EVENT, SPIKE_EVENT}),
        "wf_rolling2y_drop_add10_next1": ("rolling_2y_prior_years", {DROP_EVENT}),
        "wf_rolling2y_spike_trim10_next1": ("rolling_2y_prior_years", {SPIKE_EVENT}),
        "wf_rolling2y_symmetric_shock_next1": ("rolling_2y_prior_years", {DROP_EVENT, SPIKE_EVENT}),
    }
    for version, (scheme, allowed) in variants.items():
        last_close_by_code: dict[str, str] = {}
        for event in sorted(events, key=lambda r: (r["trade_date"], r["code"], r["event_type"])):
            if event["scheme"] != scheme or event["event_type"] not in allowed:
                continue
            last_close = last_close_by_code.get(str(event["code"]), "")
            if last_close and str(event["trade_date"]) <= last_close:
                continue
            selected = dict(event)
            selected["version_id"] = version
            selected["selected_return"] = event["next1_from_1000"]
            selected["close_horizon"] = "next1"
            rows.append(selected)
            last_close_by_code[str(event["code"])] = str(event["close_date"])
    return rows


def _funding_returns(features: pd.DataFrame) -> dict[tuple[str, str, str], float]:
    out: dict[tuple[str, str, str], float] = {}
    for (trade_date, sleeve), group in features.groupby(["trade_date", "sleeve"], sort=False):
        returns = pd.to_numeric(group["next1_from_1000"], errors="coerce")
        weights = pd.to_numeric(group["target_weight"], errors="coerce").fillna(0.0)
        codes = group["code"].astype(str)
        for code in codes:
            mask = codes.ne(code) & returns.notna()
            if not mask.any():
                out[(str(trade_date), str(sleeve), str(code))] = 0.0
                continue
            w = weights[mask]
            r = returns[mask]
            out[(str(trade_date), str(sleeve), str(code))] = (
                float((r * w).sum() / w.sum()) if float(w.sum()) else float(r.mean())
            )
    return out


def _trade_log(selected: list[dict[str, Any]], features: pd.DataFrame) -> list[dict[str, Any]]:
    funding = _funding_returns(features)
    rows: list[dict[str, Any]] = []
    for event in selected:
        stock_return = _safe_float(event.get("selected_return"))
        if stock_return is None:
            continue
        funding_return = funding.get((str(event["trade_date"]), str(event["sleeve"]), str(event["code"])), 0.0)
        overlay_weight = float(event["target_weight"]) * OVERLAY_RELATIVE_WEIGHT
        if event["event_type"] == DROP_EVENT:
            gross = overlay_weight * (stock_return - funding_return)
            action = "temporary_add"
            excess = stock_return - funding_return
        else:
            gross = overlay_weight * (funding_return - stock_return)
            action = "temporary_trim"
            excess = funding_return - stock_return
        commission = overlay_weight * COMMISSION_RATE * 2.0
        rows.append(
            {
                "version_id": event["version_id"],
                "event_id": event["event_id"],
                "scheme": event["scheme"],
                "event_type": event["event_type"],
                "action": action,
                "code": event["code"],
                "sleeve": event["sleeve"],
                "open_date": event["trade_date"],
                "close_date": event["close_date"],
                "observation_time": event["observation_time"],
                "target_weight": event["target_weight"],
                "overlay_weight": overlay_weight,
                "stock_next1_return": stock_return,
                "funding_next1_return": funding_return,
                "excess_return_vs_funding": excess,
                "gross_incremental_return": gross,
                "commission_drag": commission,
                "net_incremental_return": gross - commission,
                "same_sleeve_funding": True,
                "new_buy_signal_used": False,
                "accepted": False,
            }
        )
    return rows


def _daily_returns(
    trades: list[dict[str, Any]],
    baseline_daily: pd.DataFrame,
    champion_daily: pd.DataFrame,
) -> list[dict[str, Any]]:
    baseline_daily = baseline_daily[(baseline_daily["trade_date"] >= BACKTEST_START) & (baseline_daily["trade_date"] <= BACKTEST_END)].copy()
    champion_daily = champion_daily[(champion_daily["trade_date"] >= BACKTEST_START) & (champion_daily["trade_date"] <= BACKTEST_END)].copy()
    baseline_ret = baseline_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    champion_ret = champion_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    trade_df = pd.DataFrame(trades)
    variants = [
        "wf_anchored_drop_add10_next1",
        "wf_anchored_spike_trim10_next1",
        "wf_anchored_symmetric_shock_next1",
        "wf_rolling2y_drop_add10_next1",
        "wf_rolling2y_spike_trim10_next1",
        "wf_rolling2y_symmetric_shock_next1",
    ]
    rows: list[dict[str, Any]] = []
    for version in variants:
        overlay_by_date: dict[str, float] = {}
        if not trade_df.empty:
            grouped = trade_df[trade_df["version_id"].eq(version)].groupby("close_date")["net_incremental_return"].sum()
            overlay_by_date = {str(date): float(value) for date, value in grouped.items()}
        for base_id, base_map in [(BASELINE, baseline_ret), (CHAMPION, champion_ret)]:
            nav = 1.0
            for date in sorted(baseline_ret):
                base_return = base_map.get(date, baseline_ret[date])
                overlay = overlay_by_date.get(date, 0.0)
                ret = base_return + overlay
                nav *= 1.0 + ret
                rows.append(
                    {
                        "trade_date": date,
                        "version_id": f"{version}_on_{'v57f' if base_id == BASELINE else 'momentum_champion_estimate'}",
                        "base_reference": base_id,
                        "strategy_return": ret,
                        "strategy_nav": nav,
                        "base_return": base_return,
                        "overlay_return": overlay,
                        "accepted": False,
                    }
                )
    for base_id, base_map in [(BASELINE, baseline_ret), (CHAMPION, champion_ret)]:
        nav = 1.0
        for date in sorted(baseline_ret):
            base_return = base_map.get(date, baseline_ret[date])
            nav *= 1.0 + base_return
            rows.append(
                {
                    "trade_date": date,
                    "version_id": base_id,
                    "base_reference": base_id,
                    "strategy_return": base_return,
                    "strategy_nav": nav,
                    "base_return": base_return,
                    "overlay_return": 0.0,
                    "accepted": False,
                }
            )
    return rows


def _metrics(rows: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    trade_df = pd.DataFrame(trades)
    out: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        group = group.sort_values("trade_date")
        navs = pd.to_numeric(group["strategy_nav"], errors="coerce").tolist()
        rets = pd.to_numeric(group["strategy_return"], errors="coerce").tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0 if navs else 0.0
        vol = pd.Series(rets).std() * (252**0.5) if rets else 0.0
        event_count = int(len(trade_df[trade_df["version_id"].eq(version.replace("_on_v57f", "").replace("_on_momentum_champion_estimate", ""))])) if not trade_df.empty else 0
        out.append(
            {
                "version_id": version,
                "base_reference": group.iloc[0]["base_reference"],
                "strategy_return": navs[-1] - 1.0 if navs else 0.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs) if navs else 0.0,
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "overlay_return_sum": pd.to_numeric(group["overlay_return"], errors="coerce").sum(),
                "event_count": event_count,
                "threshold_source": "prior_years_by_sleeve_only",
                "accepted": False,
            }
        )
    base = next(row for row in out if row["version_id"] == BASELINE)
    champ = next(row for row in out if row["version_id"] == CHAMPION)
    for row in out:
        row["delta_return_pct_points_vs_v57f"] = (float(row["strategy_return"]) - float(base["strategy_return"])) * 100
        row["delta_return_pct_points_vs_champion"] = (float(row["strategy_return"]) - float(champ["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_v57f"] = (float(row["max_drawdown"]) - float(base["max_drawdown"])) * 100
        row["delta_max_drawdown_pct_points_vs_champion"] = (
            float(row["max_drawdown"]) - float(champ["max_drawdown"])
        ) * 100
    return sorted(out, key=lambda row: float(row["delta_return_pct_points_vs_champion"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].astype(str).str.slice(0, 4)
    out: list[dict[str, Any]] = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append(
            {
                "version_id": version,
                "year": year,
                "period_return": (1 + pd.to_numeric(group["strategy_return"], errors="coerce")).prod() - 1,
                "overlay_return_sum": pd.to_numeric(group["overlay_return"], errors="coerce").sum(),
                "trade_days": int(len(group)),
            }
        )
    return out


def _event_diagnostics(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        return []
    df = pd.DataFrame(events)
    rows: list[dict[str, Any]] = []
    for (scheme, event_type, year), group in df.groupby(["scheme", "event_type", "test_year"], sort=True):
        rows.append(
            {
                "scheme": scheme,
                "event_type": event_type,
                "test_year": year,
                "event_count": int(len(group)),
                "unique_stock_count": int(group["code"].nunique()),
                "avg_trigger_return": _mean(group["trigger_return_r_0935_1000"]),
                "avg_next1_from_1000": _mean(group["next1_from_1000"]),
                "positive_next1_rate": _positive_rate(group["next1_from_1000"]),
                "threshold_source": "prior_years_same_sleeve_only",
            }
        )
    return rows


def _sleeve_robustness(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows: list[dict[str, Any]] = []
    for (version, event_type, sleeve), group in df.groupby(["version_id", "event_type", "sleeve"], sort=True):
        rows.append(
            {
                "version_id": version,
                "event_type": event_type,
                "sleeve": sleeve,
                "event_count": int(len(group)),
                "unique_stock_count": int(group["code"].nunique()),
                "gross_incremental_return_pct_points": pd.to_numeric(group["gross_incremental_return"], errors="coerce").sum() * 100,
                "commission_drag_pct_points": pd.to_numeric(group["commission_drag"], errors="coerce").sum() * 100,
                "net_incremental_return_pct_points": pd.to_numeric(group["net_incremental_return"], errors="coerce").sum() * 100,
                "avg_excess_return_vs_funding": _mean(group["excess_return_vs_funding"]),
                "positive_excess_rate": _positive_rate(group["excess_return_vs_funding"]),
            }
        )
    return rows


def _threshold_stability(thresholds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(thresholds)
    df = df[df["status"].eq("pass")].copy()
    if df.empty:
        return []
    rows: list[dict[str, Any]] = []
    for (scheme, sleeve), group in df.groupby(["scheme", "sleeve"], sort=True):
        rows.append(
            {
                "scheme": scheme,
                "sleeve": sleeve,
                "test_year_count": int(group["test_year"].nunique()),
                "avg_train_rows": _mean(group["train_row_count"]),
                "avg_drop_cut": _mean(group["drop_cut_r_0935_1000"]),
                "avg_spike_cut": _mean(group["spike_cut_r_0935_1000"]),
                "min_drop_cut": pd.to_numeric(group["drop_cut_r_0935_1000"], errors="coerce").min(),
                "max_spike_cut": pd.to_numeric(group["spike_cut_r_0935_1000"], errors="coerce").max(),
                "sleeve_specific_sensitivity_used": True,
            }
        )
    return rows


def _funding_audit(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows: list[dict[str, Any]] = []
    for (version, open_date, sleeve), group in df.groupby(["version_id", "open_date", "sleeve"], sort=True):
        total = pd.to_numeric(group["overlay_weight"], errors="coerce").sum()
        rows.append(
            {
                "version_id": version,
                "open_date": open_date,
                "sleeve": sleeve,
                "event_count": int(len(group)),
                "total_overlay_weight": total,
                "max_single_overlay_weight": pd.to_numeric(group["overlay_weight"], errors="coerce").max(),
                "funding_policy": "same_sleeve_non_triggered_holdings",
                "funding_weight_review_required": bool(total > 0.10),
            }
        )
    return rows


def _data_source_audit(root: Path, features: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "source_id": "v57f_repaired_full_holding_5min_features",
            "path": str(root / FEATURES),
            "role": "main_walk_forward_feature_source",
            "start_date": str(features["trade_date"].min()) if not features.empty else "",
            "end_date": str(features["trade_date"].max()) if not features.empty else "",
            "row_count": int(len(features)),
            "stock_count": int(features["code"].nunique()) if not features.empty else 0,
            "sleeve_count": int(features["sleeve"].nunique()) if not features.empty else 0,
            "is_repaired_v57f_main_backtest_window": True,
            "treated_as_independent_oos": False,
            "status": "pass" if not features.empty else "blocked_empty_features",
        },
        {
            "source_id": "v57f_repaired_baseline_daily_returns",
            "path": str(root / REPAIRED_RUN / "daily_returns.csv"),
            "role": "baseline_reference",
            "start_date": BACKTEST_START,
            "end_date": BACKTEST_END,
            "row_count": "",
            "stock_count": "",
            "sleeve_count": "",
            "is_repaired_v57f_main_backtest_window": True,
            "treated_as_independent_oos": False,
            "status": "pass",
        },
    ]


def _v4_source_audit() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not V4_ROOT.exists():
        return [
            {
                "source_id": "v4_root",
                "path": str(V4_ROOT),
                "role": "pre2021_predecessor_source",
                "status": "missing",
                "notes": "V4 folder not found.",
            }
        ]
    daily_files = list(V4_ROOT.glob("phase_2_momentum/raw_downloads/momentum_price_repair_v1/*/daily_price_with_date.csv"))
    minute_files = [p for p in V4_ROOT.rglob("*") if p.is_file() and ("5min" in p.name.lower() or "minute" in p.name.lower())]
    for source_id, rel_path in [
        ("v4_momentum_pre2021_state_review", "phase_2_momentum/momentum_pre2021_state_review_v1.csv"),
        ("v4_momentum_pre2021_mechanism_review", "phase_2_momentum/momentum_pre2021_mechanism_review_v1.csv"),
        ("v4_pre2021_rolling_validation", "phase_1_fundamental/pre2021_rolling_validation_v1_results.csv"),
    ]:
        path = V4_ROOT / rel_path
        rows.append(
            {
                "source_id": source_id,
                "path": str(path),
                "role": "pre2021_daily_or_monthly_predecessor_proxy",
                "status": "available" if path.exists() else "missing",
                "notes": "Can explain pre-2021 bank/core momentum mechanism, but is not exact V57f repaired 5min evidence.",
            }
        )
    rows.append(
        {
            "source_id": "v4_momentum_daily_price_files",
            "path": str(V4_ROOT / "phase_2_momentum/raw_downloads/momentum_price_repair_v1"),
            "role": "pre2021_daily_price_source",
            "status": "available" if daily_files else "missing",
            "file_count": len(daily_files),
            "notes": "Daily prices exist for predecessor bank momentum work.",
        }
    )
    rows.append(
        {
            "source_id": "v4_local_5min_files",
            "path": str(V4_ROOT),
            "role": "pre2021_intraday_source",
            "status": "available" if minute_files else "missing",
            "file_count": len(minute_files),
            "notes": "No complete local V4 5min dataset is required to validate V57f repaired directly.",
        }
    )
    return rows


def _baostock_pre2021_feasibility(probe: bool) -> list[dict[str, Any]]:
    if not probe:
        return [
            {
                "probe_id": "baostock_probe_not_run_in_unit_mode",
                "code": "",
                "start_date": "",
                "end_date": "",
                "row_count": "",
                "status": "not_run",
                "notes": "Set probe_baostock=True during execution to test external source availability.",
            }
        ]
    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_baostock_probe_worker, args=(queue,))
    proc.start()
    proc.join(30)
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        return [
            {
                "probe_id": "baostock_external_timeout",
                "code": "",
                "start_date": "",
                "end_date": "",
                "row_count": 0,
                "status": "timeout",
                "notes": "BaoStock did not return within 30 seconds; walk-forward packet completed without external pre-2021 5min confirmation.",
            }
        ]
    if queue.empty():
        return [
            {
                "probe_id": "baostock_probe_no_result",
                "code": "",
                "start_date": "",
                "end_date": "",
                "row_count": 0,
                "status": "failed",
                "notes": "BaoStock probe process exited without returning a result.",
            }
        ]
    return queue.get()


def _baostock_probe_worker(queue: mp.Queue) -> None:
    try:
        import baostock as bs
    except Exception as exc:
        queue.put([
            {
                "probe_id": "baostock_import",
                "code": "",
                "start_date": "",
                "end_date": "",
                "row_count": 0,
                "status": "failed",
                "notes": str(exc)[:300],
            }
        ])
        return
    rows: list[dict[str, Any]] = []
    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    login = bs.login()
    try:
        if getattr(login, "error_code", "1") != "0":
            queue.put([
                {
                    "probe_id": "baostock_login",
                    "code": "",
                    "start_date": "",
                    "end_date": "",
                    "row_count": 0,
                    "status": "failed",
                    "notes": getattr(login, "error_msg", ""),
                }
            ])
            return
        for probe_id, code, date in [
            ("pre2019_probe", "sh.600036", "2018-01-02"),
            ("pre2021_probe", "sh.600036", "2020-12-01"),
            ("main_window_probe", "sh.600036", "2021-05-06"),
        ]:
            rs = bs.query_history_k_data_plus(code, fields, start_date=date, end_date=date, frequency="5", adjustflag="3")
            count = 0
            while rs.error_code == "0" and rs.next():
                count += 1
            status = "available" if rs.error_code == "0" and count > 0 else ("empty" if rs.error_code == "0" else "failed")
            rows.append(
                {
                    "probe_id": probe_id,
                    "code": code,
                    "start_date": date,
                    "end_date": date,
                    "row_count": count,
                    "status": status,
                    "notes": "BaoStock 5min sample query; used for feasibility only, not threshold fitting.",
                }
            )
    finally:
        try:
            bs.logout()
        except Exception:
            pass
    queue.put(rows)


def _pit_audit(thresholds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(thresholds)
    future_rows = int(df["used_future_test_year_data"].astype(bool).sum()) if "used_future_test_year_data" in df else 0
    return [
        {
            "audit_id": "threshold_training_window",
            "status": "pass" if future_rows == 0 else "fail",
            "future_data_rows": future_rows,
            "description": "Shock thresholds are generated from prior years in the same sleeve only.",
        },
        {
            "audit_id": "signal_observation_time",
            "status": "pass",
            "future_data_rows": 0,
            "description": "Signal uses 09:35-10:00 bars only; next-day returns are evaluation and NAV impact.",
        },
        {
            "audit_id": "stock_pool_boundary",
            "status": "pass",
            "future_data_rows": 0,
            "description": "Only V57f repaired historical holding stock-days are used; no full-market selection.",
        },
    ]


def _governance_audit(
    data_audit: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    fetch_feasibility: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    trade_df = pd.DataFrame(trades)
    selected_df = pd.DataFrame(selected)
    max_sleeve_overlay = 0.0
    if not trade_df.empty:
        max_sleeve_overlay = float(
            trade_df.groupby(["version_id", "open_date", "sleeve"])["overlay_weight"].sum().max()
        )
    pre2019_available = any(row.get("probe_id") == "pre2019_probe" and row.get("status") == "available" for row in fetch_feasibility)
    return [
        {
            "audit_id": "repaired_v57f_used",
            "status": "pass" if all(row["status"] == "pass" for row in data_audit if row["source_id"].startswith("v57f")) else "fail",
            "value": "startup_preload_repaired_baseline",
            "description": "Main comparison uses repaired V57f baseline.",
        },
        {
            "audit_id": "no_full_market_selection",
            "status": "pass",
            "value": bool(selected_df.empty or selected_df["new_buy_signal_allowed"].astype(str).str.lower().eq("false").all()),
            "description": "No non-V57f stock is introduced.",
        },
        {
            "audit_id": "no_v57f_core_modified",
            "status": "pass",
            "value": False,
            "description": "The runner only creates an overlay diagnostic packet.",
        },
        {
            "audit_id": "same_sleeve_funding_only",
            "status": "pass" if trade_df.empty or trade_df["same_sleeve_funding"].astype(bool).all() else "fail",
            "value": True,
            "description": "Temporary add/trim is funded inside the same sleeve.",
        },
        {
            "audit_id": "max_daily_sleeve_overlay_review",
            "status": "pass" if max_sleeve_overlay <= 0.10 else "review_required",
            "value": max_sleeve_overlay,
            "description": "Review whether clustered same-sleeve shock events exceed the intended 10% overlay envelope.",
        },
        {
            "audit_id": "pre2014_2019_5min_source",
            "status": "pass" if pre2019_available else "review_required",
            "value": pre2019_available,
            "description": "BaoStock sample indicates whether 2014-2019 5min can be used for a true pre-2021 intraday predecessor test.",
        },
    ]


def _pm_decision(
    metrics: list[dict[str, Any]],
    yearly: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    fetch_feasibility: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    best = _best(metrics)
    best_delta = float(best.get("delta_return_pct_points_vs_champion", 0.0) or 0.0)
    yearly_df = pd.DataFrame(yearly)
    positive_year_rate = 0.0
    if not yearly_df.empty and best:
        base = yearly_df[yearly_df["version_id"].eq(CHAMPION)][["year", "period_return"]].rename(columns={"period_return": "champ_return"})
        candidate = yearly_df[yearly_df["version_id"].eq(best["version_id"])][["year", "period_return"]]
        merged = candidate.merge(base, on="year", how="inner")
        if not merged.empty:
            positive_year_rate = float((merged["period_return"] > merged["champ_return"]).mean())
    hard_fail = any(row["status"] == "fail" for row in governance)
    pre2019_available = any(row.get("probe_id") == "pre2019_probe" and row.get("status") == "available" for row in fetch_feasibility)
    if hard_fail:
        decision = "blocked_by_pit_or_governance_issue"
    elif best_delta > 0.50 and positive_year_rate >= 0.60 and pre2019_available:
        decision = "diagnostic_positive_requires_pre2021_or_forward_confirmation_not_accepted"
    elif best_delta > 0.0:
        decision = "diagnostic_only_backtest_scope_no_oos_validation"
    else:
        decision = "diagnostic_only_no_backtest_edge"
    return [
        {
            "pm_gate_decision": decision,
            "best_variant": best.get("version_id", ""),
            "best_delta_return_pct_points_vs_champion": best_delta,
            "positive_year_rate_vs_champion": positive_year_rate,
            "pre2021_5min_confirmed": pre2019_available,
            "backtest_scope_classification": "historical_backtest_in_sample_engineering_window",
            "oos_validation_used": False,
            "rolling_validation_used": False,
            "internal_rolling_diagnostic_used": True,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "notes": "2021-05-06 to 2026-05-31 is the repaired V57f backtest window. Prior-year splits inside this window are internal diagnostics, not OOS validation.",
        }
    ]


def _blockers(governance: list[dict[str, Any]], fetch_feasibility: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in governance:
        if row["status"] in {"fail", "review_required"}:
            rows.append(
                {
                    "blocker_id": row["audit_id"],
                    "severity": "fatal" if row["status"] == "fail" else "research_limit",
                    "status": row["status"],
                    "description": row["description"],
                }
            )
    if fetch_feasibility and any(row.get("probe_id") == "pre2019_probe" and row.get("status") == "empty" for row in fetch_feasibility):
        rows.append(
            {
                "blocker_id": "pre2014_2019_baostock_5min_empty",
                "severity": "research_limit",
                "status": "not_backtest_blocker",
                "description": "BaoStock sample returned no 5min rows for 2018; earlier predecessor intraday walk-forward cannot be completed from this source without another data provider.",
            }
        )
    return rows


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "next_001",
            "task": "If desired, open separate pre2021 intraday data provider audit for V4 bank/core predecessor pool.",
            "priority": "medium",
            "status": "queued" if "pre2021_5min_unconfirmed" in decision else "optional",
        },
        {
            "queue_id": "next_002",
            "task": "Keep V5f internal subsleeve momentum champion as primary candidate; use short-window reversion only as diagnostic unless forward evidence confirms.",
            "priority": "high",
            "status": "queued",
        },
        {
            "queue_id": "next_003",
            "task": "Do not tune shock quantiles or fixed pct thresholds inside the repaired V57f backtest window.",
            "priority": "high",
            "status": "guardrail",
        },
    ]


def _report(
    metrics: list[dict[str, Any]],
    yearly: list[dict[str, Any]],
    sleeve: list[dict[str, Any]],
    threshold_stability: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    fetch_feasibility: list[dict[str, Any]],
) -> str:
    best = _best(metrics)
    pre_status = _pre2021_status(fetch_feasibility)
    lines = [
        "# V5f Short-Window Reversion Backtest-Scope Internal Diagnostic",
        "",
        "Scope: repaired V57f holding pool only. The 2021-05-06 to 2026-05-31 window is historical backtest scope, not validation or OOS evidence.",
        "",
        "Key result:",
        f"- best variant: `{best.get('version_id', '')}`",
        f"- delta vs V5f momentum champion: `{float(best.get('delta_return_pct_points_vs_champion', 0.0) or 0.0):.4f}` pct points",
        f"- delta vs repaired V57f: `{float(best.get('delta_return_pct_points_vs_v57f', 0.0) or 0.0):.4f}` pct points",
        f"- pre-2021 5min feasibility: `{pre_status}`",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        "",
        "Method:",
        "- Shock thresholds are sleeve-specific and trained from prior years inside the same backtest window.",
        "- These prior-year splits are internal rolling diagnostics only, not formal walk-forward validation.",
        "- 2021 is used as early in-window seed where prior V57f 5min history is unavailable.",
        "- Drop and spike branches both close at next trading day and use same-sleeve funding.",
        "- V4 evidence is treated as predecessor proxy only, not repaired V57f out-of-sample proof.",
        "",
        "Top metrics:",
    ]
    for row in metrics[:6]:
        lines.append(
            f"- `{row['version_id']}` return `{float(row['strategy_return']):.4f}`, "
            f"delta vs champion `{float(row['delta_return_pct_points_vs_champion']):.4f}` pct, "
            f"events `{row.get('event_count', 0)}`"
        )
    lines += ["", "Sleeve threshold stability:"]
    for row in threshold_stability[:12]:
        lines.append(
            f"- `{row['scheme']}` `{row['sleeve']}` drop_cut_avg `{float(row['avg_drop_cut']):.4f}`, "
            f"spike_cut_avg `{float(row['avg_spike_cut']):.4f}`"
        )
    if sleeve:
        lines += ["", "Sleeve contribution highlights:"]
        for row in sorted(sleeve, key=lambda r: float(r["net_incremental_return_pct_points"]), reverse=True)[:8]:
            lines.append(
                f"- `{row['version_id']}` `{row['sleeve']}` `{row['event_type']}` "
                f"net `{float(row['net_incremental_return_pct_points']):.4f}` pct points, events `{row['event_count']}`"
            )
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# Agent Execution Rules",
            "",
            "- Use startup preload repaired V57f baseline only.",
            "- Treat 2021-05-06 to 2026-05-31 as the main backtest window, not independent proof.",
            "- Prior-year splits inside 2021-2026 are internal diagnostics only, not rolling validation.",
            "- Use prior-year, same-sleeve thresholds only; no full-sample quantiles.",
            "- Do not select from full market.",
            "- Do not change V57f core.",
            "- Do not mark accepted or live approved.",
        ]
    ) + "\n"


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        FEATURES,
        REPAIRED_RUN / "daily_returns.csv",
        CHAMPION_DAILY,
    ]
    return [
        {
            "blocker_id": f"missing_{path.name}",
            "severity": "fatal",
            "status": "blocking",
            "description": str(path),
        }
        for path in required
        if not (root / path).exists()
    ]


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_short_window_reversion_walk_forward_robustness",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "full_market_selection_used": False,
        "new_buy_signal_used": False,
        "backtest_scope_classification": "historical_backtest_in_sample_engineering_window",
        "oos_validation_used": False,
        "rolling_validation_used": False,
        "internal_rolling_diagnostic_used": True,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "fatal_blockers": [row for row in blockers if row.get("severity") == "fatal"],
        **extra,
    }


def _best(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        row
        for row in metrics
        if row["version_id"] not in {BASELINE, CHAMPION}
        and row["version_id"].endswith("_on_momentum_champion_estimate")
    ]
    if not candidates:
        return {}
    return max(candidates, key=lambda row: float(row.get("delta_return_pct_points_vs_champion", 0.0) or 0.0))


def _pre2021_status(fetch_feasibility: list[dict[str, Any]]) -> str:
    if not fetch_feasibility:
        return "not_checked"
    status = {row.get("probe_id"): row.get("status") for row in fetch_feasibility}
    if status.get("pre2019_probe") == "available":
        return "pre2019_available"
    if status.get("pre2021_probe") == "available":
        return "2020_available_but_2014_2019_unconfirmed_or_empty"
    if status.get("baostock_probe_not_run_in_unit_mode") == "not_run":
        return "not_run"
    return "pre2021_unavailable_or_failed"


def _mean(values: Any) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float(series.mean()) if not series.empty else 0.0


def _positive_rate(values: Any) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float((series > 0).mean()) if not series.empty else 0.0


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        if not keys:
            f.write("")
            return
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5f_short_window_reversion_walk_forward(Path("."), probe_baostock=True), ensure_ascii=False, indent=2))
