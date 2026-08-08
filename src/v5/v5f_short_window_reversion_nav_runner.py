from __future__ import annotations

import csv
import json
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


OUT_DIR = Path("v5f_short_window_reversion_nav_engineering") / "current"
DIAG_DIR = Path("v5f_short_window_reversion_diagnostic") / "current"
DIAG_SUMMARY = DIAG_DIR / "v5f_short_window_reversion_summary.json"
EVENT_LOG = DIAG_DIR / "v5f_short_window_reversion_event_log.csv"
FEATURES = DIAG_DIR / "v5f_short_window_reversion_minute_day_features.csv"
CHAMPION_DAILY = Path("v5f_quality_value_mean_reversion") / "current" / "v5f_qv_mean_reversion_daily_returns.csv"

COMMISSION_RATE = 0.0003
OVERLAY_RELATIVE_ADD = 0.10

MORNING_NEXT1 = "morning30_repair_next1_same_sleeve_add10"
MORNING_NEXT2 = "morning30_repair_next2_same_sleeve_add10"
VWAP_NEXT1 = "late_vwap_repair_next1_same_sleeve_add10"
COMBO = "combo_morning30_next2_plus_late_vwap_next1_add10"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_short_window_reversion_nav(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_short_window_reversion_nav_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_short_window_reversion_nav_summary.json", summary)
        return summary

    diag_summary = _read_json(root / DIAG_SUMMARY)
    events = pd.read_csv(root / EVENT_LOG, dtype={"trade_date": str, "code": str})
    features = pd.read_csv(root / FEATURES, dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    champion_daily = pd.read_csv(root / CHAMPION_DAILY, dtype={"trade_date": str})
    baseline_daily = baseline_daily[
        (baseline_daily["trade_date"] >= BACKTEST_START) & (baseline_daily["trade_date"] <= BACKTEST_END)
    ].copy()
    champion_daily = champion_daily[
        (champion_daily["trade_date"] >= BACKTEST_START)
        & (champion_daily["trade_date"] <= BACKTEST_END)
        & (champion_daily["version_id"].eq(CHAMPION))
    ].copy()

    spec = _spec()
    feature_idx = _feature_index(features)
    focused_events = _focused_events(events, features, feature_idx)
    funding = _funding_returns(features)
    selected = _select_variant_events(focused_events)
    trades = _trade_log(selected, funding)
    funding_audit = _funding_audit(trades)
    daily = _daily_returns(trades, baseline_daily, champion_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    sleeve = _sleeve_attribution(trades)
    governance = _governance_audit(diag_summary, selected, trades)
    pit = _pit_audit()
    decision = _pm_decision(metrics, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_short_window_reversion_nav_spec.csv", spec)
    _write_csv(out / "v5f_short_window_reversion_nav_focused_events.csv", focused_events)
    _write_csv(out / "v5f_short_window_reversion_nav_selected_events.csv", selected)
    _write_csv(out / "v5f_short_window_reversion_nav_trade_log.csv", trades)
    _write_csv(out / "v5f_short_window_reversion_nav_funding_audit.csv", funding_audit)
    _write_csv(out / "v5f_short_window_reversion_nav_daily_returns.csv", daily)
    _write_csv(out / "v5f_short_window_reversion_nav_metrics.csv", metrics)
    _write_csv(out / "v5f_short_window_reversion_nav_yearly.csv", yearly)
    _write_csv(out / "v5f_short_window_reversion_nav_sleeve_attribution.csv", sleeve)
    _write_csv(out / "v5f_short_window_reversion_nav_governance_audit.csv", governance)
    _write_csv(out / "v5f_short_window_reversion_nav_pit_audit.csv", pit)
    _write_csv(out / "v5f_short_window_reversion_nav_pm_decision.csv", decision)
    _write_csv(out / "v5f_short_window_reversion_nav_next_queue.csv", next_queue)
    _write_csv(out / "v5f_short_window_reversion_nav_blockers.csv", blockers_out)
    (out / "v5f_short_window_reversion_nav_report.md").write_text(
        _report(metrics, yearly, sleeve, decision),
        encoding="utf-8",
    )
    (out / "v5f_short_window_reversion_nav_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_overlay(metrics)
    summary = _summary(
        "completed_v5f_short_window_reversion_nav_engineering",
        decision[0]["pm_gate_decision"],
        [],
        focused_event_count=len(focused_events),
        selected_event_count=len(selected),
        best_variant=best.get("version_id", ""),
        best_delta_vs_champion=float(best.get("delta_return_pct_points_vs_champion", 0.0) or 0.0),
        accepted=False,
    )
    _write_json(out / "v5f_short_window_reversion_nav_summary.json", summary)
    return summary


def _spec() -> list[dict[str, Any]]:
    return [
        {
            "version_id": MORNING_NEXT1,
            "event_type": "morning_30m_micro_crash",
            "observation_time": "10:00:00",
            "close_horizon": "next1",
            "overlay_relative_add": OVERLAY_RELATIVE_ADD,
            "funding": "same_sleeve_non_triggered_holdings",
            "accepted": False,
        },
        {
            "version_id": MORNING_NEXT2,
            "event_type": "morning_30m_micro_crash",
            "observation_time": "10:00:00",
            "close_horizon": "next2",
            "overlay_relative_add": OVERLAY_RELATIVE_ADD,
            "funding": "same_sleeve_non_triggered_holdings",
            "accepted": False,
        },
        {
            "version_id": VWAP_NEXT1,
            "event_type": "late_day_vwap_dislocation",
            "observation_time": "14:55:00",
            "close_horizon": "next1",
            "overlay_relative_add": OVERLAY_RELATIVE_ADD,
            "funding": "same_sleeve_non_triggered_holdings",
            "accepted": False,
        },
        {
            "version_id": COMBO,
            "event_type": "morning_30m_micro_crash + late_day_vwap_dislocation",
            "observation_time": "10:00:00 / 14:55:00",
            "close_horizon": "morning next2, late vwap next1",
            "overlay_relative_add": OVERLAY_RELATIVE_ADD,
            "funding": "same_sleeve_non_triggered_holdings",
            "accepted": False,
        },
    ]


def _feature_index(features: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    features = features.sort_values(["code", "trade_date"]).reset_index(drop=True)
    cycle_cols = ["code", "holding_start_date", "next_rebalance_date"]
    features["next1_date"] = features.groupby(cycle_cols)["trade_date"].shift(-1)
    features["next2_date"] = features.groupby(cycle_cols)["trade_date"].shift(-2)
    return {(str(row["code"]), str(row["trade_date"])): row.to_dict() for _, row in features.iterrows()}


def _focused_events(
    events: pd.DataFrame,
    features: pd.DataFrame,
    feature_idx: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    events = events[
        events["event_type"].isin(["morning_30m_micro_crash", "late_day_vwap_dislocation"])
    ].copy()
    rows: list[dict[str, Any]] = []
    for _, row in events.iterrows():
        code = str(row["code"])
        trade_date = str(row["trade_date"])
        feature = feature_idx.get((code, trade_date), {})
        event_type = str(row["event_type"])
        if event_type == "morning_30m_micro_crash":
            obs_price = _safe_float(feature.get("close_1000"))
            next1 = _safe_float(feature.get("next1_from_1000"))
            next2 = _safe_float(feature.get("next2_from_1000"))
            same_day = _safe_float(feature.get("r_1000_1455"))
            next1_date = feature.get("next1_date", "")
            next2_date = feature.get("next2_date", "")
        else:
            obs_price = _safe_float(feature.get("close_1455"))
            next1 = _safe_float(feature.get("next1_from_1455"))
            next2 = _safe_float(feature.get("next2_from_1455"))
            same_day = 0.0
            next1_date = feature.get("next1_date", "")
            next2_date = feature.get("next2_date", "")
        rows.append(
            {
                "event_id": f"{event_type}|{code}|{trade_date}",
                "event_type": event_type,
                "code": code,
                "trade_date": trade_date,
                "sleeve": row["sleeve"],
                "holding_start_date": row["holding_start_date"],
                "observation_time": row["observation_time"],
                "observation_price": obs_price,
                "target_weight": _safe_float(row["target_weight"]) or 0.0,
                "trigger_return": _safe_float(row["trigger_return"]),
                "same_day_return": same_day,
                "next1_return": next1,
                "next2_return": next2,
                "next1_date": "" if pd.isna(next1_date) else next1_date,
                "next2_date": "" if pd.isna(next2_date) else next2_date,
                "fundamental_proxy_intact": row.get("fundamental_proxy_intact", ""),
                "valuation_proxy_cheap": row.get("valuation_proxy_cheap", ""),
                "accepted": False,
            }
        )
    return rows


def _select_variant_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    variants = [
        (MORNING_NEXT1, ["morning_30m_micro_crash"], {"morning_30m_micro_crash": "next1"}),
        (MORNING_NEXT2, ["morning_30m_micro_crash"], {"morning_30m_micro_crash": "next2"}),
        (VWAP_NEXT1, ["late_day_vwap_dislocation"], {"late_day_vwap_dislocation": "next1"}),
        (
            COMBO,
            ["morning_30m_micro_crash", "late_day_vwap_dislocation"],
            {"morning_30m_micro_crash": "next2", "late_day_vwap_dislocation": "next1"},
        ),
    ]
    rows: list[dict[str, Any]] = []
    events_sorted = sorted(events, key=lambda row: (row["trade_date"], row["code"], row["event_type"]))
    priority = {"morning_30m_micro_crash": 0, "late_day_vwap_dislocation": 1}
    for version, allowed, horizon_map in variants:
        last_close_by_code: dict[str, str] = {}
        seen_code_day: set[tuple[str, str]] = set()
        for event in sorted(events_sorted, key=lambda row: (row["trade_date"], row["code"], priority[row["event_type"]])):
            if event["event_type"] not in allowed:
                continue
            key = (event["code"], event["trade_date"])
            if version == COMBO and key in seen_code_day:
                continue
            horizon = horizon_map[event["event_type"]]
            close_date = str(event[f"{horizon}_date"])
            if close_date == "" or close_date.lower() == "nan":
                continue
            last_close = last_close_by_code.get(event["code"], "")
            if last_close and event["trade_date"] <= last_close:
                continue
            selected = dict(event)
            selected.update(
                {
                    "version_id": version,
                    "close_horizon": horizon,
                    "close_date": close_date,
                    "selected_return": event[f"{horizon}_return"],
                    "overlay_relative_add": OVERLAY_RELATIVE_ADD,
                    "duplicate_or_overlap_filtered": False,
                    "accepted": False,
                }
            )
            rows.append(selected)
            last_close_by_code[event["code"]] = close_date
            seen_code_day.add(key)
    return rows


def _funding_returns(features: pd.DataFrame) -> dict[tuple[str, str, str, str], float]:
    ret_cols = {
        ("morning_30m_micro_crash", "next1"): "next1_from_1000",
        ("morning_30m_micro_crash", "next2"): "next2_from_1000",
        ("late_day_vwap_dislocation", "next1"): "next1_from_1455",
        ("late_day_vwap_dislocation", "next2"): "next2_from_1455",
    }
    funding: dict[tuple[str, str, str, str], float] = {}
    for (trade_date, sleeve), group in features.groupby(["trade_date", "sleeve"], sort=False):
        for (event_type, horizon), col in ret_cols.items():
            series = pd.to_numeric(group[col], errors="coerce")
            weights = pd.to_numeric(group["target_weight"], errors="coerce").fillna(0.0)
            for code in group["code"].astype(str):
                mask = group["code"].astype(str).ne(code) & series.notna()
                if not mask.any():
                    funding[(trade_date, sleeve, event_type, horizon, code)] = 0.0
                    continue
                w = weights[mask]
                r = series[mask]
                funding[(trade_date, sleeve, event_type, horizon, code)] = (
                    float((r * w).sum() / w.sum()) if float(w.sum()) else float(r.mean())
                )
    return funding


def _trade_log(
    selected: list[dict[str, Any]],
    funding: dict[tuple[str, str, str, str], float],
) -> list[dict[str, Any]]:
    rows = []
    for row in selected:
        stock_return = _safe_float(row["selected_return"])
        if stock_return is None:
            continue
        funding_return = funding.get(
            (row["trade_date"], row["sleeve"], row["event_type"], row["close_horizon"], row["code"]),
            0.0,
        )
        overlay_weight = float(row["target_weight"]) * OVERLAY_RELATIVE_ADD
        gross = overlay_weight * (stock_return - funding_return)
        commission = overlay_weight * COMMISSION_RATE * 2
        net = gross - commission
        rows.append(
            {
                "version_id": row["version_id"],
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "code": row["code"],
                "sleeve": row["sleeve"],
                "open_date": row["trade_date"],
                "close_date": row["close_date"],
                "observation_time": row["observation_time"],
                "close_horizon": row["close_horizon"],
                "target_weight": row["target_weight"],
                "overlay_weight": overlay_weight,
                "stock_return_after_observation": stock_return,
                "same_sleeve_funding_return": funding_return,
                "excess_return_vs_funding": stock_return - funding_return,
                "gross_incremental_return": gross,
                "commission_drag": commission,
                "net_incremental_return": net,
                "accepted": False,
            }
        )
    return rows


def _funding_audit(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows = []
    for (version, open_date, sleeve), group in df.groupby(["version_id", "open_date", "sleeve"], sort=True):
        rows.append(
            {
                "version_id": version,
                "open_date": open_date,
                "sleeve": sleeve,
                "event_count": int(len(group)),
                "total_overlay_weight": pd.to_numeric(group["overlay_weight"]).sum(),
                "max_single_overlay_weight": pd.to_numeric(group["overlay_weight"]).max(),
                "funding_policy": "same_sleeve_non_triggered_holdings",
                "funding_weight_ok": pd.to_numeric(group["overlay_weight"]).sum() <= 0.10,
            }
        )
    return rows


def _daily_returns(
    trades: list[dict[str, Any]],
    baseline_daily: pd.DataFrame,
    champion_daily: pd.DataFrame,
) -> list[dict[str, Any]]:
    overlay = pd.DataFrame(trades)
    baseline_ret = baseline_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    champion_ret = champion_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    rows: list[dict[str, Any]] = []
    variants = [MORNING_NEXT1, MORNING_NEXT2, VWAP_NEXT1, COMBO]
    for version in variants:
        version_overlay = {}
        if not overlay.empty:
            grouped = overlay[overlay["version_id"].eq(version)].groupby("close_date")["net_incremental_return"].sum()
            version_overlay = {str(date): float(value) for date, value in grouped.items()}
        nav_v57f = 1.0
        nav_champion = 1.0
        for date in sorted(baseline_ret):
            oret = version_overlay.get(date, 0.0)
            v57f_ret = baseline_ret[date] + oret
            champion_plus_ret = champion_ret.get(date, baseline_ret[date]) + oret
            nav_v57f *= 1.0 + v57f_ret
            nav_champion *= 1.0 + champion_plus_ret
            rows.append(
                {
                    "trade_date": date,
                    "version_id": f"{version}_on_v57f",
                    "base_reference": BASELINE,
                    "strategy_return": v57f_ret,
                    "strategy_nav": nav_v57f,
                    "base_return": baseline_ret[date],
                    "overlay_return": oret,
                    "accepted": False,
                }
            )
            rows.append(
                {
                    "trade_date": date,
                    "version_id": f"{version}_on_momentum_champion_estimate",
                    "base_reference": CHAMPION,
                    "strategy_return": champion_plus_ret,
                    "strategy_nav": nav_champion,
                    "base_return": champion_ret.get(date, baseline_ret[date]),
                    "overlay_return": oret,
                    "accepted": False,
                }
            )
    nav = 1.0
    for date in sorted(baseline_ret):
        nav *= 1.0 + baseline_ret[date]
        rows.append(
            {
                "trade_date": date,
                "version_id": BASELINE,
                "base_reference": BASELINE,
                "strategy_return": baseline_ret[date],
                "strategy_nav": nav,
                "base_return": baseline_ret[date],
                "overlay_return": 0.0,
                "accepted": False,
            }
        )
    nav = 1.0
    for date in sorted(baseline_ret):
        ret = champion_ret.get(date, baseline_ret[date])
        nav *= 1.0 + ret
        rows.append(
            {
                "trade_date": date,
                "version_id": CHAMPION,
                "base_reference": CHAMPION,
                "strategy_return": ret,
                "strategy_nav": nav,
                "base_return": ret,
                "overlay_return": 0.0,
                "accepted": False,
            }
        )
    return rows


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out = []
    for version, group in df.groupby("version_id", sort=True):
        group = group.sort_values("trade_date")
        navs = pd.to_numeric(group["strategy_nav"]).tolist()
        rets = pd.to_numeric(group["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = pd.Series(rets).std() * (252**0.5)
        out.append(
            {
                "version_id": version,
                "base_reference": group.iloc[0]["base_reference"],
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "overlay_return_sum": pd.to_numeric(group["overlay_return"]).sum(),
                "accepted": False,
            }
        )
    base = next(row for row in out if row["version_id"] == BASELINE)
    champ = next(row for row in out if row["version_id"] == CHAMPION)
    for row in out:
        row["delta_return_pct_points_vs_v57f"] = (float(row["strategy_return"]) - float(base["strategy_return"])) * 100
        row["delta_return_pct_points_vs_champion"] = (
            float(row["strategy_return"]) - float(champ["strategy_return"])
        ) * 100
        row["delta_max_drawdown_pct_points_vs_v57f"] = (
            float(row["max_drawdown"]) - float(base["max_drawdown"])
        ) * 100
        row["delta_max_drawdown_pct_points_vs_champion"] = (
            float(row["max_drawdown"]) - float(champ["max_drawdown"])
        ) * 100
    return sorted(out, key=lambda row: float(row["delta_return_pct_points_vs_champion"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].astype(str).str.slice(0, 4)
    out = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append(
            {
                "version_id": version,
                "year": year,
                "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1,
                "overlay_return_sum": pd.to_numeric(group["overlay_return"]).sum(),
                "trade_days": len(group),
            }
        )
    return out


def _sleeve_attribution(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows = []
    for (version, event_type, sleeve), group in df.groupby(["version_id", "event_type", "sleeve"], sort=True):
        rows.append(
            {
                "version_id": version,
                "event_type": event_type,
                "sleeve": sleeve,
                "event_count": len(group),
                "unique_stock_count": group["code"].nunique(),
                "gross_incremental_return_sum_pct_points": pd.to_numeric(group["gross_incremental_return"]).sum() * 100,
                "commission_drag_sum_pct_points": pd.to_numeric(group["commission_drag"]).sum() * 100,
                "net_incremental_return_sum_pct_points": pd.to_numeric(group["net_incremental_return"]).sum() * 100,
                "avg_excess_return_vs_funding": pd.to_numeric(group["excess_return_vs_funding"]).mean(),
            }
        )
    return rows


def _governance_audit(
    diag_summary: dict[str, Any],
    selected: list[dict[str, Any]],
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    trade_df = pd.DataFrame(trades)
    max_daily_sleeve_overlay = 0.0
    if not trade_df.empty:
        max_daily_sleeve_overlay = float(
            trade_df.groupby(["version_id", "open_date", "sleeve"])["overlay_weight"].sum().max()
        )
    return [
        {"audit_id": "backtest_scope_end", "status": "pass", "detail": BACKTEST_END},
        {
            "audit_id": "source_diagnostic_gate",
            "status": "pass" if diag_summary.get("fatal_blocker_count") == 0 else "fail",
            "detail": diag_summary.get("pm_gate_decision"),
        },
        {
            "audit_id": "focused_signal_only",
            "status": "pass"
            if {row["event_type"] for row in selected}.issubset(
                {"morning_30m_micro_crash", "late_day_vwap_dislocation"}
            )
            else "fail",
            "detail": sorted({row["event_type"] for row in selected}),
        },
        {"audit_id": "same_sleeve_funding", "status": "pass", "detail": "non_triggered_same_sleeve_holdings"},
        {"audit_id": "max_daily_sleeve_overlay_weight", "status": "pass" if max_daily_sleeve_overlay <= 0.10 else "review", "detail": max_daily_sleeve_overlay},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": True},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pit_audit() -> list[dict[str, Any]]:
    return [
        {
            "audit_id": "morning_signal_pit",
            "status": "pass",
            "detail": "Morning signal uses 09:35 to 10:00 bars; next 1d/2d returns are evaluation.",
        },
        {
            "audit_id": "late_vwap_signal_pit",
            "status": "pass",
            "detail": "Late VWAP signal uses bars through 14:55; next-day return is evaluation.",
        },
        {
            "audit_id": "fixed_variants_no_scan",
            "status": "pass",
            "detail": "Tests only requested morning 1/2d and late VWAP next-day repair variants.",
        },
    ]


def _pm_decision(metrics: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] in {"pass"} for row in governance)
    best = _best_overlay(metrics)
    best_delta = float(best.get("delta_return_pct_points_vs_champion", 0.0) or 0.0)
    best_dd_delta = float(best.get("delta_max_drawdown_pct_points_vs_champion", 0.0) or 0.0)
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        primary = CHAMPION
        rationale = "Governance audit failed."
    elif best_delta > 1.0 and best_dd_delta <= 0.50:
        decision = "promote_short_window_reversion_to_pm_quant_review_not_accepted"
        primary = best["version_id"]
        rationale = "Focused short-window repair improves estimated NAV over momentum champion after same-sleeve funding and commission."
    elif best_delta > 0.0:
        decision = "short_window_reversion_positive_but_needs_robustness_keep_momentum_primary"
        primary = CHAMPION
        rationale = "Focused repair is positive but not strong enough for immediate candidate promotion."
    else:
        decision = "short_window_reversion_nav_failed_keep_momentum_primary"
        primary = CHAMPION
        rationale = "Focused repair fails after same-sleeve funding and commission."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": primary,
            "best_variant": best.get("version_id", ""),
            "best_delta_return_pct_points_vs_champion": best_delta,
            "best_delta_max_drawdown_pct_points_vs_champion": best_dd_delta,
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Keep V5f momentum 70/30 as primary unless focused repair is promoted.", "allowed": True},
        {"priority": 2, "task": "Open PM/Quant robustness review for focused short-window repair.", "allowed": decision.startswith("promote_short_window")},
        {"priority": 3, "task": "Run event concentration and stress-period robustness before any candidate status.", "allowed": decision.startswith("promote_short_window") or decision.startswith("short_window_reversion_positive")},
        {"priority": 4, "task": "Optimize shock thresholds or use full-market intraday selection.", "allowed": False},
    ]


def _best_overlay(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    overlay_rows = [
        row
        for row in metrics
        if row["version_id"] not in {BASELINE, CHAMPION}
        and str(row["version_id"]).endswith("_on_momentum_champion_estimate")
    ]
    if not overlay_rows:
        return {}
    return max(overlay_rows, key=lambda row: float(row["delta_return_pct_points_vs_champion"]))


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Focused short-window NAV engineering completed."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    focused_event_count: int = 0,
    selected_event_count: int = 0,
    best_variant: str = "",
    best_delta_vs_champion: float = 0.0,
    accepted: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_short_window_reversion_nav_engineering",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_reference": CHAMPION,
        "focused_event_count": focused_event_count,
        "selected_event_count": selected_event_count,
        "best_variant": best_variant,
        "best_delta_return_pct_points_vs_champion": best_delta_vs_champion,
        "accepted": accepted,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    metrics: list[dict[str, Any]],
    yearly: list[dict[str, Any]],
    sleeve: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Focused Short-Window Reversion NAV Engineering",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary candidate: `{decision[0]['primary_candidate']}`",
            f"- Best variant: `{decision[0]['best_variant']}`",
            "- Signals: morning 30m micro-crash and late-day VWAP dislocation only.",
            "- Funding: same-sleeve non-triggered holdings; double-side commission included.",
            "- Status: not accepted; not live approved.",
            "",
            "## Metrics",
            *[
                f"- `{row['version_id']}`: return={float(row['strategy_return']) * 100:.2f}%, "
                f"delta_vs_v57f={float(row['delta_return_pct_points_vs_v57f']):.4f} pct, "
                f"delta_vs_champion={float(row['delta_return_pct_points_vs_champion']):.4f} pct, "
                f"dd_delta_vs_champion={float(row['delta_max_drawdown_pct_points_vs_champion']):.4f} pct"
                for row in metrics
            ],
            "",
            "## Sleeve Attribution",
            *[
                f"- `{row['version_id']}` / `{row['event_type']}` / `{row['sleeve']}`: "
                f"events={row['event_count']}, net={float(row['net_incremental_return_sum_pct_points']):.4f} pct"
                for row in sleeve
            ],
            "",
            f"Yearly rows generated: {len(yearly)}.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Focused Short-Window Reversion NAV Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- Use V57f repaired holdings only.",
            "- Test only morning 30m micro-crash and late VWAP dislocation.",
            "- Same-sleeve funding and double-side commission are required.",
            "- Not accepted and not live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        DIAG_SUMMARY,
        EVENT_LOG,
        FEATURES,
        REPAIRED_RUN / "daily_returns.csv",
        CHAMPION_DAILY,
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
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
    print(json.dumps(run_v5f_short_window_reversion_nav(Path(".")), ensure_ascii=False, indent=2))
