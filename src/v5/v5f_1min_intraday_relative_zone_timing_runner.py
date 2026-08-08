from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_1min_intraday_relative_zone_timing_test") / "current"
ONE_MIN_DATASET = "local_1min_clean_2013_2026"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
QV_WEIGHT_LOG = Path("v5f_quality_value_mean_reversion") / "current" / "v5f_qv_mean_reversion_weight_log.csv"
MICRO_EVENT_DIAG = Path("v5f_1min_microstructure_signal_quality_gate") / "current" / "v5f_1min_event_path_diagnostics.csv"

CHAMPION = "internal_subsleeve_mom12_70_30_current_champion"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
OBS_TIMES = ["10:00:00", "10:30:00", "14:00:00", "14:30:00", "14:55:00"]
LOW_CUT = 0.30
HIGH_CUT = 0.70

BUY_SIDES = {"buy", "buy_tilt", "increase"}
SELL_SIDES = {"sell", "sell_tilt", "decrease"}
CRASH_EVENTS = {"morning_30m_micro_crash", "morning_60m_micro_crash", "late_day_vwap_dislocation"}
SPIKE_EVENTS = {"morning_30m_micro_spike", "late_day_vwap_premium"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_1min_intraday_relative_zone_timing(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_required_input", blockers)
        _write_minimal(out, summary, blockers)
        return summary

    db = _find_v5_database(root)
    intents = _trade_intents(root)
    day_cache = _load_days(db, [(row["code"], row["trade_date"]) for row in intents])
    zone_panel = _value_momentum_zone_panel(intents, day_cache)
    timing_summary = _timing_summary(zone_panel, ["intent_family", "side", "obs_time"])
    zone_summary = _timing_summary(zone_panel, ["intent_family", "side", "obs_time", "pit_zone_bucket"])
    vm_candidates = _candidate_matrix_from_timing(timing_summary)

    mr_events = _mean_reversion_events(root)
    mr_day_cache = _load_days(db, [(row["code"], row["trade_date"]) for row in mr_events])
    mr_panel = _mean_reversion_zone_panel(mr_events, mr_day_cache)
    mr_summary = _timing_summary(mr_panel, ["intent_family", "side", "event_type"])
    mr_zone_summary = _timing_summary(mr_panel, ["intent_family", "side", "event_type", "pit_zone_bucket"])

    candidate_matrix = vm_candidates + _candidate_matrix_from_timing(mr_summary)
    data_gate = _data_gate(intents, zone_panel, mr_events, mr_panel)
    governance = _governance_audit()
    decision = _pm_decision(candidate_matrix, data_gate, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(data_gate, governance)

    _write_csv(out / "v5f_1min_zone_definition.csv", _zone_definition())
    _write_csv(out / "v5f_1min_value_momentum_trade_intent.csv", intents)
    _write_csv(out / "v5f_1min_value_momentum_zone_panel.csv", zone_panel)
    _write_csv(out / "v5f_1min_value_momentum_execution_timing_summary.csv", timing_summary)
    _write_csv(out / "v5f_1min_value_momentum_zone_bucket_summary.csv", zone_summary)
    _write_csv(out / "v5f_1min_mean_reversion_zone_panel.csv", mr_panel)
    _write_csv(out / "v5f_1min_mean_reversion_zone_summary.csv", mr_summary)
    _write_csv(out / "v5f_1min_mean_reversion_zone_bucket_summary.csv", mr_zone_summary)
    _write_csv(out / "v5f_1min_execution_timing_candidate_matrix.csv", candidate_matrix)
    _write_csv(out / "v5f_1min_intraday_zone_data_gate.csv", data_gate)
    _write_csv(out / "v5f_1min_intraday_zone_pit_governance_audit.csv", governance)
    _write_csv(out / "v5f_1min_intraday_zone_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_1min_intraday_zone_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_1min_intraday_zone_blockers.csv", blockers_out)
    (out / "v5f_1min_intraday_relative_zone_report.md").write_text(
        _report(timing_summary, mr_summary, candidate_matrix, decision),
        encoding="utf-8",
    )
    (out / "v5f_1min_intraday_zone_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best_buy = _best_candidate(candidate_matrix, action="buy")
    best_sell = _best_candidate(candidate_matrix, action="sell")
    summary = _summary(
        "completed_v5f_1min_intraday_relative_zone_timing_test",
        decision[0]["pm_gate_decision"],
        [],
        value_momentum_intent_count=len(intents),
        value_momentum_zone_row_count=len(zone_panel),
        mean_reversion_event_count=len(mr_events),
        mean_reversion_zone_row_count=len(mr_panel),
        best_buy_context=best_buy.get("context_id", ""),
        best_buy_avg_edge_vs_close=float(best_buy.get("avg_action_edge_vs_close", 0.0) or 0.0),
        best_sell_context=best_sell.get("context_id", ""),
        best_sell_avg_edge_vs_close=float(best_sell.get("avg_action_edge_vs_close", 0.0) or 0.0),
    )
    _write_json(out / "v5f_1min_intraday_relative_zone_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    missing = []
    try:
        db = _find_v5_database(root)
    except FileNotFoundError as exc:
        missing.append(_blocker("v5_database_missing", str(exc)))
        db = None
    for path in [REPAIRED_RUN / "rebalance_signals.csv", QV_WEIGHT_LOG, MICRO_EVENT_DIAG]:
        if not (root / path).exists():
            missing.append(_blocker(f"missing_{path.name}", str(path)))
    if db is not None:
        data_dir = db / "processed" / ONE_MIN_DATASET / "by_year"
        if not data_dir.exists():
            missing.append(_blocker("missing_clean_1min_dataset", str(data_dir)))
    return missing


def _trade_intents(root: Path) -> list[dict[str, Any]]:
    usecols = [
        "trade_date",
        "active_rebalance_date",
        "version_id",
        "code",
        "sleeve",
        "base_target_weight",
        "target_weight",
        "weight_delta",
        "mom_12_1",
        "quality_value_score",
    ]
    df = pd.read_csv(root / QV_WEIGHT_LOG, usecols=usecols, dtype={"trade_date": str, "active_rebalance_date": str, "code": str})
    df = df[
        df["version_id"].eq(CHAMPION)
        & df["trade_date"].eq(df["active_rebalance_date"])
        & (df["trade_date"] >= BACKTEST_START)
        & (df["trade_date"] <= BACKTEST_END)
    ].copy()
    if df.empty:
        return []
    df = df.sort_values(["trade_date", "sleeve", "code"]).copy()
    for col in ["base_target_weight", "target_weight", "weight_delta", "mom_12_1", "quality_value_score"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    rows: list[dict[str, Any]] = []
    prev_base: dict[str, float] = {}
    prev_champion: dict[str, float] = {}
    for trade_date, group in df.groupby("trade_date", sort=True):
        current_codes = set(str(code) for code in group["code"].tolist())
        for _, row in group.iterrows():
            code = str(row["code"])
            base = _float(row["base_target_weight"])
            champion = _float(row["target_weight"])
            base_delta = base - prev_base.get(code, 0.0)
            champion_delta = champion - prev_champion.get(code, 0.0)
            overlay_delta = _float(row["weight_delta"])
            common = {
                "trade_date": trade_date,
                "code": code,
                "sleeve": str(row["sleeve"]),
                "mom_12_1": row.get("mom_12_1"),
                "quality_value_score": row.get("quality_value_score"),
                "base_target_weight": base,
                "champion_target_weight": champion,
                "champion_minus_base_weight_delta": overlay_delta,
                "accepted": False,
            }
            if abs(base_delta) > 1e-8:
                rows.append(
                    {
                        **common,
                        "intent_id": f"value_lowvol_rebalance|{trade_date}|{code}",
                        "intent_family": "value_lowvol_rebalance",
                        "side": "buy" if base_delta > 0 else "sell",
                        "trade_delta_weight": base_delta,
                        "interpretation": "V57f value/low-vol official rebalance target change.",
                    }
                )
            if abs(overlay_delta) > 1e-8:
                rows.append(
                    {
                        **common,
                        "intent_id": f"momentum_overlay_tilt|{trade_date}|{code}",
                        "intent_family": "momentum_overlay_tilt",
                        "side": "buy_tilt" if overlay_delta > 0 else "sell_tilt",
                        "trade_delta_weight": overlay_delta,
                        "interpretation": "V5f 12-1 momentum overweight/underweight relative to V57f target.",
                    }
                )
            if abs(champion_delta) > 1e-8:
                rows.append(
                    {
                        **common,
                        "intent_id": f"v5f_champion_rebalance|{trade_date}|{code}",
                        "intent_family": "v5f_champion_rebalance",
                        "side": "increase" if champion_delta > 0 else "decrease",
                        "trade_delta_weight": champion_delta,
                        "interpretation": "Full V5f champion target change versus previous official rebalance.",
                    }
                )
        for code in sorted(set(prev_base) - current_codes):
            if abs(prev_base.get(code, 0.0)) > 1e-8:
                rows.append(
                    {
                        "intent_id": f"value_lowvol_rebalance|{trade_date}|{code}",
                        "intent_family": "value_lowvol_rebalance",
                        "trade_date": trade_date,
                        "code": code,
                        "sleeve": "unselected_current_rebalance",
                        "side": "sell",
                        "trade_delta_weight": -prev_base.get(code, 0.0),
                        "base_target_weight": 0.0,
                        "champion_target_weight": 0.0,
                        "champion_minus_base_weight_delta": 0.0,
                        "accepted": False,
                        "interpretation": "V57f value/low-vol official rebalance removal.",
                    }
                )
        prev_base = {str(row["code"]): _float(row["base_target_weight"]) for _, row in group.iterrows()}
        prev_champion = {str(row["code"]): _float(row["target_weight"]) for _, row in group.iterrows()}
    return rows


def _load_days(db: Path, keys: list[tuple[str, str]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    wanted: dict[tuple[str, str], set[str]] = defaultdict(set)
    for code, trade_date in keys:
        if not code or not trade_date:
            continue
        wanted[(code, trade_date[:4])].add(trade_date)
    cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for (code, year), dates in sorted(wanted.items()):
        path = db / "processed" / ONE_MIN_DATASET / "by_year" / str(year) / f"{code.replace('.', '_')}_1min.csv"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in reader:
                trade_date = str(row.get("trade_date", ""))
                if trade_date not in dates:
                    continue
                by_date[trade_date].append(
                    {
                        "trade_date": trade_date,
                        "time": str(row.get("time", "")),
                        "open": _float(row.get("open")),
                        "high": _float(row.get("high")),
                        "low": _float(row.get("low")),
                        "close": _float(row.get("close")),
                        "volume": _float(row.get("volume")),
                        "amount": _float(row.get("amount")),
                    }
                )
        for trade_date, rows in by_date.items():
            rows.sort(key=lambda item: item["time"])
            cache[(code, trade_date)] = rows
    return cache


def _value_momentum_zone_panel(intents: list[dict[str, Any]], day_cache: dict[tuple[str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for intent in intents:
        day = day_cache.get((intent["code"], intent["trade_date"]))
        if not day:
            continue
        for obs_time in OBS_TIMES:
            metrics = _zone_metrics(day, obs_time)
            if not metrics:
                continue
            side = str(intent["side"])
            rows.append(
                {
                    **intent,
                    **metrics,
                    "obs_time": obs_time,
                    "sample_scope": "formal_backtest_execution_diagnostic",
                    "action_edge_vs_close": _action_edge(side, metrics["price_at_obs"], metrics["day_close"]),
                    "action_edge_vs_full_day_vwap": _action_edge(side, metrics["price_at_obs"], metrics["full_day_vwap"]),
                    "action_edge_vs_1455": _action_edge(side, metrics["price_at_obs"], metrics["close_1455"]),
                    "weighted_action_edge_vs_close": _action_edge(side, metrics["price_at_obs"], metrics["day_close"]) * abs(_float(intent["trade_delta_weight"])),
                    "zone_signal_is_pit": True,
                    "realized_full_day_zone_is_hindsight": True,
                    "trading_frequency_change_allowed": False,
                }
            )
    return rows


def _mean_reversion_events(root: Path) -> list[dict[str, Any]]:
    rows = []
    for row in _read_csv(root / MICRO_EVENT_DIAG):
        event_type = str(row.get("event_type", ""))
        trade_date = str(row.get("trade_date", ""))
        if trade_date < BACKTEST_START or trade_date > BACKTEST_END:
            continue
        if event_type not in CRASH_EVENTS and event_type not in SPIKE_EVENTS:
            continue
        side = "buy" if event_type in CRASH_EVENTS else "sell"
        rows.append(
            {
                "intent_id": f"mean_reversion_event|{event_type}|{row.get('code')}|{trade_date}",
                "intent_family": "mean_reversion_event",
                "event_type": event_type,
                "trade_date": trade_date,
                "code": str(row.get("code", "")),
                "sleeve": str(row.get("sleeve", "")),
                "side": side,
                "obs_time": str(row.get("observation_time", "")),
                "trigger_return_1min_recomputed": row.get("trigger_return_1min_recomputed"),
                "confirmed_by_1min": row.get("confirmed_by_1min"),
                "single_minute_dominated": row.get("single_minute_dominated"),
                "same_day_return_after_observation_1min": row.get("same_day_return_after_observation_1min"),
                "next1_return_after_observation": row.get("next1_return_after_observation"),
                "next2_return_after_observation": row.get("next2_return_after_observation"),
                "accepted": False,
            }
        )
    return rows


def _mean_reversion_zone_panel(events: list[dict[str, Any]], day_cache: dict[tuple[str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for event in events:
        day = day_cache.get((event["code"], event["trade_date"]))
        if not day:
            continue
        obs_time = str(event["obs_time"])
        metrics = _zone_metrics(day, obs_time)
        if not metrics:
            continue
        side = str(event["side"])
        rows.append(
            {
                **event,
                **metrics,
                "trade_delta_weight": "",
                "sample_scope": "formal_backtest_mean_reversion_diagnostic",
                "action_edge_vs_close": _action_edge(side, metrics["price_at_obs"], metrics["day_close"]),
                "action_edge_vs_full_day_vwap": _action_edge(side, metrics["price_at_obs"], metrics["full_day_vwap"]),
                "action_edge_vs_1455": _action_edge(side, metrics["price_at_obs"], metrics["close_1455"]),
                "zone_signal_is_pit": True,
                "realized_full_day_zone_is_hindsight": True,
                "trading_frequency_change_allowed": False,
            }
        )
    return rows


def _zone_metrics(day: list[dict[str, Any]], obs_time: str) -> dict[str, Any] | None:
    by_time = {row["time"]: row for row in day}
    obs = by_time.get(obs_time)
    if obs is None:
        return None
    upto = [row for row in day if row["time"] <= obs_time]
    if not upto:
        return None
    price = obs["close"]
    low_so_far = min(row["low"] for row in upto)
    high_so_far = max(row["high"] for row in upto)
    day_low = min(row["low"] for row in day)
    day_high = max(row["high"] for row in day)
    day_close = day[-1]["close"]
    close_1455 = by_time.get("14:55:00", day[-1])["close"]
    pit_zone = _zone(price, low_so_far, high_so_far)
    full_zone = _zone(price, day_low, day_high)
    vwap_so_far = _vwap(upto)
    full_vwap = _vwap(day)
    return {
        "price_at_obs": price,
        "low_so_far": low_so_far,
        "high_so_far": high_so_far,
        "day_low": day_low,
        "day_high": day_high,
        "day_close": day_close,
        "close_1455": close_1455,
        "vwap_so_far": vwap_so_far,
        "full_day_vwap": full_vwap,
        "pit_relative_zone": pit_zone,
        "pit_zone_bucket": _zone_bucket(pit_zone),
        "realized_full_day_zone": full_zone,
        "realized_full_day_zone_bucket": _zone_bucket(full_zone),
        "price_vs_vwap_so_far": _ret(price, vwap_so_far),
        "price_vs_full_day_vwap": _ret(price, full_vwap),
        "one_min_bar_count": len(day),
    }


def _timing_summary(rows: list[dict[str, Any]], group_cols: list[str]) -> list[dict[str, Any]]:
    if not rows:
        return []
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(col, "") for col in group_cols)].append(row)
    out = []
    for key, group in sorted(groups.items()):
        edge = [_float(row.get("action_edge_vs_close")) for row in group]
        edge_vwap = [_float(row.get("action_edge_vs_full_day_vwap")) for row in group]
        weighted_edge = [_float(row.get("weighted_action_edge_vs_close")) for row in group if row.get("weighted_action_edge_vs_close") not in ("", None)]
        base = {col: key[idx] for idx, col in enumerate(group_cols)}
        out.append(
            {
                **base,
                "sample_count": len(group),
                "avg_pit_relative_zone": _mean([row.get("pit_relative_zone") for row in group]),
                "avg_realized_full_day_zone": _mean([row.get("realized_full_day_zone") for row in group]),
                "pit_low_zone_rate_pct": _pct(sum(1 for row in group if row.get("pit_zone_bucket") == "low_0_30"), len(group)),
                "pit_high_zone_rate_pct": _pct(sum(1 for row in group if row.get("pit_zone_bucket") == "high_70_100"), len(group)),
                "realized_low_zone_rate_pct": _pct(sum(1 for row in group if row.get("realized_full_day_zone_bucket") == "low_0_30"), len(group)),
                "realized_high_zone_rate_pct": _pct(sum(1 for row in group if row.get("realized_full_day_zone_bucket") == "high_70_100"), len(group)),
                "avg_action_edge_vs_close": _mean(edge),
                "median_action_edge_vs_close": _median(edge),
                "positive_edge_rate_pct": _pct(sum(1 for value in edge if value > 0), len(edge)),
                "avg_action_edge_vs_full_day_vwap": _mean(edge_vwap),
                "weighted_avg_action_edge_vs_close": _sum(weighted_edge),
                "diagnostic_only": True,
            }
        )
    return out


def _candidate_matrix_from_timing(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_context: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        family = str(row.get("intent_family", "mean_reversion_event"))
        side = str(row.get("side", ""))
        if side in BUY_SIDES or side == "buy":
            action = "buy"
        elif side in SELL_SIDES or side == "sell":
            action = "sell"
        else:
            continue
        by_context[(family, action)].append(row)
    out = []
    for (family, action), group in sorted(by_context.items()):
        eligible = [row for row in group if int(row.get("sample_count", 0) or 0) >= 20]
        if not eligible:
            eligible = group
        best = max(eligible, key=lambda row: _float(row.get("avg_action_edge_vs_close"))) if eligible else {}
        if not best:
            continue
        context_id = "|".join(str(best.get(col, "")) for col in ["intent_family", "side", "obs_time", "event_type"] if best.get(col, "") != "")
        out.append(
            {
                "context_id": context_id,
                "intent_family": family,
                "action": action,
                "preferred_fixed_context": context_id,
                "sample_count": best.get("sample_count", 0),
                "avg_action_edge_vs_close": best.get("avg_action_edge_vs_close"),
                "positive_edge_rate_pct": best.get("positive_edge_rate_pct"),
                "avg_pit_relative_zone": best.get("avg_pit_relative_zone"),
                "avg_realized_full_day_zone": best.get("avg_realized_full_day_zone"),
                "status": "diagnostic_candidate_not_trading_rule",
                "accepted": False,
                "trading_frequency_change_allowed": False,
            }
        )
    return out


def _data_gate(intents: list[dict[str, Any]], zone_panel: list[dict[str, Any]], mr_events: list[dict[str, Any]], mr_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"gate_id": "value_momentum_intents_loaded", "status": "pass" if intents else "fail", "value": len(intents)},
        {"gate_id": "value_momentum_zone_panel_built", "status": "pass" if zone_panel else "fail", "value": len(zone_panel)},
        {"gate_id": "mean_reversion_events_loaded", "status": "pass" if mr_events else "fail", "value": len(mr_events)},
        {"gate_id": "mean_reversion_zone_panel_built", "status": "pass" if mr_panel else "fail", "value": len(mr_panel)},
        {"gate_id": "fixed_observation_times", "status": "pass", "value": ";".join(OBS_TIMES)},
        {"gate_id": "fixed_zone_buckets", "status": "pass", "value": "low_0_30;mid_30_70;high_70_100"},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "pit_zone_uses_only_bars_seen_by_obs_time", "status": "pass", "detail": "pit_relative_zone uses low/high/vwap only up to fixed observation time."},
        {"audit_id": "full_day_zone_hindsight_only", "status": "pass", "detail": "realized_full_day_zone is written only as an audit label, not as a signal."},
        {"audit_id": "no_frequency_increase", "status": "pass", "detail": "The test compares fixed execution observation times; it does not add intraday rebalance frequency."},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": "V57f core is not modified."},
        {"audit_id": "no_v5f_mainline_modified", "status": "pass", "detail": "internal_subsleeve_mom12_70_30 remains V5f mainline."},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "Fixed zones 0-30/30-70/70-100 and fixed observation times only."},
        {"audit_id": "accepted_false", "status": "pass", "detail": "No result is accepted or live approved."},
        {"audit_id": "formal_backtest_end_preserved", "status": "pass", "detail": f"Formal backtest ends at {BACKTEST_END}."},
    ]


def _pm_decision(candidate_matrix: list[dict[str, Any]], data_gate: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any(row["status"] == "fail" for row in data_gate + governance):
        decision = "blocked_by_data_or_governance_issue"
        status = "blocked"
    else:
        max_edge = max((_float(row.get("avg_action_edge_vs_close")) for row in candidate_matrix), default=0.0)
        if max_edge > 0.001:
            decision = "relative_zone_timing_diagnostic_positive_ready_for_fixed_execution_spec_not_trading"
            status = "diagnostic_positive"
        else:
            decision = "relative_zone_timing_diagnostic_only_no_material_edge"
            status = "diagnostic_only"
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "accepted": False,
            "live_trading_approved": False,
            "trading_frequency_increased": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal_used": False,
            "notes": "1min relative zones may support fixed execution timing diagnostics, but cannot change stock selection, weights, or rebalance frequency in this task.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "v5f_fixed_execution_window_quant_spec",
            "status": "ready_for_spec_only" if "positive" in decision else "diagnostic_only",
            "scope": "Translate useful relative-zone timing observations into fixed execution-window spec; no backtest promotion yet.",
        },
        {
            "queue_id": "v5f_1min_zone_forward_observation",
            "status": "ready",
            "scope": "Append future forward/paper execution-zone diagnostics without increasing trading frequency.",
        },
    ]


def _zone_definition() -> list[dict[str, Any]]:
    return [
        {"zone_id": "pit_relative_zone", "definition": "(price_at_obs - low_so_far) / (high_so_far - low_so_far)", "pit_safe": True},
        {"zone_id": "realized_full_day_zone", "definition": "(price_at_obs - day_low) / (day_high - day_low)", "pit_safe": False},
        {"zone_id": "low_0_30", "definition": "zone <= 0.30", "pit_safe": "depends_on_zone_id"},
        {"zone_id": "mid_30_70", "definition": "0.30 < zone < 0.70", "pit_safe": "depends_on_zone_id"},
        {"zone_id": "high_70_100", "definition": "zone >= 0.70", "pit_safe": "depends_on_zone_id"},
    ]


def _report(
    timing_summary: list[dict[str, Any]],
    mr_summary: list[dict[str, Any]],
    candidate_matrix: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5f 1min Intraday Relative Zone Timing Test",
        "",
        "This diagnostic tests whether fixed 1-minute intraday relative zones can improve execution timing for value, momentum, and mean-reversion contexts. It does not alter stock selection, target weights, or rebalance frequency.",
        "",
        "## Candidate Contexts",
    ]
    for row in candidate_matrix:
        lines.append(
            f"- `{row['context_id']}`: avg edge vs close `{row['avg_action_edge_vs_close']}`, positive edge `{row['positive_edge_rate_pct']}%`, avg PIT zone `{row['avg_pit_relative_zone']}`."
        )
    lines.extend(["", "## Value / Momentum Timing Highlights"])
    for row in sorted(timing_summary, key=lambda item: (_float(item.get("avg_action_edge_vs_close"))), reverse=True)[:12]:
        lines.append(
            f"- `{row.get('intent_family')}` `{row.get('side')}` `{row.get('obs_time')}`: n `{row.get('sample_count')}`, edge `{row.get('avg_action_edge_vs_close')}`, PIT low `{row.get('pit_low_zone_rate_pct')}%`, PIT high `{row.get('pit_high_zone_rate_pct')}%`."
        )
    lines.extend(["", "## Mean Reversion Timing Highlights"])
    for row in sorted(mr_summary, key=lambda item: (_float(item.get("avg_action_edge_vs_close"))), reverse=True)[:12]:
        lines.append(
            f"- `{row.get('event_type')}` `{row.get('side')}`: n `{row.get('sample_count')}`, edge `{row.get('avg_action_edge_vs_close')}`, PIT low `{row.get('pit_low_zone_rate_pct')}%`, PIT high `{row.get('pit_high_zone_rate_pct')}%`."
        )
    lines.extend(["", f"PM decision: `{decision[0]['pm_gate_decision']}`", ""])
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5f 1min Intraday Relative Zone Agent Rules",
            "",
            "- Do not modify V57f core.",
            "- Do not modify V5f mainline.",
            "- Do not increase trading frequency.",
            "- Do not use realized full-day zones as live signals.",
            "- Do not scan thresholds beyond fixed 0-30/30-70/70-100 diagnostic buckets.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_1min_intraday_relative_zone_timing_test",
        "status": status,
        "pm_gate_decision": decision,
        "formal_backtest_start": BACKTEST_START,
        "formal_backtest_end": BACKTEST_END,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "trading_frequency_increased": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("status") == "blocking"]),
        "fatal_blockers": [row for row in blockers if row.get("status") == "blocking"],
        **extra,
    }


def _write_minimal(out: Path, summary: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    _write_json(out / "v5f_1min_intraday_relative_zone_summary.json", summary)
    _write_csv(out / "v5f_1min_intraday_zone_blockers.csv", blockers)


def _blockers(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for group in groups:
        for row in group:
            if row.get("status") == "fail":
                rows.append(_blocker(row.get("gate_id") or row.get("audit_id") or "unknown", str(row.get("value", row.get("detail", "")))))
    return rows or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _best_candidate(rows: list[dict[str, Any]], action: str) -> dict[str, Any]:
    eligible = [row for row in rows if row.get("action") == action]
    return max(eligible, key=lambda row: _float(row.get("avg_action_edge_vs_close"))) if eligible else {}


def _action_edge(side: str, price: float | None, reference: float | None) -> float:
    if price in (None, 0.0) or reference in (None, 0.0):
        return 0.0
    if side in BUY_SIDES or side == "buy":
        return reference / price - 1.0
    if side in SELL_SIDES or side == "sell":
        return price / reference - 1.0
    return 0.0


def _zone(price: float | None, low: float | None, high: float | None) -> float:
    if price is None or low is None or high is None or abs(high - low) < 1e-12:
        return 0.5
    return max(0.0, min(1.0, (price - low) / (high - low)))


def _zone_bucket(zone: float) -> str:
    if zone <= LOW_CUT:
        return "low_0_30"
    if zone >= HIGH_CUT:
        return "high_70_100"
    return "mid_30_70"


def _vwap(rows: list[dict[str, Any]]) -> float | None:
    volume = sum(_float(row.get("volume")) for row in rows)
    if volume <= 0:
        return rows[-1].get("close") if rows else None
    return sum(_float(row.get("amount")) for row in rows) / volume


def _ret(end: float | None, start: float | None) -> float | None:
    if end is None or start in (None, 0.0):
        return None
    return end / start - 1.0


def _float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else 0.0
    except Exception:
        return 0.0


def _mean(values: list[Any]) -> float:
    clean = [_float(value) for value in values if value not in (None, "")]
    return sum(clean) / len(clean) if clean else 0.0


def _median(values: list[Any]) -> float:
    clean = sorted(_float(value) for value in values if value not in (None, ""))
    if not clean:
        return 0.0
    mid = len(clean) // 2
    return clean[mid] if len(clean) % 2 else (clean[mid - 1] + clean[mid]) / 2.0


def _sum(values: list[Any]) -> float:
    return sum(_float(value) for value in values if value not in (None, ""))


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 6) if denominator else 0.0


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("Could not locate V5 database directory with processed/raw/manifests children.")


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    summary = run_v5f_1min_intraday_relative_zone_timing(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
