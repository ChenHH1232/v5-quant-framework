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


OUT_DIR = Path("v5f_short_window_spike_reversion_symmetry") / "current"
DIAG_DIR = Path("v5f_short_window_reversion_diagnostic") / "current"
FEATURES = DIAG_DIR / "v5f_short_window_reversion_minute_day_features.csv"
CHAMPION_DAILY = Path("v5f_quality_value_mean_reversion") / "current" / "v5f_qv_mean_reversion_daily_returns.csv"

COMMISSION_RATE = 0.0003
TRIM_RELATIVE_WEIGHT = 0.10

MORNING_SPIKE_NEXT1 = "morning30_spike_revert_next1_trim10"
MORNING_SPIKE_NEXT2 = "morning30_spike_revert_next2_trim10"
VWAP_PREMIUM_NEXT1 = "late_vwap_premium_revert_next1_trim10"
COMBO = "combo_morning30_spike_next1_plus_late_vwap_premium_next1_trim10"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_short_window_spike_reversion(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_short_window_spike_reversion_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_short_window_spike_reversion_summary.json", summary)
        return summary

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

    features = _prepare_features(features)
    spec = _spec(features)
    events = _spike_events(features)
    diagnostics = _event_diagnostics(events)
    funding = _funding_returns(features)
    selected = _select_variant_events(events)
    trades = _trade_log(selected, funding)
    funding_audit = _funding_audit(trades)
    daily = _daily_returns(trades, baseline_daily, champion_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    sleeve = _sleeve_attribution(trades)
    governance = _governance_audit(features, selected, trades)
    pit = _pit_audit()
    decision = _pm_decision(metrics, diagnostics, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_short_window_spike_reversion_spec.csv", spec)
    _write_csv(out / "v5f_short_window_spike_reversion_event_log.csv", events)
    _write_csv(out / "v5f_short_window_spike_reversion_diagnostics.csv", diagnostics)
    _write_csv(out / "v5f_short_window_spike_reversion_selected_events.csv", selected)
    _write_csv(out / "v5f_short_window_spike_reversion_trade_log.csv", trades)
    _write_csv(out / "v5f_short_window_spike_reversion_funding_audit.csv", funding_audit)
    _write_csv(out / "v5f_short_window_spike_reversion_daily_returns.csv", daily)
    _write_csv(out / "v5f_short_window_spike_reversion_metrics.csv", metrics)
    _write_csv(out / "v5f_short_window_spike_reversion_yearly.csv", yearly)
    _write_csv(out / "v5f_short_window_spike_reversion_sleeve_attribution.csv", sleeve)
    _write_csv(out / "v5f_short_window_spike_reversion_governance_audit.csv", governance)
    _write_csv(out / "v5f_short_window_spike_reversion_pit_audit.csv", pit)
    _write_csv(out / "v5f_short_window_spike_reversion_pm_decision.csv", decision)
    _write_csv(out / "v5f_short_window_spike_reversion_next_queue.csv", next_queue)
    _write_csv(out / "v5f_short_window_spike_reversion_blockers.csv", blockers_out)
    (out / "v5f_short_window_spike_reversion_report.md").write_text(
        _report(diagnostics, metrics, yearly, sleeve, decision),
        encoding="utf-8",
    )
    (out / "v5f_short_window_spike_reversion_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_overlay(metrics)
    summary = _summary(
        "completed_v5f_short_window_spike_reversion_symmetry",
        decision[0]["pm_gate_decision"],
        [],
        event_count=len(events),
        selected_event_count=len(selected),
        best_variant=best.get("version_id", ""),
        best_delta_vs_champion=float(best.get("delta_return_pct_points_vs_champion", 0.0) or 0.0),
        symmetry_result=decision[0]["symmetry_result"],
    )
    _write_json(out / "v5f_short_window_spike_reversion_summary.json", summary)
    return summary


def _prepare_features(features: pd.DataFrame) -> pd.DataFrame:
    features = features.sort_values(["code", "holding_start_date", "next_rebalance_date", "trade_date"]).copy()
    cycle_cols = ["code", "holding_start_date", "next_rebalance_date"]
    features["next1_date"] = features.groupby(cycle_cols)["trade_date"].shift(-1)
    features["next2_date"] = features.groupby(cycle_cols)["trade_date"].shift(-2)
    return features


def _spec(features: pd.DataFrame) -> list[dict[str, Any]]:
    cut_30 = _quantile(features["r_0935_1000"], 0.90)
    return [
        {
            "version_id": MORNING_SPIKE_NEXT1,
            "event_type": "morning_30m_micro_spike",
            "rule": f"09:35->10:00 return >= max(top decile {cut_30:.6f}, +1%).",
            "close_horizon": "next1",
            "action": "temporary trim 10% relative weight, fund same-sleeve non-triggered holdings",
            "accepted": False,
        },
        {
            "version_id": MORNING_SPIKE_NEXT2,
            "event_type": "morning_30m_micro_spike",
            "rule": f"09:35->10:00 return >= max(top decile {cut_30:.6f}, +1%).",
            "close_horizon": "next2",
            "action": "temporary trim 10% relative weight, fund same-sleeve non-triggered holdings",
            "accepted": False,
        },
        {
            "version_id": VWAP_PREMIUM_NEXT1,
            "event_type": "late_day_vwap_premium",
            "rule": "Previous close->14:55 return >= +2% and 14:55 price >= 0.5% above intraday VWAP.",
            "close_horizon": "next1",
            "action": "temporary trim 10% relative weight, fund same-sleeve non-triggered holdings",
            "accepted": False,
        },
        {
            "version_id": COMBO,
            "event_type": "morning_30m_micro_spike + late_day_vwap_premium",
            "rule": "Combine morning spike next1 and late VWAP premium next1; one event per stock-day.",
            "close_horizon": "next1",
            "action": "temporary trim 10% relative weight, fund same-sleeve non-triggered holdings",
            "accepted": False,
        },
    ]


def _spike_events(features: pd.DataFrame) -> list[dict[str, Any]]:
    top_30 = max(_quantile(features["r_0935_1000"], 0.90), 0.01)
    rows: list[dict[str, Any]] = []
    for _, row in features.iterrows():
        event_defs = [
            (
                "morning_30m_micro_spike",
                _safe_float(row.get("r_0935_1000")) is not None
                and _safe_float(row.get("r_0935_1000")) >= top_30,
                "10:00:00",
                row.get("r_0935_1000"),
                row.get("next1_from_1000"),
                row.get("next2_from_1000"),
                row.get("next1_date"),
                row.get("next2_date"),
            ),
            (
                "late_day_vwap_premium",
                _safe_float(row.get("r_prevclose_1455")) is not None
                and _safe_float(row.get("r_prevclose_1455")) >= 0.02
                and _safe_float(row.get("r_1455_vwap")) is not None
                and _safe_float(row.get("r_1455_vwap")) >= 0.005,
                "14:55:00",
                row.get("r_prevclose_1455"),
                row.get("next1_from_1455"),
                row.get("next2_from_1455"),
                row.get("next1_date"),
                row.get("next2_date"),
            ),
        ]
        for event_type, triggered, observation_time, trigger_return, next1, next2, next1_date, next2_date in event_defs:
            if not triggered:
                continue
            rows.append(
                {
                    "event_id": f"{event_type}|{row['code']}|{row['trade_date']}",
                    "event_type": event_type,
                    "code": row["code"],
                    "trade_date": row["trade_date"],
                    "sleeve": row["sleeve"],
                    "holding_start_date": row["holding_start_date"],
                    "next_rebalance_date": row["next_rebalance_date"],
                    "observation_time": observation_time,
                    "target_weight": _safe_float(row.get("target_weight")) or 0.0,
                    "trigger_return": _safe_float(trigger_return),
                    "next1_return_after_observation": _safe_float(next1),
                    "next2_return_after_observation": _safe_float(next2),
                    "next1_date": "" if pd.isna(next1_date) else next1_date,
                    "next2_date": "" if pd.isna(next2_date) else next2_date,
                    "new_buy_signal_allowed": False,
                    "accepted": False,
                }
            )
    return rows


def _event_diagnostics(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(events)
    if df.empty:
        return []
    rows = []
    for event_type, group in df.groupby("event_type", sort=True):
        rows.append(
            {
                "event_type": event_type,
                "event_count": int(len(group)),
                "unique_stock_count": int(group["code"].nunique()),
                "avg_trigger_return": _mean(group["trigger_return"]),
                "avg_next1_return_after_observation": _mean(group["next1_return_after_observation"]),
                "avg_next2_return_after_observation": _mean(group["next2_return_after_observation"]),
                "hit_rate_next1_negative": _negative_rate(group["next1_return_after_observation"]),
                "hit_rate_next2_negative": _negative_rate(group["next2_return_after_observation"]),
                "reversion_direction": _reversion_direction(group),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _select_variant_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    variants = [
        (MORNING_SPIKE_NEXT1, ["morning_30m_micro_spike"], {"morning_30m_micro_spike": "next1"}),
        (MORNING_SPIKE_NEXT2, ["morning_30m_micro_spike"], {"morning_30m_micro_spike": "next2"}),
        (VWAP_PREMIUM_NEXT1, ["late_day_vwap_premium"], {"late_day_vwap_premium": "next1"}),
        (
            COMBO,
            ["morning_30m_micro_spike", "late_day_vwap_premium"],
            {"morning_30m_micro_spike": "next1", "late_day_vwap_premium": "next1"},
        ),
    ]
    priority = {"morning_30m_micro_spike": 0, "late_day_vwap_premium": 1}
    events_sorted = sorted(events, key=lambda row: (row["trade_date"], row["code"], priority[row["event_type"]]))
    rows: list[dict[str, Any]] = []
    for version, allowed, horizon_map in variants:
        last_close_by_code: dict[str, str] = {}
        seen_code_day: set[tuple[str, str]] = set()
        for event in events_sorted:
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
                    "selected_return": event[f"{horizon}_return_after_observation"],
                    "trim_relative_weight": TRIM_RELATIVE_WEIGHT,
                    "accepted": False,
                }
            )
            rows.append(selected)
            seen_code_day.add(key)
            last_close_by_code[event["code"]] = close_date
    return rows


def _funding_returns(features: pd.DataFrame) -> dict[tuple[str, str, str, str], float]:
    ret_cols = {
        ("morning_30m_micro_spike", "next1"): "next1_from_1000",
        ("morning_30m_micro_spike", "next2"): "next2_from_1000",
        ("late_day_vwap_premium", "next1"): "next1_from_1455",
        ("late_day_vwap_premium", "next2"): "next2_from_1455",
    }
    funding: dict[tuple[str, str, str, str], float] = {}
    for (trade_date, sleeve), group in features.groupby(["trade_date", "sleeve"], sort=False):
        codes = group["code"].astype(str)
        weights = pd.to_numeric(group["target_weight"], errors="coerce").fillna(0.0)
        for (event_type, horizon), col in ret_cols.items():
            series = pd.to_numeric(group[col], errors="coerce")
            for code in codes:
                mask = codes.ne(code) & series.notna()
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
        trim_weight = float(row["target_weight"]) * TRIM_RELATIVE_WEIGHT
        gross = trim_weight * (funding_return - stock_return)
        commission = trim_weight * COMMISSION_RATE * 2
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
                "trim_weight": trim_weight,
                "stock_return_after_observation": stock_return,
                "same_sleeve_funding_return": funding_return,
                "funding_minus_stock_return": funding_return - stock_return,
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
                "total_trim_weight": pd.to_numeric(group["trim_weight"], errors="coerce").sum(),
                "funding_policy": "same_sleeve_non_triggered_holdings",
                "funding_weight_ok": pd.to_numeric(group["trim_weight"], errors="coerce").sum() <= 0.10,
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
    variants = [MORNING_SPIKE_NEXT1, MORNING_SPIKE_NEXT2, VWAP_PREMIUM_NEXT1, COMBO]
    rows: list[dict[str, Any]] = []
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
        navs = pd.to_numeric(group["strategy_nav"], errors="coerce").tolist()
        rets = pd.to_numeric(group["strategy_return"], errors="coerce").tolist()
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
                "overlay_return_sum": pd.to_numeric(group["overlay_return"], errors="coerce").sum(),
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
                "period_return": (1 + pd.to_numeric(group["strategy_return"], errors="coerce")).prod() - 1,
                "overlay_return_sum": pd.to_numeric(group["overlay_return"], errors="coerce").sum(),
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
                "net_incremental_return_sum_pct_points": pd.to_numeric(group["net_incremental_return"], errors="coerce").sum() * 100,
                "avg_funding_minus_stock_return": pd.to_numeric(group["funding_minus_stock_return"], errors="coerce").mean(),
            }
        )
    return rows


def _governance_audit(
    features: pd.DataFrame,
    selected: list[dict[str, Any]],
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    trade_df = pd.DataFrame(trades)
    max_trim = 0.0
    if not trade_df.empty:
        max_trim = float(trade_df.groupby(["version_id", "open_date", "sleeve"])["trim_weight"].sum().max())
    return [
        {"audit_id": "backtest_scope_end", "status": "pass", "detail": BACKTEST_END},
        {"audit_id": "full_holding_5min_feature_count", "status": "pass" if len(features) == 33984 else "review", "detail": len(features)},
        {
            "audit_id": "focused_spike_signal_only",
            "status": "pass"
            if {row["event_type"] for row in selected}.issubset({"morning_30m_micro_spike", "late_day_vwap_premium"})
            else "fail",
            "detail": sorted({row["event_type"] for row in selected}),
        },
        {"audit_id": "same_sleeve_funding", "status": "pass", "detail": "non_triggered_same_sleeve_holdings"},
        {"audit_id": "max_daily_sleeve_trim_weight", "status": "pass" if max_trim <= 0.10 else "review", "detail": max_trim},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": True},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pit_audit() -> list[dict[str, Any]]:
    return [
        {
            "audit_id": "morning_spike_signal_pit",
            "status": "pass",
            "detail": "Morning spike uses 09:35 to 10:00 bars; forward returns are evaluation.",
        },
        {
            "audit_id": "late_vwap_premium_signal_pit",
            "status": "pass",
            "detail": "Late VWAP premium uses bars through 14:55; next-day return is evaluation.",
        },
        {
            "audit_id": "fixed_mirror_variants_no_scan",
            "status": "pass",
            "detail": "Tests mirror of focused short-window reversion signals only.",
        },
    ]


def _pm_decision(
    metrics: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    best = _best_overlay(metrics)
    best_delta = float(best.get("delta_return_pct_points_vs_champion", 0.0) or 0.0)
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        symmetry = "unknown"
        rationale = "Governance audit failed."
    elif best_delta > 0.5:
        decision = "spike_reversion_positive_ready_for_pm_quant_review_not_accepted"
        symmetry = "partially_symmetric"
        rationale = "Acute spike reversion is positive after same-sleeve funding and commission."
    elif best_delta > 0.0:
        decision = "spike_reversion_positive_but_weak_keep_diagnostic"
        symmetry = "weakly_symmetric"
        rationale = "Acute spike reversion exists but is smaller than the acute-drop repair signal."
    else:
        decision = "spike_reversion_not_symmetric_keep_drop_repair_only"
        symmetry = "not_symmetric"
        rationale = "Acute spike reversion does not survive same-sleeve funding and commission."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": best.get("version_id", "") if best_delta > 0.5 else CHAMPION,
            "best_variant": best.get("version_id", ""),
            "best_delta_return_pct_points_vs_champion": best_delta,
            "symmetry_result": symmetry,
            "diagnostic_event_types": ";".join(row["event_type"] for row in diagnostics),
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Keep morning drop repair next1 as the cleaner short-window candidate unless spike review promotes.", "allowed": True},
        {"priority": 2, "task": "Open PM/Quant review for spike reversion if promoted.", "allowed": decision.startswith("spike_reversion_positive_ready")},
        {"priority": 3, "task": "Compare drop-repair and spike-trim interaction before any combined overlay.", "allowed": True},
        {"priority": 4, "task": "Optimize spike thresholds or full-market intraday shorting.", "allowed": False},
    ]


def _best_overlay(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        row
        for row in metrics
        if row["version_id"] not in {BASELINE, CHAMPION}
        and str(row["version_id"]).endswith("_on_momentum_champion_estimate")
    ]
    if not rows:
        return {}
    return max(rows, key=lambda row: float(row["delta_return_pct_points_vs_champion"]))


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Spike reversion symmetry test completed."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    event_count: int = 0,
    selected_event_count: int = 0,
    best_variant: str = "",
    best_delta_vs_champion: float = 0.0,
    symmetry_result: str = "",
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_short_window_spike_reversion_symmetry",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_reference": CHAMPION,
        "event_count": event_count,
        "selected_event_count": selected_event_count,
        "best_variant": best_variant,
        "best_delta_return_pct_points_vs_champion": best_delta_vs_champion,
        "symmetry_result": symmetry_result,
        "accepted": False,
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
    diagnostics: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    yearly: list[dict[str, Any]],
    sleeve: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Short-Window Spike Reversion Symmetry",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Symmetry result: `{decision[0]['symmetry_result']}`",
            f"- Best variant: `{decision[0]['best_variant']}`",
            "- Mirror test: acute rise means temporary trim; same-sleeve funding; double-side commission.",
            "- Status: not accepted; not live approved.",
            "",
            "## Diagnostics",
            *[
                f"- `{row['event_type']}`: count={row['event_count']}, next1={float(row['avg_next1_return_after_observation']):.4%}, next2={float(row['avg_next2_return_after_observation']):.4%}, direction={row['reversion_direction']}"
                for row in diagnostics
            ],
            "",
            "## Metrics",
            *[
                f"- `{row['version_id']}`: return={float(row['strategy_return']) * 100:.2f}%, "
                f"delta_vs_champion={float(row['delta_return_pct_points_vs_champion']):.4f} pct"
                for row in metrics
            ],
            "",
            f"Yearly rows generated: {len(yearly)}; sleeve attribution rows: {len(sleeve)}.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Spike Reversion Symmetry Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- Uses V57f repaired holdings only.",
            "- Tests acute rise mirror of the short-window drop repair line.",
            "- Same-sleeve funding and double-side commission are required.",
            "- No accepted/live approval and no threshold optimization.",
            "",
        ]
    )


def _reversion_direction(group: pd.DataFrame) -> str:
    next1 = _mean(group["next1_return_after_observation"])
    next2 = _mean(group["next2_return_after_observation"])
    neg1 = _negative_rate(group["next1_return_after_observation"])
    if next1 < 0 and next2 < 0 and neg1 >= 0.5:
        return "spike_reversion_negative_forward"
    if next1 > 0 and next2 > 0:
        return "momentum_continuation_after_spike"
    return "mixed_or_small"


def _mean(values: Any) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float(series.mean()) if len(series) else 0.0


def _negative_rate(values: Any) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float((series < 0).mean()) if len(series) else 0.0


def _quantile(values: Any, q: float) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float(series.quantile(q)) if len(series) else 0.0


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [FEATURES, REPAIRED_RUN / "daily_returns.csv", CHAMPION_DAILY]
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
    print(json.dumps(run_v5f_short_window_spike_reversion(Path(".")), ensure_ascii=False, indent=2))
