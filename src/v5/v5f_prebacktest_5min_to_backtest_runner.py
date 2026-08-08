from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_prebacktest_5min_to_backtest") / "current"
DATASET_ID = "local_5min_2013_2026"
CALIBRATION_START = "2013-01-01"
REQUESTED_PREBACKTEST_START = "2013-01-01"
THRESHOLD_CALIBRATION_END = "2017-12-31"
VALIDATION_START = "2013-01-01"
VALIDATION_END = "2021-04-30"
FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003
BORROW_INTENSITY = 0.10
CAPS = [0.02, 0.05, 0.10]
HORIZONS = ["next1", "next2"]
POLICIES = ["paired_drop_spike_net0", "pro_rata_non_drop"]
MIN_TRAIN_ROWS = 80

PRE2021_CANDIDATES = (
    Path("v5f_pre2021_repaired_multisleeve_data_gate")
    / "current"
    / "v5f_pre2021_candidate_signal_preview.csv"
)
PRE2021_DATA_GATE_DIR = Path("v5f_pre2021_repaired_multisleeve_data_gate") / "current"
CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"
REQUIRED_PREBACKTEST_FIELDS = ["low_vol_score", "volatility_120d", "dividend_yield"]
PRE2021_REPAIRED_STRICT_PANELS = {
    "highway_infrastructure": Path("processed")
    / "pre2021_repaired_factor_panels_v5"
    / "highway_v54h"
    / "strict_pit_panel_with_low_vol.csv",
    "port_rail_infrastructure": Path("processed")
    / "pre2021_repaired_factor_panels_v5"
    / "port_rail_v55j"
    / "strict_pit_panel_with_low_vol.csv",
}
BACKTEST_FEATURES = (
    Path("v5f_short_window_reversion_diagnostic")
    / "current"
    / "v5f_short_window_reversion_minute_day_features.csv"
)
MR_BORROWING_SUMMARY = (
    Path("v5f_event_triggered_mean_reversion_borrowing_test")
    / "current"
    / "v5f_mr_borrowing_summary.json"
)
VMR_SUMMARY = (
    Path("v5f_value_momentum_reversion_balance_test")
    / "current"
    / "v5f_vmr_balance_summary.json"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_prebacktest_5min_to_backtest(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_prebacktest_5min_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_input", blockers)
        _write_json(out / "v5f_prebacktest_5min_to_backtest_summary.json", summary)
        return summary

    db = _find_v5_database(root)
    manifest = _read_json(db / "manifests" / DATASET_ID / "collection_manifest.json")
    candidates, candidate_source_rows = _load_prebacktest_candidates(root)
    candidate_features = _candidate_daily_features(root, db, candidates)
    cycles = _cycles(candidates)
    candidate_date_stats = _candidate_date_stats(candidates, candidate_source_rows)
    validation_features = _validation_features(candidate_features, candidates, cycles)
    validation_thresholds = _thresholds_from_features(
        candidate_features,
        candidates,
        train_end=THRESHOLD_CALIBRATION_END,
        threshold_id_prefix="validation_fixed_2013_2017",
    )
    validation_trades = _trade_log(validation_features, validation_thresholds, "prebacktest_validation")
    validation_metrics = _metrics(validation_trades, "prebacktest_validation")
    selected = _select_variant(validation_metrics)

    backtest_features = _load_backtest_features(root)
    backtest_thresholds = _thresholds_from_features(
        candidate_features,
        candidates,
        train_end=VALIDATION_END,
        threshold_id_prefix="formal_backtest_fixed_2013_202104",
    )
    backtest_trades_all = _trade_log(backtest_features, backtest_thresholds, "formal_backtest")
    backtest_metrics_all = _metrics(backtest_trades_all, "formal_backtest")
    backtest_selected = _filter_selected_metrics(backtest_metrics_all, selected)

    before_after = _before_after(root, validation_metrics, backtest_metrics_all, backtest_selected, selected)
    governance = _governance_audit(
        manifest,
        validation_features,
        backtest_features,
        validation_thresholds,
        backtest_thresholds,
        candidate_date_stats,
    )
    decision = _pm_decision(validation_metrics, backtest_selected, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance, decision)

    _write_csv(out / "v5f_prebacktest_full_candidate_calendar.csv", candidates.to_dict("records"))
    _write_csv(out / "v5f_prebacktest_candidate_source_audit.csv", candidate_source_rows)
    _write_csv(
        out / "v5f_prebacktest_5min_source_audit.csv",
        _source_audit(manifest, candidates, candidate_features, backtest_features, candidate_date_stats),
    )
    _write_csv(out / "v5f_prebacktest_candidate_cycles.csv", cycles)
    _write_csv(out / "v5f_prebacktest_validation_feature_panel.csv", validation_features)
    _write_csv(out / "v5f_prebacktest_validation_thresholds.csv", validation_thresholds)
    _write_csv(out / "v5f_prebacktest_validation_borrowing_trade_log.csv", validation_trades)
    _write_csv(out / "v5f_prebacktest_validation_borrowing_metrics.csv", validation_metrics)
    _write_csv(out / "v5f_prebacktest_selected_variant.csv", [selected] if selected else [])
    _write_csv(out / "v5f_formal_backtest_fixed_thresholds.csv", backtest_thresholds)
    _write_csv(out / "v5f_formal_backtest_fixed_borrowing_trade_log.csv", backtest_trades_all)
    _write_csv(out / "v5f_formal_backtest_fixed_borrowing_metrics.csv", backtest_metrics_all)
    _write_csv(out / "v5f_formal_backtest_selected_variant_result.csv", backtest_selected)
    _write_csv(out / "v5f_prebacktest_to_backtest_before_after.csv", before_after)
    _write_csv(out / "v5f_prebacktest_5min_governance_audit.csv", governance)
    _write_csv(out / "v5f_prebacktest_5min_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_prebacktest_5min_next_queue.csv", next_queue)
    _write_csv(out / "v5f_prebacktest_5min_blockers.csv", blockers_out)
    (out / "v5f_prebacktest_5min_to_backtest_report.md").write_text(
        _report(
            manifest,
            validation_metrics,
            selected,
            backtest_selected,
            backtest_metrics_all,
            before_after,
            decision,
            candidate_date_stats,
        ),
        encoding="utf-8",
    )
    (out / "v5f_prebacktest_5min_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best_validation = validation_metrics[0] if validation_metrics else {}
    selected_backtest = backtest_selected[0] if backtest_selected else {}
    best_backtest = backtest_metrics_all[0] if backtest_metrics_all else {}
    summary = _summary(
        "completed_prebacktest_5min_validation_then_formal_backtest",
        decision[0]["pm_gate_decision"],
        [],
        local_5min_dataset_status=manifest.get("status", ""),
        local_5min_total_rows=manifest.get("total_5min_rows", 0),
        calibration_start=CALIBRATION_START,
        requested_prebacktest_start=REQUESTED_PREBACKTEST_START,
        threshold_calibration_end=THRESHOLD_CALIBRATION_END,
        validation_start=VALIDATION_START,
        validation_end=VALIDATION_END,
        available_pit_candidate_start=candidate_date_stats.get("available_pit_candidate_start", ""),
        available_pit_candidate_end=candidate_date_stats.get("available_pit_candidate_end", ""),
        prebacktest_candidate_date_count=candidate_date_stats.get("candidate_date_count", 0),
        prebacktest_candidate_source=candidate_date_stats.get("candidate_source", ""),
        formal_backtest_start=FORMAL_BACKTEST_START,
        formal_backtest_end=FORMAL_BACKTEST_END,
        candidate_feature_rows=len(candidate_features),
        validation_feature_rows=len(validation_features),
        backtest_feature_rows=len(backtest_features),
        validation_best_variant=best_validation.get("version_id", ""),
        validation_best_net_pct_points=float(best_validation.get("net_incremental_return_pct_points", 0.0) or 0.0),
        validation_best_win_rate=float(best_validation.get("win_rate", 0.0) or 0.0),
        selected_variant=selected.get("version_id", "") if selected else "",
        selected_backtest_net_pct_points=float(selected_backtest.get("net_incremental_return_pct_points", 0.0) or 0.0),
        selected_backtest_win_rate=float(selected_backtest.get("win_rate", 0.0) or 0.0),
        best_backtest_variant=best_backtest.get("version_id", ""),
        best_backtest_net_pct_points=float(best_backtest.get("net_incremental_return_pct_points", 0.0) or 0.0),
        independent_validation_pass=decision[0]["independent_validation_pass"],
        accepted=False,
        live_trading_approved=False,
        v57f_core_modified=False,
        threshold_scan_used=False,
        full_market_selection_used=False,
    )
    _write_json(out / "v5f_prebacktest_5min_to_backtest_summary.json", summary)
    return summary


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("V5 database directory not found.")


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in [PRE2021_CANDIDATES, BACKTEST_FEATURES, MR_BORROWING_SUMMARY, VMR_SUMMARY]:
        if not (root / path).exists():
            rows.append({"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "detail": str(path)})
    try:
        db = _find_v5_database(root)
        for path in [
            db / "processed" / DATASET_ID / "v5_required_5min_universe.csv",
            db / "manifests" / DATASET_ID / "collection_manifest.json",
        ]:
            if not path.exists():
                rows.append({"blocker_id": "missing_local_5min_dataset", "severity": "fatal", "status": "blocking", "detail": str(path)})
    except Exception as exc:
        rows.append({"blocker_id": "missing_v5_database", "severity": "fatal", "status": "blocking", "detail": str(exc)})
    return rows


def _load_prebacktest_candidates(root: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    full_rows, audit_rows = _full_candidate_calendar(root)
    if full_rows:
        frame = pd.DataFrame(full_rows)
        frame = frame.sort_values(["preview_date", "selected_rank", "code"]).reset_index(drop=True)
        audit_rows.append(
            {
                "audit_id": "candidate_source_selected",
                "status": "pass",
                "candidate_source": "full_common_pit_calendar",
                "candidate_rows": len(frame),
                "candidate_dates": frame["preview_date"].nunique(),
                "detail": "Generated from all common PIT-clean prebacktest candidate dates, not the old first/last preview sample.",
            }
        )
        return frame, audit_rows

    fallback = pd.read_csv(root / PRE2021_CANDIDATES, dtype=str)
    audit_rows.append(
        {
            "audit_id": "candidate_source_selected",
            "status": "fallback",
            "candidate_source": "legacy_preview_first_last_only",
            "candidate_rows": len(fallback),
            "candidate_dates": fallback["preview_date"].nunique() if "preview_date" in fallback.columns else 0,
            "detail": "Full calendar generation unavailable; fell back to the historical preview file.",
        }
    )
    return fallback, audit_rows


def _full_candidate_calendar(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    audit_rows: list[dict[str, Any]] = []
    config_path = root / CONFIG
    if not config_path.exists():
        return [], [
            {
                "audit_id": "full_calendar_config",
                "status": "missing",
                "candidate_source": "full_common_pit_calendar",
                "detail": str(CONFIG),
            }
        ]
    try:
        config = _read_json(config_path)
        sectors = _resolved_prebacktest_sectors(root, config)
    except Exception as exc:
        return [], [
            {
                "audit_id": "full_calendar_sector_resolution",
                "status": "error",
                "candidate_source": "full_common_pit_calendar",
                "detail": f"{type(exc).__name__}: {exc}",
            }
        ]
    if not sectors:
        return [], [
            {
                "audit_id": "full_calendar_sector_resolution",
                "status": "empty",
                "candidate_source": "full_common_pit_calendar",
                "detail": "No sectors resolved from repaired config.",
            }
        ]

    panels: dict[str, pd.DataFrame] = {}
    date_sets: dict[str, set[str]] = {}
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        panel_path = Path(sector["panel_path"])
        if not panel_path.exists():
            audit_rows.append(
                {
                    "audit_id": "full_calendar_panel",
                    "status": "missing",
                    "sector_id": sector_id,
                    "candidate_source": "full_common_pit_calendar",
                    "detail": str(panel_path),
                }
            )
            continue
        df = pd.read_csv(panel_path, dtype=str)
        date_col = _date_column(df.columns.astype(str).tolist())
        df[date_col] = df[date_col].astype(str).str.slice(0, 10)
        panels[sector_id] = df
        date_sets[sector_id] = _candidate_dates_from_frame(df, date_col)
        audit_rows.append(
            {
                "audit_id": "full_calendar_panel",
                "status": "pass" if date_sets[sector_id] else "no_candidate_dates",
                "sector_id": sector_id,
                "candidate_source": str(sector.get("panel_source_scope") or ""),
                "candidate_dates": len(date_sets[sector_id]),
                "first_candidate_date": min(date_sets[sector_id]) if date_sets[sector_id] else "",
                "last_candidate_date": max(date_sets[sector_id]) if date_sets[sector_id] else "",
                "detail": str(panel_path),
            }
        )

    if set(date_sets) != {str(sector.get("sector_id") or "") for sector in sectors}:
        return [], audit_rows
    common_dates = sorted(set.intersection(*date_sets.values())) if date_sets else []
    if not common_dates:
        audit_rows.append(
            {
                "audit_id": "full_calendar_common_dates",
                "status": "empty",
                "candidate_source": "full_common_pit_calendar",
                "candidate_dates": 0,
                "detail": "No common PIT-clean candidate date across all repaired V57f sleeves.",
            }
        )
        return [], audit_rows

    raw_spec = {"signals": config.get("signals", {})}
    target_count = int(config.get("portfolio", {}).get("target_count") or 28)
    rows: list[dict[str, Any]] = []
    for day in common_dates:
        day_rows: list[dict[str, Any]] = []
        for sector in sectors:
            sector_id = str(sector.get("sector_id") or "")
            df = panels[sector_id]
            date_col = _date_column(df.columns.astype(str).tolist())
            for record in df[df[date_col].eq(day)].to_dict("records"):
                enriched = _enrich_basket_panel_row(record, sector_id)
                enriched["sector_id"] = sector_id
                enriched["source_strategy_id"] = str(sector.get("strategy_id") or "")
                day_rows.append(enriched)
        scored, used_factors = _score_sector_adaptive(raw_spec, day_rows)
        scored.sort(key=lambda item: _safe_float(item.get("score")) or -999999.0, reverse=True)
        for rank, item in enumerate(scored[:target_count], start=1):
            rows.append(
                {
                    "preview_date": day,
                    "code": item.get("code", ""),
                    "sector_id": item.get("sector_id", ""),
                    "selected_rank": rank,
                    "score": _fmt_float(item.get("score")),
                    "used_factors": ";".join(used_factors),
                    "preview_status": "complete_multisleeve_full_calendar",
                    "candidate_source": "full_common_pit_calendar",
                    "governance_note": "Generated from PIT-clean prebacktest panels; not accepted and not live approved.",
                }
            )
    audit_rows.append(
        {
            "audit_id": "full_calendar_common_dates",
            "status": "pass",
            "candidate_source": "full_common_pit_calendar",
            "candidate_dates": len(common_dates),
            "first_candidate_date": common_dates[0],
            "last_candidate_date": common_dates[-1],
            "detail": "Used every common candidate date available before the formal backtest window.",
        }
    )
    return rows, audit_rows


def _resolved_prebacktest_sectors(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    sectors: list[dict[str, Any]] = []
    for sector in config.get("sectors", []):
        item = dict(sector)
        sector_id = str(item.get("sector_id") or "")
        repaired = _resolve_pre2021_repaired_panel_path(root, sector_id)
        if repaired:
            item["panel_path"] = repaired
            item["panel_source_scope"] = "pre2021_repaired_strict_pit_panel"
        else:
            item["panel_path"] = _resolve_workspace_path(root, str(item.get("panel_csv") or ""))
            item["panel_source_scope"] = "startup_repaired_shadow_panel"
        sectors.append(item)
    return sectors


def _database_roots(root: Path) -> list[Path]:
    candidates = [child for child in root.iterdir() if child.is_dir() and (child / "processed").is_dir()]
    return sorted(candidates, key=lambda path: 0 if (path / "processed" / "startup_preload_repaired_panels_v5").exists() else 1)


def _resolve_workspace_path(root: Path, raw: str) -> Path:
    direct = root / raw
    if direct.exists():
        return direct
    normalized = raw.replace("\\", "/")
    marker = "processed/"
    if marker in normalized:
        suffix = normalized.split(marker, 1)[1]
        for db_root in _database_roots(root):
            candidate = db_root / "processed" / Path(suffix)
            if candidate.exists():
                return candidate
        roots = _database_roots(root)
        if roots:
            return roots[0] / "processed" / Path(suffix)
    return direct


def _resolve_pre2021_repaired_panel_path(root: Path, sector_id: str) -> Path | None:
    suffix = PRE2021_REPAIRED_STRICT_PANELS.get(sector_id)
    if not suffix:
        return None
    for db_root in _database_roots(root):
        candidate = db_root / suffix
        if candidate.exists():
            return candidate
    return None


def _date_column(columns: list[str]) -> str:
    if "trade_date" in columns:
        return "trade_date"
    if "date" in columns:
        return "date"
    return columns[0] if columns else "trade_date"


def _candidate_dates_from_frame(df: pd.DataFrame, date_col: str) -> set[str]:
    dates = df[date_col].astype(str).str.slice(0, 10)
    mask = (dates >= REQUESTED_PREBACKTEST_START) & (dates <= VALIDATION_END)
    for field in REQUIRED_PREBACKTEST_FIELDS:
        if field not in df.columns:
            return set()
        mask &= _nonempty(df[field])
    return set(dates[mask].tolist())


def _nonempty(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("") & ~series.astype(str).str.strip().isin({"nan", "NaN", "None"})


def _enrich_basket_panel_row(row: dict[str, Any], sector_id: str) -> dict[str, Any]:
    enriched = dict(row)
    dividend = _normalized_yield(enriched.get("dividend_yield"))
    if dividend is not None:
        enriched["dividend_yield_decimal"] = dividend
    ocf_yield = _safe_float(enriched.get("operating_cash_flow_yield"))
    if ocf_yield is not None:
        enriched["cash_generation_yield"] = ocf_yield
    elif sector_id in {"bank", "insurance"} and dividend is not None:
        enriched["cash_generation_yield"] = dividend
    return enriched


def _normalized_yield(value: Any) -> float | None:
    raw = _safe_float(value)
    if raw is None or raw < 0:
        return None
    return raw / 100.0 if raw > 1.0 else raw


def _score_sector_adaptive(raw_spec: dict[str, Any], date_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    used: list[str] = []
    by_sector: dict[str, list[dict[str, Any]]] = {}
    for row in date_rows:
        by_sector.setdefault(str(row.get("sector_id") or ""), []).append(row)
    for sector_id, sector_rows in sorted(by_sector.items()):
        scored, sector_used = _score_weighted_composite(_sector_scoring_spec(raw_spec, sector_id), sector_rows)
        rows.extend(scored)
        for factor in sector_used:
            if factor not in used:
                used.append(factor)
    return rows, used


def _sector_scoring_spec(raw_spec: dict[str, Any], sector_id: str) -> dict[str, Any]:
    base_signals = raw_spec.get("signals", {})
    base_scoring = base_signals.get("scoring", {})
    overrides = base_scoring.get("sector_scoring_overrides", {})
    override = overrides.get(sector_id) or overrides.get("_default") or {}
    scoring = {key: value for key, value in base_scoring.items() if key not in {"sector_scoring_overrides", "default_scoring"}}
    for key, value in override.items():
        if key != "factors":
            scoring[key] = value
    return {"signals": {"factors": override.get("factors") or base_signals.get("factors", []), "scoring": scoring}}


def _score_weighted_composite(raw_spec: dict[str, Any], date_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    factors = raw_spec.get("signals", {}).get("factors", [])
    scoring = raw_spec.get("signals", {}).get("scoring", {})
    weights = scoring.get("weights", {})
    min_factor_count = int(scoring.get("min_factor_count", 1) or 1)
    factor_scores: dict[str, dict[str, float]] = {}
    used_factors: list[str] = []
    for factor in factors:
        name = str(factor.get("name") or "")
        keyed: list[tuple[str, float]] = []
        values: list[float] = []
        for row in date_rows:
            raw_value = _factor_value(row, name)
            if raw_value is None:
                continue
            value = -raw_value if factor.get("direction") == "lower_is_better" else raw_value
            keyed.append((str(row.get("code") or ""), value))
            values.append(value)
        zscores = _zscores(_winsorized(values))
        if len(zscores) >= 3:
            used_factors.append(name)
            factor_scores[name] = {code: zscores[index] for index, (code, _value) in enumerate(keyed)}
        else:
            factor_scores[name] = {}

    scored: list[dict[str, Any]] = []
    for row in date_rows:
        score = 0.0
        used_weight = 0.0
        factor_count = 0
        for factor in factors:
            name = str(factor.get("name") or "")
            value = factor_scores.get(name, {}).get(str(row.get("code") or ""))
            if value is None:
                continue
            weight = float(weights.get(name, 1.0))
            score += weight * value
            used_weight += abs(weight)
            factor_count += 1
        if used_weight <= 0 or factor_count < min_factor_count:
            continue
        enriched = dict(row)
        enriched["score"] = score / used_weight
        enriched["factor_count"] = factor_count
        scored.append(enriched)
    return scored, used_factors


def _factor_value(row: dict[str, Any], name: str) -> float | None:
    value = _safe_float(row.get(name))
    if value is not None:
        return value
    aliases = {
        "roe_quality": ["return_on_equity_ttm", "roe"],
        "capital_resilience": ["core_tier_1_capital_adequacy_ratio"],
        "provision_buffer": ["provision_coverage_ratio"],
    }
    for alias in aliases.get(name, []):
        value = _safe_float(row.get(alias))
        if value is not None:
            return value
    return None


def _zscores(values: list[float]) -> list[float]:
    if len(values) < 3:
        return []
    avg = sum(values) / len(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    std = variance**0.5
    if std == 0:
        return []
    return [(value - avg) / std for value in values]


def _winsorized(values: list[float], lower: float = 0.05, upper: float = 0.95) -> list[float]:
    if len(values) < 5:
        return values
    sorted_values = sorted(values)
    low = _quantile(sorted_values, lower)
    high = _quantile(sorted_values, upper)
    return [min(max(value, low), high) for value in values]


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    pos = (len(sorted_values) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = pos - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _fmt_float(value: Any) -> str:
    numeric = _safe_float(value)
    return "" if numeric is None else f"{numeric:.10g}"


def _candidate_date_stats(candidates: pd.DataFrame, source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted(candidates["preview_date"].dropna().astype(str).unique().tolist()) if "preview_date" in candidates else []
    selected_source = next((row for row in reversed(source_rows) if row.get("audit_id") == "candidate_source_selected"), {})
    return {
        "candidate_source": selected_source.get("candidate_source", ""),
        "candidate_date_count": len(dates),
        "available_pit_candidate_start": dates[0] if dates else "",
        "available_pit_candidate_end": dates[-1] if dates else "",
        "requested_prebacktest_start": REQUESTED_PREBACKTEST_START,
        "validation_end": VALIDATION_END,
        "full_calendar_used": selected_source.get("candidate_source") == "full_common_pit_calendar",
    }


def _candidate_daily_features(root: Path, db: Path, candidates: pd.DataFrame) -> list[dict[str, Any]]:
    processed = db / "processed" / DATASET_ID
    source = "full_calendar" if "candidate_source" in candidates.columns and candidates["candidate_source"].astype(str).eq("full_common_pit_calendar").any() else "candidate_preview"
    cache_path = processed / f"v5_required_5min_daily_feature_cache_2013_202104_{source}_codes.csv"
    if cache_path.exists():
        return pd.read_csv(cache_path, dtype={"trade_date": str, "code": str}).to_dict("records")
    rows: list[dict[str, Any]] = []
    codes = sorted(candidates["code"].dropna().astype(str).unique().tolist())
    for code in codes:
        file_code = code.replace(".", "_")
        for year in range(2013, 2022):
            path = processed / "by_year" / str(year) / f"{file_code}_5min.csv"
            if not path.exists():
                continue
            df = pd.read_csv(
                path,
                usecols=["code", "trade_date", "time", "open", "high", "low", "close", "volume", "amount"],
                dtype={"code": str, "trade_date": str, "time": str},
            )
            df = df[(df["trade_date"] >= CALIBRATION_START) & (df["trade_date"] <= VALIDATION_END)].copy()
            rows.extend(_day_feature_rows(df, year))
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["code", "trade_date"]).reset_index(drop=True)
    out.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return out.to_dict("records")


def _day_feature_rows(df: pd.DataFrame, year: int) -> list[dict[str, Any]]:
    if df.empty:
        return []
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    rows = []
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
                "close_0935": close_0935,
                "close_1000": close_1000,
                "close_1030": close_1030,
                "close_1455": close_1455,
                "day_close": _safe_float(group.iloc[-1]["close"]),
                "vwap_1455": vwap,
                "r_0935_1000": _ret(close_1000, close_0935),
                "r_0935_1030": _ret(close_1030, close_0935),
                "r_1000_1455": _ret(close_1455, close_1000),
                "r_1455_vwap": _ret(close_1455, vwap),
                "source": DATASET_ID,
            }
        )
    return rows


def _cycles(candidates: pd.DataFrame) -> list[dict[str, Any]]:
    dates = sorted(candidates["preview_date"].dropna().astype(str).unique().tolist())
    rows = []
    for index, start in enumerate(dates):
        next_date = dates[index + 1] if index + 1 < len(dates) else ""
        end = VALIDATION_END if not next_date else (pd.Timestamp(next_date) - pd.Timedelta(days=1)).date().isoformat()
        rows.append(
            {
                "preview_date": start,
                "cycle_start": start,
                "cycle_end": end,
                "next_preview_date": next_date,
                "candidate_count": int((candidates["preview_date"].astype(str) == start).sum()),
                "classification": "prebacktest_validation_candidate_preview_not_full_v57f_rebalance",
            }
        )
    return rows


def _validation_features(
    daily_rows: list[dict[str, Any]],
    candidates: pd.DataFrame,
    cycles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    daily = pd.DataFrame(daily_rows)
    if daily.empty:
        return []
    rows = []
    for cycle in cycles:
        selected = candidates[candidates["preview_date"].astype(str).eq(str(cycle["preview_date"]))].copy()
        selected_codes = set(selected["code"].astype(str))
        meta = selected.set_index("code").to_dict("index")
        df = daily[
            daily["code"].astype(str).isin(selected_codes)
            & (daily["trade_date"].astype(str) >= str(cycle["cycle_start"]))
            & (daily["trade_date"].astype(str) <= str(cycle["cycle_end"]))
        ].copy()
        target_weight = 1.0 / len(selected) if len(selected) else 0.0
        for code, group in df.sort_values(["code", "trade_date"]).groupby("code", sort=True):
            group = group.reset_index(drop=True)
            group["next_day_close"] = group["day_close"].shift(-1)
            group["next_2d_close"] = group["day_close"].shift(-2)
            for _, row in group.iterrows():
                item = row.to_dict()
                item.update(
                    {
                        "preview_date": cycle["preview_date"],
                        "sleeve": meta[str(code)].get("sector_id", ""),
                        "target_weight": target_weight,
                        "next1_from_1000": _ret(row.get("next_day_close"), row.get("close_1000")),
                        "next2_from_1000": _ret(row.get("next_2d_close"), row.get("close_1000")),
                        "sample_role": "prebacktest_validation",
                    }
                )
                rows.append(item)
    return rows


def _thresholds_from_features(
    daily_rows: list[dict[str, Any]],
    candidates: pd.DataFrame,
    *,
    train_end: str,
    threshold_id_prefix: str,
) -> list[dict[str, Any]]:
    daily = pd.DataFrame(daily_rows)
    if daily.empty:
        return []
    code_sleeve = (
        candidates[["code", "sector_id"]]
        .drop_duplicates()
        .rename(columns={"sector_id": "sleeve"})
    )
    expanded = daily.merge(code_sleeve, on="code", how="inner")
    expanded = expanded[(expanded["trade_date"].astype(str) >= CALIBRATION_START) & (expanded["trade_date"].astype(str) <= train_end)].copy()
    rows = []
    for sleeve, group in expanded.groupby("sleeve", sort=True):
        series = pd.to_numeric(group["r_0935_1000"], errors="coerce").dropna()
        status = "pass" if len(series) >= MIN_TRAIN_ROWS else "insufficient_train_rows"
        rows.append(
            {
                "threshold_id": f"{threshold_id_prefix}|candidate_union|{sleeve}",
                "threshold_set": threshold_id_prefix,
                "sleeve": sleeve,
                "train_start": CALIBRATION_START,
                "train_end": train_end,
                "train_row_count": int(len(series)),
                "drop_cut_r_0935_1000": float(series.quantile(0.10)) if status == "pass" else "",
                "spike_cut_r_0935_1000": float(series.quantile(0.90)) if status == "pass" else "",
                "threshold_source": "candidate_union_same_sleeve_fixed_prebacktest",
                "used_backtest_return_data": False,
                "status": status,
            }
        )
    return rows


def _load_backtest_features(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / BACKTEST_FEATURES, dtype={"trade_date": str, "code": str})
    df = df[(df["trade_date"] >= FORMAL_BACKTEST_START) & (df["trade_date"] <= FORMAL_BACKTEST_END)].copy()
    needed = ["r_0935_1000", "next1_from_1000", "next2_from_1000", "target_weight"]
    for col in needed:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["sample_role"] = "formal_backtest"
    return df.to_dict("records")


def _trade_log(features: list[dict[str, Any]], thresholds: list[dict[str, Any]], sample_role: str) -> list[dict[str, Any]]:
    if not features or not thresholds:
        return []
    df = pd.DataFrame(features)
    threshold_df = pd.DataFrame([row for row in thresholds if row.get("status") == "pass"])
    df = df.merge(threshold_df[["sleeve", "drop_cut_r_0935_1000", "spike_cut_r_0935_1000", "threshold_id"]], on="sleeve", how="left")
    df = df[df["drop_cut_r_0935_1000"].notna()].copy()
    df["is_drop"] = pd.to_numeric(df["r_0935_1000"], errors="coerce") <= pd.to_numeric(df["drop_cut_r_0935_1000"], errors="coerce")
    df["is_spike"] = pd.to_numeric(df["r_0935_1000"], errors="coerce") >= pd.to_numeric(df["spike_cut_r_0935_1000"], errors="coerce")
    rows = []
    for (trade_date, sleeve), group in df.groupby(["trade_date", "sleeve"], sort=True):
        for horizon in HORIZONS:
            ret_col = f"{horizon}_from_1000"
            day_group = group[group[ret_col].notna()].copy()
            drops = day_group[day_group["is_drop"]].copy()
            if drops.empty:
                continue
            for policy in POLICIES:
                for cap in CAPS:
                    trade = _single_trade(day_group, drops, policy, cap, ret_col)
                    if trade:
                        trade.update(
                            {
                                "version_id": f"{sample_role}|{policy}|cap{int(cap*100)}|{horizon}",
                                "sample_role": sample_role,
                                "trade_date": trade_date,
                                "sleeve": sleeve,
                                "funding_policy": policy,
                                "borrow_cap_pct_of_sleeve": cap,
                                "horizon": horizon,
                            }
                        )
                        rows.append(trade)
    return rows


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
    target_ret = _weighted_return(drops, ret_col)
    source_ret = _weighted_return(sources, ret_col)
    if actual <= 0 or target_ret is None or source_ret is None:
        return None
    gross = actual * (target_ret - source_ret)
    commission = actual * COMMISSION_RATE * 2.0
    net = gross - commission
    return {
        "drop_count": int(len(drops)),
        "source_count": int(len(sources)),
        "actual_borrow_weight": actual,
        "target_avg_return": target_ret,
        "source_avg_return": source_ret,
        "gross_incremental_return": gross,
        "commission_drag": commission,
        "net_incremental_return": net,
        "win": net > 0,
        "same_sleeve_funding": True,
        "new_buy_signal_used": False,
        "accepted": False,
    }


def _metrics(trades: list[dict[str, Any]], sample_role: str) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows = []
    for version, group in df.groupby("version_id", sort=True):
        net = pd.to_numeric(group["net_incremental_return"], errors="coerce").dropna()
        rows.append(
            {
                "version_id": version,
                "sample_role": sample_role,
                "policy_key": "|".join(str(version).split("|")[1:]),
                "funding_policy": group.iloc[0]["funding_policy"],
                "borrow_cap_pct_of_sleeve": group.iloc[0]["borrow_cap_pct_of_sleeve"],
                "horizon": group.iloc[0]["horizon"],
                "trade_group_count": int(len(group)),
                "net_incremental_return": float(net.sum()),
                "net_incremental_return_pct_points": float(net.sum()) * 100,
                "win_rate": float((net > 0).mean()) if len(net) else 0.0,
                "avg_trade_net_incremental_return": float(net.mean()) if len(net) else 0.0,
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda row: (float(row["net_incremental_return_pct_points"]), float(row["win_rate"])), reverse=True)


def _select_variant(validation_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not validation_metrics:
        return {}
    best = validation_metrics[0].copy()
    best["selection_source"] = "prebacktest_validation_full_available_pit_calendar_to_202104"
    best["formal_backtest_return_used_for_selection"] = False
    return best


def _filter_selected_metrics(metrics: list[dict[str, Any]], selected: dict[str, Any]) -> list[dict[str, Any]]:
    if not selected:
        return []
    key = selected.get("policy_key", "")
    return [row for row in metrics if row.get("policy_key") == key]


def _before_after(
    root: Path,
    validation_metrics: list[dict[str, Any]],
    backtest_metrics: list[dict[str, Any]],
    backtest_selected: list[dict[str, Any]],
    selected: dict[str, Any],
) -> list[dict[str, Any]]:
    mr_summary = _read_json(root / MR_BORROWING_SUMMARY)
    vmr_summary = _read_json(root / VMR_SUMMARY)
    validation_best = validation_metrics[0] if validation_metrics else {}
    selected_bt = backtest_selected[0] if backtest_selected else {}
    backtest_best = backtest_metrics[0] if backtest_metrics else {}
    return [
        {
            "comparison_id": "validation_selected_then_formal_backtest",
            "validation_best_variant": validation_best.get("version_id", ""),
            "validation_best_net_pct_points": validation_best.get("net_incremental_return_pct_points", ""),
            "selected_policy_key": selected.get("policy_key", ""),
            "selected_backtest_variant": selected_bt.get("version_id", ""),
            "selected_backtest_net_pct_points": selected_bt.get("net_incremental_return_pct_points", ""),
            "selected_backtest_win_rate": selected_bt.get("win_rate", ""),
            "interpretation": "This is the true prebacktest-selected version applied to formal backtest.",
        },
        {
            "comparison_id": "best_backtest_if_reselected_in_backtest",
            "validation_best_variant": validation_best.get("version_id", ""),
            "validation_best_net_pct_points": validation_best.get("net_incremental_return_pct_points", ""),
            "selected_policy_key": "backtest_reselected_not_allowed_for_promotion",
            "selected_backtest_variant": backtest_best.get("version_id", ""),
            "selected_backtest_net_pct_points": backtest_best.get("net_incremental_return_pct_points", ""),
            "selected_backtest_win_rate": backtest_best.get("win_rate", ""),
            "interpretation": "Diagnostic only; not used for model selection.",
        },
        {
            "comparison_id": "old_backtest_scope_internal_result",
            "validation_best_variant": "",
            "validation_best_net_pct_points": "",
            "selected_policy_key": mr_summary.get("best_variant", ""),
            "selected_backtest_variant": mr_summary.get("best_variant", ""),
            "selected_backtest_net_pct_points": mr_summary.get("best_delta_return_pct_points_vs_champion", ""),
            "selected_backtest_win_rate": "",
            "interpretation": "Old in-backtest engineering result; included only for comparison.",
        },
        {
            "comparison_id": "current_v5f_primary_champion",
            "validation_best_variant": "",
            "validation_best_net_pct_points": "",
            "selected_policy_key": vmr_summary.get("primary_candidate", ""),
            "selected_backtest_variant": vmr_summary.get("primary_candidate", ""),
            "selected_backtest_net_pct_points": 0.0,
            "selected_backtest_win_rate": "",
            "interpretation": "Primary model remains internal_subsleeve_mom12_70_30.",
        },
    ]


def _source_audit(
    manifest: dict[str, Any],
    candidates: pd.DataFrame,
    candidate_features: list[dict[str, Any]],
    backtest_features: list[dict[str, Any]],
    candidate_date_stats: dict[str, Any],
) -> list[dict[str, Any]]:
    years = manifest.get("years_loaded", [])
    return [
        {"audit_id": "local_5min_dataset_completed", "status": "pass" if manifest.get("status") == "completed" else "fail", "detail": manifest.get("status", "")},
        {"audit_id": "prebacktest_years_available", "status": "pass" if all(year in years for year in range(2013, 2022)) else "fail", "detail": ";".join(map(str, years))},
        {"audit_id": "requested_prebacktest_split", "status": "pass", "detail": f"{REQUESTED_PREBACKTEST_START}_to_{VALIDATION_END}; formal={FORMAL_BACKTEST_START}_to_{FORMAL_BACKTEST_END}"},
        {"audit_id": "candidate_source", "status": "pass" if candidate_date_stats.get("full_calendar_used") else "fallback", "detail": candidate_date_stats.get("candidate_source", "")},
        {"audit_id": "available_pit_candidate_dates", "status": "pass" if candidate_date_stats.get("candidate_date_count", 0) else "fail", "detail": f"{candidate_date_stats.get('candidate_date_count')} dates from {candidate_date_stats.get('available_pit_candidate_start')} to {candidate_date_stats.get('available_pit_candidate_end')}"},
        {"audit_id": "candidate_rows", "status": "pass" if len(candidates) else "fail", "detail": int(len(candidates))},
        {"audit_id": "candidate_feature_rows", "status": "pass" if candidate_features else "fail", "detail": len(candidate_features)},
        {"audit_id": "formal_backtest_feature_rows", "status": "pass" if backtest_features else "fail", "detail": len(backtest_features)},
    ]


def _governance_audit(
    manifest: dict[str, Any],
    validation_features: list[dict[str, Any]],
    backtest_features: list[dict[str, Any]],
    validation_thresholds: list[dict[str, Any]],
    backtest_thresholds: list[dict[str, Any]],
    candidate_date_stats: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {"audit_id": "prebacktest_before_formal_backtest", "status": "pass", "detail": f"{VALIDATION_END} < {FORMAL_BACKTEST_START}"},
        {"audit_id": "local_5min_completed", "status": "pass" if manifest.get("status") == "completed" else "fail", "detail": manifest.get("status", "")},
        {"audit_id": "full_candidate_calendar_used", "status": "pass" if candidate_date_stats.get("full_calendar_used") else "fail", "detail": candidate_date_stats.get("candidate_source", "")},
        {"audit_id": "validation_features_available", "status": "pass" if validation_features else "fail", "detail": len(validation_features)},
        {"audit_id": "backtest_features_available", "status": "pass" if backtest_features else "fail", "detail": len(backtest_features)},
        {"audit_id": "thresholds_no_backtest_return_used", "status": "pass" if all(str(row.get("used_backtest_return_data")) == "False" for row in validation_thresholds + backtest_thresholds) else "fail", "detail": ""},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": "candidate union and V57f repaired holdings only"},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": "same-sleeve temporary borrowing only"},
        {"audit_id": "v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted", "status": "pass", "detail": False},
    ]


def _pm_decision(
    validation_metrics: list[dict[str, Any]],
    backtest_selected: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] == "fail"]
    validation_best = validation_metrics[0] if validation_metrics else {}
    selected_bt = backtest_selected[0] if backtest_selected else {}
    validation_net = float(validation_best.get("net_incremental_return_pct_points", 0.0) or 0.0)
    bt_net = float(selected_bt.get("net_incremental_return_pct_points", 0.0) or 0.0)
    if failed:
        decision = "blocked_by_data_or_pit_issue"
        verdict = "blocked"
    elif validation_net > 0 and bt_net > 0:
        decision = "prebacktest_validated_backtest_positive_keep_diagnostic_not_candidate"
        verdict = "positive_but_not_enough_for_candidate"
    else:
        decision = "prebacktest_validation_or_backtest_mixed_keep_diagnostic"
        verdict = "mixed"
    return [
        {
            "pm_gate_decision": decision,
            "independent_validation_pass": False,
            "formal_promotion_allowed": False,
            "validation_best_net_pct_points": validation_net,
            "selected_backtest_net_pct_points": bt_net,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "verdict": verdict,
            "next_step": "keep_internal_subsleeve_mom12_70_30_primary; archive 5min data blocker as resolved; keep borrowing as diagnostic only",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "keep_internal_subsleeve_mom12_70_30_primary", "allowed": True, "reason": "Mainline remains stronger and already passed broader governance."},
        {"priority": 2, "next_task": "archive_pre2020_5min_missing_blockers", "allowed": True, "reason": "2013-2021 prebacktest 5min validation is now complete."},
        {"priority": 3, "next_task": "keep_spike_borrowing_diagnostic_or_forward_observation", "allowed": True, "reason": "Validation/backtest result is small and not candidate-grade."},
        {"priority": 4, "next_task": "promote_spike_borrowing_to_candidate", "allowed": False, "reason": "No accepted/live approval; result remains diagnostic."},
    ]


def _blockers(governance: list[dict[str, Any]], decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]} for row in governance if row["status"] == "fail"]
    if rows:
        return rows
    return [
        {
            "blocker_id": "candidate_promotion_blocked",
            "severity": "governance",
            "status": "blocking_promotion_only",
            "detail": decision[0]["verdict"],
        }
    ]


def _report(
    manifest: dict[str, Any],
    validation_metrics: list[dict[str, Any]],
    selected: dict[str, Any],
    backtest_selected: list[dict[str, Any]],
    backtest_metrics: list[dict[str, Any]],
    before_after: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    candidate_date_stats: dict[str, Any],
) -> str:
    validation_best = validation_metrics[0] if validation_metrics else {}
    selected_bt = backtest_selected[0] if backtest_selected else {}
    backtest_best = backtest_metrics[0] if backtest_metrics else {}
    lines = [
        "# V5f Prebacktest 5min Validation Then Formal Backtest",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Local 5min dataset: `{manifest.get('status')}`, rows `{manifest.get('total_5min_rows')}`.",
        f"- Requested prebacktest window: `{REQUESTED_PREBACKTEST_START}` to `{VALIDATION_END}`.",
        f"- Threshold calibration window: `{CALIBRATION_START}` to `{THRESHOLD_CALIBRATION_END}`.",
        f"- Available PIT candidate window: `{candidate_date_stats.get('available_pit_candidate_start', '')}` to `{candidate_date_stats.get('available_pit_candidate_end', '')}`.",
        f"- Prebacktest candidate dates: `{candidate_date_stats.get('candidate_date_count', 0)}` from `{candidate_date_stats.get('candidate_source', '')}`.",
        f"- Formal backtest window: `{FORMAL_BACKTEST_START}` to `{FORMAL_BACKTEST_END}`.",
        "- Accepted: `False`; V57f core modified: `False`; threshold scan used: `False`.",
        "",
        "## Validation Selection",
        "",
        f"- Best validation variant: `{validation_best.get('version_id', '')}`",
        f"- Validation net: `{float(validation_best.get('net_incremental_return_pct_points', 0.0) or 0.0):.4f}` pct points.",
        f"- Validation win rate: `{float(validation_best.get('win_rate', 0.0) or 0.0):.2%}`.",
        "",
        "## Formal Backtest",
        "",
        f"- Selected variant applied to backtest: `{selected_bt.get('version_id', '')}`",
        f"- Selected backtest net: `{float(selected_bt.get('net_incremental_return_pct_points', 0.0) or 0.0):.4f}` pct points.",
        f"- Selected backtest win rate: `{float(selected_bt.get('win_rate', 0.0) or 0.0):.2%}`.",
        f"- Best backtest if reselected inside backtest: `{backtest_best.get('version_id', '')}` / `{float(backtest_best.get('net_incremental_return_pct_points', 0.0) or 0.0):.4f}` pct points.",
        "",
        "## Comparison",
        "",
    ]
    for row in before_after:
        lines.append(f"- `{row['comparison_id']}`: selected/backtest net `{row['selected_backtest_net_pct_points']}`; {row['interpretation']}")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Prebacktest 5min Rules",
            "",
            "- 2013-01-01 to 2021-04-30 is the prebacktest calibration/validation boundary.",
            "- Use every PIT-clean common candidate date available inside that boundary.",
            "- If the PIT-clean repaired pool starts later than 2013, disclose the available candidate start date.",
            "- 2021-05-01 to 2026-05-31 is formal backtest.",
            "- Select policy/cap/horizon only from prebacktest validation.",
            "- Use fixed same-sleeve candidate-union thresholds for formal backtest.",
            "- No full-market selection, no V57f core modification, no accepted/live approval.",
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


def _weighted_return(df: pd.DataFrame, ret_col: str) -> float | None:
    temp = df[[ret_col, "target_weight"]].copy()
    temp[ret_col] = pd.to_numeric(temp[ret_col], errors="coerce")
    temp["target_weight"] = pd.to_numeric(temp["target_weight"], errors="coerce").fillna(0.0)
    temp = temp[temp[ret_col].notna()]
    if temp.empty:
        return None
    if float(temp["target_weight"].sum()) == 0.0:
        return float(temp[ret_col].mean())
    return float((temp[ret_col] * temp["target_weight"]).sum() / temp["target_weight"].sum())


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
        "task": "v5f_prebacktest_5min_to_backtest",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("severity") == "fatal"]),
        "fatal_blockers": [row for row in blockers if row.get("severity") == "fatal"],
    }
    payload.update(extra)
    return payload


if __name__ == "__main__":
    print(json.dumps(run_v5f_prebacktest_5min_to_backtest(Path(".")), ensure_ascii=False, indent=2))
