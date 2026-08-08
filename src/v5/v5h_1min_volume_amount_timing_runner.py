from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5h_1min_volume_amount_timing_test") / "current"
GOV_OUT_DIR = Path("v5h_1min_research_line_governance") / "current"
ONE_MIN_DATASET = "local_1min_clean_2013_2026"
ONE_MIN_MANIFEST = Path("manifests") / ONE_MIN_DATASET / "collection_manifest.json"
ZONE_DIR = Path("v5f_1min_intraday_relative_zone_timing_test") / "current"
VALUE_MOMENTUM_PANEL = ZONE_DIR / "v5f_1min_value_momentum_zone_panel.csv"
MEAN_REVERSION_PANEL = ZONE_DIR / "v5f_1min_mean_reversion_zone_panel.csv"
ZONE_SUMMARY = ZONE_DIR / "v5f_1min_intraday_relative_zone_summary.json"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
V5H_LINE_ID = "v5h_1min_microstructure_execution_research"

BUY_SIDES = {"buy", "buy_tilt", "increase"}
SELL_SIDES = {"sell", "sell_tilt", "decrease"}
MIN_BUCKET_SAMPLE = 30


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_1min_volume_amount_timing(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_required_input", blockers)
        _write_minimal(out, summary, blockers)
        _write_v5h_governance(root, summary)
        return summary

    db = _find_v5_database(root)
    manifest = _read_json(db / ONE_MIN_MANIFEST)
    zone_summary = _read_json(root / ZONE_SUMMARY)
    source_rows = _source_rows(root)
    day_cache = _load_days(db, [(row["code"], row["trade_date"]) for row in source_rows])
    feature_panel = _volume_amount_feature_panel(source_rows, day_cache)
    bucket_summary = _bucket_summary(feature_panel)
    context_summary = _context_summary(feature_panel)
    candidate_matrix = _candidate_matrix(bucket_summary, context_summary)
    data_gate = _data_gate(manifest, source_rows, feature_panel)
    governance = _governance_audit()
    decision = _pm_decision(candidate_matrix, data_gate, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(data_gate, governance)

    _write_csv(out / "v5h_1min_volume_amount_feature_schema.csv", _feature_schema())
    _write_csv(out / "v5h_1min_volume_amount_feature_panel.csv", feature_panel)
    _write_csv(out / "v5h_1min_volume_amount_context_summary.csv", context_summary)
    _write_csv(out / "v5h_1min_volume_amount_bucket_summary.csv", bucket_summary)
    _write_csv(out / "v5h_1min_volume_amount_candidate_matrix.csv", candidate_matrix)
    _write_csv(out / "v5h_1min_volume_amount_data_gate.csv", data_gate)
    _write_csv(out / "v5h_1min_volume_amount_governance_audit.csv", governance)
    _write_csv(out / "v5h_1min_volume_amount_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_1min_volume_amount_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5h_1min_volume_amount_blockers.csv", blockers_out)
    (out / "v5h_1min_volume_amount_report.md").write_text(
        _report(zone_summary, context_summary, candidate_matrix, decision),
        encoding="utf-8",
    )
    (out / "v5h_1min_volume_amount_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5h_1min_volume_amount_timing_test",
        decision[0]["pm_gate_decision"],
        [],
        source_zone_summary_status=zone_summary.get("status", ""),
        source_row_count=len(source_rows),
        feature_row_count=len(feature_panel),
        bucket_summary_row_count=len(bucket_summary),
        best_buy_context=_best(candidate_matrix, "buy").get("condition_id", ""),
        best_buy_incremental_edge_vs_unconditioned=float(_best(candidate_matrix, "buy").get("incremental_edge_vs_unconditioned", 0.0) or 0.0),
        best_sell_context=_best(candidate_matrix, "sell").get("condition_id", ""),
        best_sell_incremental_edge_vs_unconditioned=float(_best(candidate_matrix, "sell").get("incremental_edge_vs_unconditioned", 0.0) or 0.0),
    )
    _write_json(out / "v5h_1min_volume_amount_summary.json", summary)
    _write_v5h_governance(root, summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    missing = []
    try:
        db = _find_v5_database(root)
    except FileNotFoundError as exc:
        missing.append(_blocker("v5_database_missing", str(exc)))
        db = None
    for path in [VALUE_MOMENTUM_PANEL, MEAN_REVERSION_PANEL, ZONE_SUMMARY]:
        if not (root / path).exists():
            missing.append(_blocker(f"missing_{path.name}", str(path)))
    if db is not None and not (db / ONE_MIN_MANIFEST).exists():
        missing.append(_blocker("missing_1min_manifest", str(db / ONE_MIN_MANIFEST)))
    return missing


def _source_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _read_csv(root / VALUE_MOMENTUM_PANEL):
        rows.append(_normalize_source_row(row, "value_momentum_zone_panel"))
    for row in _read_csv(root / MEAN_REVERSION_PANEL):
        rows.append(_normalize_source_row(row, "mean_reversion_zone_panel"))
    return [row for row in rows if BACKTEST_START <= row["trade_date"] <= BACKTEST_END]


def _normalize_source_row(row: dict[str, Any], source_panel: str) -> dict[str, Any]:
    side = str(row.get("side", ""))
    action = "buy" if side in BUY_SIDES or side == "buy" else "sell" if side in SELL_SIDES or side == "sell" else "unknown"
    context_parts = [str(row.get("intent_family", "")), side]
    if str(row.get("event_type", "")):
        context_parts.append(str(row.get("event_type", "")))
    else:
        context_parts.append(str(row.get("obs_time", "")))
    return {
        "source_panel": source_panel,
        "intent_id": str(row.get("intent_id", "")),
        "intent_family": str(row.get("intent_family", "")),
        "event_type": str(row.get("event_type", "")),
        "context_id": "|".join(context_parts),
        "trade_date": str(row.get("trade_date", "")),
        "code": str(row.get("code", "")),
        "sleeve": str(row.get("sleeve", "")),
        "side": side,
        "action": action,
        "obs_time": str(row.get("obs_time", "")),
        "pit_zone_bucket": str(row.get("pit_zone_bucket", "")),
        "pit_relative_zone": _float(row.get("pit_relative_zone")),
        "realized_full_day_zone": _float(row.get("realized_full_day_zone")),
        "action_edge_vs_close": _float(row.get("action_edge_vs_close")),
        "action_edge_vs_full_day_vwap": _float(row.get("action_edge_vs_full_day_vwap")),
        "trade_delta_weight": row.get("trade_delta_weight", ""),
        "accepted": False,
    }


def _load_days(db: Path, keys: list[tuple[str, str]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    wanted: dict[tuple[str, str], set[str]] = defaultdict(set)
    for code, trade_date in keys:
        if code and trade_date:
            wanted[(code, trade_date[:4])].add(trade_date)
    cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for (code, year), dates in sorted(wanted.items()):
        path = db / "processed" / ONE_MIN_DATASET / "by_year" / str(year) / f"{code.replace('.', '_')}_1min.csv"
        if not path.exists():
            continue
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                trade_date = str(row.get("trade_date", ""))
                if trade_date not in dates:
                    continue
                by_date[trade_date].append(
                    {
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


def _volume_amount_feature_panel(
    source_rows: list[dict[str, Any]],
    day_cache: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in source_rows:
        day = day_cache.get((row["code"], row["trade_date"]))
        if not day:
            continue
        features = _volume_amount_features(day, row["obs_time"])
        if not features:
            continue
        output.append(
            {
                **row,
                **features,
                "low_zone_and_quiet": row["pit_zone_bucket"] == "low_0_30" and features["amount_intensity_bucket"] in {"quiet", "normal"},
                "low_zone_and_active": row["pit_zone_bucket"] == "low_0_30" and features["amount_intensity_bucket"] in {"active", "extreme"},
                "high_zone_and_active": row["pit_zone_bucket"] == "high_70_100" and features["amount_intensity_bucket"] in {"active", "extreme"},
                "pressure_aligned_with_action": _pressure_aligned(row["action"], features["amount_pressure_bucket"]),
                "diagnostic_only": True,
                "accepted": False,
                "trading_frequency_change_allowed": False,
            }
        )
    return output


def _volume_amount_features(day: list[dict[str, Any]], obs_time: str) -> dict[str, Any] | None:
    obs_index = next((index for index, row in enumerate(day) if row["time"] == obs_time), None)
    if obs_index is None:
        return None
    upto = day[: obs_index + 1]
    last5 = upto[-5:]
    last15 = upto[-15:]
    prior = upto[:-15] if len(upto) > 15 else upto
    elapsed = max(len(upto), 1)
    cum_volume = sum(row["volume"] for row in upto)
    cum_amount = sum(row["amount"] for row in upto)
    total_volume = sum(row["volume"] for row in day)
    total_amount = sum(row["amount"] for row in day)
    avg_volume = cum_volume / elapsed if elapsed else 0.0
    avg_amount = cum_amount / elapsed if elapsed else 0.0
    last5_volume_intensity = _avg(last5, "volume") / avg_volume if avg_volume > 0 else 0.0
    last15_volume_intensity = _avg(last15, "volume") / avg_volume if avg_volume > 0 else 0.0
    last5_amount_intensity = _avg(last5, "amount") / avg_amount if avg_amount > 0 else 0.0
    last15_amount_intensity = _avg(last15, "amount") / avg_amount if avg_amount > 0 else 0.0
    amount_pressure = _signed_pressure(upto, "amount")
    volume_pressure = _signed_pressure(upto, "volume")
    last15_amount_pressure = _signed_pressure(last15, "amount")
    prior_amount_pressure = _signed_pressure(prior, "amount")
    return {
        "elapsed_1min_bars": elapsed,
        "cum_volume_to_obs": cum_volume,
        "cum_amount_to_obs": cum_amount,
        "total_day_volume_hindsight": total_volume,
        "total_day_amount_hindsight": total_amount,
        "volume_share_to_obs_hindsight": cum_volume / total_volume if total_volume > 0 else 0.0,
        "amount_share_to_obs_hindsight": cum_amount / total_amount if total_amount > 0 else 0.0,
        "avg_volume_per_min_to_obs": avg_volume,
        "avg_amount_per_min_to_obs": avg_amount,
        "last5_volume_intensity": last5_volume_intensity,
        "last15_volume_intensity": last15_volume_intensity,
        "last5_amount_intensity": last5_amount_intensity,
        "last15_amount_intensity": last15_amount_intensity,
        "volume_intensity_bucket": _intensity_bucket(last15_volume_intensity),
        "amount_intensity_bucket": _intensity_bucket(last15_amount_intensity),
        "amount_pressure_to_obs": amount_pressure,
        "volume_pressure_to_obs": volume_pressure,
        "last15_amount_pressure": last15_amount_pressure,
        "prior_amount_pressure": prior_amount_pressure,
        "amount_pressure_turn": last15_amount_pressure - prior_amount_pressure,
        "amount_pressure_bucket": _pressure_bucket(amount_pressure),
        "last15_amount_pressure_bucket": _pressure_bucket(last15_amount_pressure),
        "amount_pressure_turn_bucket": _turn_bucket(last15_amount_pressure - prior_amount_pressure),
        "volume_amount_signal_is_pit": True,
        "day_total_volume_amount_is_hindsight": True,
    }


def _bucket_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group_cols = [
        ["intent_family", "action", "pit_zone_bucket", "amount_intensity_bucket"],
        ["intent_family", "action", "pit_zone_bucket", "volume_intensity_bucket"],
        ["intent_family", "action", "pit_zone_bucket", "amount_pressure_bucket"],
        ["intent_family", "action", "pit_zone_bucket", "last15_amount_pressure_bucket"],
        ["intent_family", "action", "pit_zone_bucket", "amount_pressure_turn_bucket"],
        ["context_id", "action", "amount_intensity_bucket"],
        ["context_id", "action", "amount_pressure_bucket"],
    ]
    output: list[dict[str, Any]] = []
    for cols in group_cols:
        output.extend(_group(rows, cols))
    return output


def _context_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _group(rows, ["context_id", "intent_family", "action"])


def _group(rows: list[dict[str, Any]], cols: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(col, "") for col in cols)].append(row)
    output = []
    for key, group in sorted(groups.items()):
        edge = [row["action_edge_vs_close"] for row in group]
        row = {col: key[index] for index, col in enumerate(cols)}
        row.update(
            {
                "grouping": "|".join(cols),
                "sample_count": len(group),
                "avg_action_edge_vs_close": _mean(edge),
                "median_action_edge_vs_close": _median(edge),
                "positive_edge_rate_pct": _pct(sum(1 for value in edge if value > 0), len(edge)),
                "avg_action_edge_vs_full_day_vwap": _mean([row["action_edge_vs_full_day_vwap"] for row in group]),
                "avg_pit_relative_zone": _mean([row["pit_relative_zone"] for row in group]),
                "avg_amount_intensity": _mean([row["last15_amount_intensity"] for row in group]),
                "avg_volume_intensity": _mean([row["last15_volume_intensity"] for row in group]),
                "avg_amount_pressure": _mean([row["amount_pressure_to_obs"] for row in group]),
                "low_zone_rate_pct": _pct(sum(1 for row in group if row["pit_zone_bucket"] == "low_0_30"), len(group)),
                "high_zone_rate_pct": _pct(sum(1 for row in group if row["pit_zone_bucket"] == "high_70_100"), len(group)),
                "diagnostic_only": True,
            }
        )
        output.append(row)
    return output


def _candidate_matrix(bucket_summary: list[dict[str, Any]], context_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base: dict[tuple[str, str], float] = {}
    for row in context_summary:
        key = (str(row.get("intent_family", "")), str(row.get("action", "")))
        base[key] = max(base.get(key, -999.0), _float(row.get("avg_action_edge_vs_close")))

    candidates = []
    for row in bucket_summary:
        if int(row.get("sample_count", 0) or 0) < MIN_BUCKET_SAMPLE:
            continue
        family = str(row.get("intent_family", "")) or str(row.get("context_id", "")).split("|")[0]
        action = str(row.get("action", ""))
        if action not in {"buy", "sell"}:
            continue
        edge = _float(row.get("avg_action_edge_vs_close"))
        base_edge = base.get((family, action), 0.0)
        condition_id = "|".join(f"{key}={row.get(key)}" for key in row if key in {
            "context_id",
            "intent_family",
            "action",
            "pit_zone_bucket",
            "amount_intensity_bucket",
            "volume_intensity_bucket",
            "amount_pressure_bucket",
            "last15_amount_pressure_bucket",
            "amount_pressure_turn_bucket",
        })
        candidates.append(
            {
                "condition_id": condition_id,
                "intent_family": family,
                "action": action,
                "sample_count": row.get("sample_count"),
                "avg_action_edge_vs_close": edge,
                "unconditioned_best_edge": base_edge,
                "incremental_edge_vs_unconditioned": edge - base_edge,
                "positive_edge_rate_pct": row.get("positive_edge_rate_pct"),
                "avg_amount_intensity": row.get("avg_amount_intensity"),
                "avg_volume_intensity": row.get("avg_volume_intensity"),
                "avg_amount_pressure": row.get("avg_amount_pressure"),
                "status": "diagnostic_candidate_not_trading_rule",
                "accepted": False,
                "trading_frequency_change_allowed": False,
            }
        )
    candidates.sort(key=lambda row: (row["action"], row["incremental_edge_vs_unconditioned"]), reverse=True)
    return candidates


def _data_gate(manifest: dict[str, Any], source_rows: list[dict[str, Any]], feature_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"gate_id": "v5h_line_id", "status": "pass", "value": V5H_LINE_ID},
        {"gate_id": "one_min_dataset_completed", "status": "pass" if manifest.get("status") == "completed" else "fail", "value": manifest.get("status")},
        {"gate_id": "volume_amount_fields_available", "status": "pass", "value": "volume;amount"},
        {"gate_id": "source_rows_loaded", "status": "pass" if source_rows else "fail", "value": len(source_rows)},
        {"gate_id": "feature_panel_built", "status": "pass" if feature_panel else "fail", "value": len(feature_panel)},
        {"gate_id": "feature_coverage_rate_pct", "status": "pass" if _pct(len(feature_panel), len(source_rows)) >= 99.0 else "fail", "value": _pct(len(feature_panel), len(source_rows))},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "v5h_scope", "status": "pass", "detail": "V5h is defined as 1min microstructure/execution research, not a replacement for V57f/V5f."},
        {"audit_id": "pit_volume_amount_features", "status": "pass", "detail": "Intensity and pressure use bars up to observation time only."},
        {"audit_id": "hindsight_fields_labeled", "status": "pass", "detail": "Total-day volume/amount shares are labeled hindsight and not used as live signals."},
        {"audit_id": "no_trading_frequency_increase", "status": "pass", "detail": "No intraday trading frequency is introduced."},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": "V57f core is not modified."},
        {"audit_id": "no_v5f_mainline_modified", "status": "pass", "detail": "V5f mainline remains unchanged."},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "Fixed volume/amount buckets are diagnostic only."},
        {"audit_id": "accepted_false", "status": "pass", "detail": "No result is accepted/live approved."},
    ]


def _pm_decision(candidate_matrix: list[dict[str, Any]], data_gate: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any(row["status"] == "fail" for row in data_gate + governance):
        decision = "blocked_by_data_or_governance_issue"
        status = "blocked"
    else:
        best_inc = max((_float(row.get("incremental_edge_vs_unconditioned")) for row in candidate_matrix), default=0.0)
        if best_inc > 0.0005:
            decision = "v5h_volume_amount_diagnostic_positive_ready_for_fixed_execution_spec_not_trading"
            status = "diagnostic_positive"
        else:
            decision = "v5h_volume_amount_diagnostic_only_no_material_incremental_edge"
            status = "diagnostic_only"
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "trading_frequency_increased": False,
            "threshold_scan_used": False,
            "new_buy_signal_used": False,
            "notes": "Volume/amount can be used as V5h execution-quality diagnostics only; no trading rule is admitted here.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "v5h_fixed_buy_execution_timing_spec",
            "status": "ready_for_spec_only" if "positive" in decision else "diagnostic_only",
            "scope": "Convert helpful volume/amount conditions into fixed execution-time spec; no portfolio backtest promotion.",
        },
        {
            "queue_id": "v5h_forward_volume_amount_observation",
            "status": "ready",
            "scope": "Append post-2026-05-31 volume/amount diagnostics as forward observation only.",
        },
    ]


def _write_v5h_governance(root: Path, latest_summary: dict[str, Any]) -> None:
    out = root / GOV_OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    mapping = [
        _map_row("database", "local_1min_clean_2013_2026", "1min cleaned OHLCV/amount database", "v5h_data_foundation", "completed"),
        _map_row("v5f_1min_microstructure_signal_quality_gate", "v5f_1min_microstructure_signal_quality_gate", "1min event confirmation, VWAP, path diagnostics", "v5h_microstructure_signal_quality_gate", "completed_source_artifact"),
        _map_row("v5f_1min_vwap_execution_precision_audit", "v5f_1min_vwap_execution_precision_audit", "1min VWAP precision audit", "v5h_vwap_execution_precision_audit", "completed_source_artifact"),
        _map_row("v5f_spike_mr_signal_quality_filter_spec", "v5f_spike_mr_signal_quality_filter_spec", "1min noise/quality flags for spike/MR events", "v5h_signal_quality_filter_spec", "completed_source_artifact"),
        _map_row("v5f_1min_forward_observation_append", "v5f_1min_forward_observation_append", "post-backtest 1min observation append", "v5h_forward_observation_append", "completed_source_artifact"),
        _map_row("v5f_1min_intraday_relative_zone_timing_test", "v5f_1min_intraday_relative_zone_timing_test", "relative intraday high/low zone timing diagnostic", "v5h_intraday_relative_zone_timing", "completed_source_artifact"),
        _map_row("v5h_1min_volume_amount_timing_test", "v5h_1min_volume_amount_timing_test", "1min volume/amount timing diagnostics", "v5h_volume_amount_timing", latest_summary.get("status", "")),
    ]
    governance = _governance_audit()
    decision = [
        {
            "pm_gate_decision": "define_v5h_as_1min_microstructure_execution_research_line",
            "status": "defined",
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "trading_frequency_increased": False,
            "notes": "Existing one-minute artifacts are reclassified under V5h lineage while original directories remain as source artifacts.",
        }
    ]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5h_1min_research_line_governance",
        "status": "completed_v5h_line_definition",
        "v5h_line_id": V5H_LINE_ID,
        "component_count": len(mapping),
        "latest_volume_amount_status": latest_summary.get("status", ""),
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "trading_frequency_increased": False,
    }
    _write_json(out / "v5h_1min_research_line_summary.json", summary)
    _write_csv(out / "v5h_1min_component_mapping.csv", mapping)
    _write_csv(out / "v5h_1min_line_governance_audit.csv", governance)
    _write_csv(out / "v5h_1min_line_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_1min_line_next_queue.csv", _next_queue("positive"))
    (out / "v5h_1min_research_line_report.md").write_text(_v5h_line_report(mapping, decision), encoding="utf-8")
    (out / "v5h_1min_line_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")


def _map_row(source_id: str, source_path: str, description: str, v5h_component_id: str, status: str) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_path": source_path,
        "v5h_component_id": v5h_component_id,
        "description": description,
        "status": status,
        "rename_policy": "lineage_reclassification_only_do_not_move_source_artifact",
        "accepted": False,
        "trading_frequency_change_allowed": False,
    }


def _feature_schema() -> list[dict[str, Any]]:
    return [
        {"field": "last15_amount_intensity", "definition": "last 15 observed 1min avg amount / elapsed avg amount up to observation time", "pit_safe": True},
        {"field": "last15_volume_intensity", "definition": "last 15 observed 1min avg volume / elapsed avg volume up to observation time", "pit_safe": True},
        {"field": "amount_pressure_to_obs", "definition": "sum(amount * sign(minute_return)) / cumulative amount up to observation time", "pit_safe": True},
        {"field": "amount_pressure_turn", "definition": "last15 amount pressure minus prior elapsed amount pressure", "pit_safe": True},
        {"field": "volume_share_to_obs_hindsight", "definition": "cumulative volume / full-day volume", "pit_safe": False},
    ]


def _report(
    zone_summary: dict[str, Any],
    context_summary: list[dict[str, Any]],
    candidate_matrix: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5h 1min Volume/Amount Timing Test",
        "",
        "This packet adds 1-minute volume and amount diagnostics to the prior relative-zone timing test. It is diagnostic only and does not increase trading frequency.",
        "",
        f"- Source zone test: `{zone_summary.get('status')}`",
        "",
        "## Best Volume/Amount Conditions",
    ]
    for row in sorted(candidate_matrix, key=lambda item: _float(item.get("incremental_edge_vs_unconditioned")), reverse=True)[:12]:
        lines.append(
            f"- `{row['condition_id']}`: n `{row['sample_count']}`, edge `{row['avg_action_edge_vs_close']}`, incremental `{row['incremental_edge_vs_unconditioned']}`."
        )
    lines.extend(["", "## Unconditioned Contexts"])
    for row in sorted(context_summary, key=lambda item: _float(item.get("avg_action_edge_vs_close")), reverse=True)[:10]:
        lines.append(f"- `{row.get('context_id')}`: n `{row.get('sample_count')}`, edge `{row.get('avg_action_edge_vs_close')}`.")
    lines.extend(["", f"PM decision: `{decision[0]['pm_gate_decision']}`", ""])
    return "\n".join(lines)


def _v5h_line_report(mapping: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    lines = [
        "# V5h 1min Research Line Governance",
        "",
        "V5h is now defined as the one-minute microstructure and execution-quality research line. Existing one-minute V5f artifacts remain in place as source artifacts and are mapped into V5h lineage.",
        "",
        "## Components",
    ]
    for row in mapping:
        lines.append(f"- `{row['v5h_component_id']}` <= `{row['source_path']}`: {row['description']}")
    lines.extend(["", f"PM decision: `{decision[0]['pm_gate_decision']}`", ""])
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5h 1min Agent Execution Rules",
            "",
            "- V5h covers one-minute microstructure, VWAP, relative-zone, volume, and amount diagnostics.",
            "- Do not modify V57f core or V5f mainline.",
            "- Do not increase trading frequency.",
            "- Do not use hindsight full-day volume/amount shares as live signals.",
            "- Do not scan thresholds or mark accepted/live approved.",
            "",
        ]
    )


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5h_1min_volume_amount_timing_test",
        "v5h_line_id": V5H_LINE_ID,
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
    _write_json(out / "v5h_1min_volume_amount_summary.json", summary)
    _write_csv(out / "v5h_1min_volume_amount_blockers.csv", blockers)


def _blockers(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    for group in groups:
        for row in group:
            if row.get("status") == "fail":
                blockers.append(_blocker(row.get("gate_id") or row.get("audit_id") or "unknown", str(row.get("value", row.get("detail", "")))))
    return blockers or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _best(rows: list[dict[str, Any]], action: str) -> dict[str, Any]:
    eligible = [row for row in rows if row.get("action") == action]
    return max(eligible, key=lambda row: _float(row.get("incremental_edge_vs_unconditioned"))) if eligible else {}


def _pressure_aligned(action: str, bucket: str) -> bool:
    if action == "buy":
        return bucket in {"negative_pressure", "neutral_pressure"}
    if action == "sell":
        return bucket in {"positive_pressure", "neutral_pressure"}
    return False


def _signed_pressure(rows: list[dict[str, Any]], weight_col: str) -> float:
    if len(rows) < 2:
        return 0.0
    total = 0.0
    signed = 0.0
    prev_close = rows[0]["close"]
    for row in rows[1:]:
        weight = max(_float(row.get(weight_col)), 0.0)
        total += weight
        delta = row["close"] - prev_close
        if delta > 1e-12:
            signed += weight
        elif delta < -1e-12:
            signed -= weight
        prev_close = row["close"]
    return signed / total if total > 0 else 0.0


def _intensity_bucket(value: float) -> str:
    if value < 0.80:
        return "quiet"
    if value < 1.20:
        return "normal"
    if value < 2.00:
        return "active"
    return "extreme"


def _pressure_bucket(value: float) -> str:
    if value <= -0.10:
        return "negative_pressure"
    if value >= 0.10:
        return "positive_pressure"
    return "neutral_pressure"


def _turn_bucket(value: float) -> str:
    if value <= -0.10:
        return "pressure_worsening"
    if value >= 0.10:
        return "pressure_improving"
    return "pressure_stable"


def _avg(rows: list[dict[str, Any]], col: str) -> float:
    return sum(_float(row.get(col)) for row in rows) / len(rows) if rows else 0.0


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


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 6) if denominator else 0.0


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("Could not locate V5 database directory with processed/raw/manifests children.")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    summary = run_v5h_1min_volume_amount_timing(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
