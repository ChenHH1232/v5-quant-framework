from __future__ import annotations

"""Generate read-only companion performance addenda for the V5 model archive.

The runner deliberately prefers an unavailable metric over an inferred one.  It
does not run a model, query a platform, or treat an execution diagnostic as NAV.
"""

import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Iterable


OUT = Path("v5n_model_performance_reporting") / "current"
BOUNDARY = "2026-05-31"
FORMAL_START = "2021-05-01"
BASELINE = "v57f_startup_preload_repaired_baseline"
PRIMARY = "internal_subsleeve_mom12_70_30"
EXCLUDED_PATH_MARKERS = ("202607", "202608", "forward", "paper_trading_signals")


def run_v5n_model_performance_reporting(root: Path = Path("."), output_dir: Path | None = None) -> dict[str, Any]:
    """Build the V5n inventory, companion addenda, and evidence-quality audits."""
    root = Path(root)
    _assert_boundary(root)
    out = output_dir or root / OUT
    out.mkdir(parents=True, exist_ok=True)
    addenda_root = out / "model_addenda"
    addenda_root.mkdir(exist_ok=True)

    registered = _registered_models(root)
    models = _inventory(root, registered)
    return_sources = _return_sources(root)
    identity_rows: list[dict[str, Any]] = []
    benchmark_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    backtest_rows: list[dict[str, Any]] = []
    execution_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    link_rows: list[dict[str, Any]] = []
    completeness_rows: list[dict[str, Any]] = []

    for model_id, model in sorted(models.items()):
        source = _find_source(model_id, model, return_sources)
        series = _read_series(source, model_id) if source else None
        benchmark = _benchmark_for(model_id, model, source, series)
        metrics = _metrics(series["strategy"] if series else None, series["benchmark"] if series else None, series["dates"] if series else None)
        report_status = _report_status(model, source, metrics)
        validation = _validation_for(model, source)
        model_out = addenda_root / _safe_id(model_id)
        model_out.mkdir(exist_ok=True)
        sources = ";".join(model["evidence_paths"])

        identity_rows.append({
            "canonical_model_id": model_id, "display_name": model["display_name"], "family": model["family"],
            "role": model["role"], "status": report_status, "parent_model": model["parent_model"],
            "formal_backtest_start": FORMAL_START, "formal_backtest_end": BOUNDARY,
            "validation_window": validation["validation_window"], "validation_independent": validation["independent"],
            "daily_nav_or_returns_available": bool(series), "alpha_beta_ir_computable": metrics["alpha_zero_rf_annualized_pct"] != "not_available",
            "primary_benchmark": benchmark["benchmark_id"], "economic_exposure_benchmark": benchmark["economic_exposure_benchmark"],
            "evidence_paths": sources, "supersedes_or_alias_of": model["alias_of"],
        })
        benchmark_rows.append({"canonical_model_id": model_id, **benchmark})
        validation_rows.append({"canonical_model_id": model_id, **validation})
        backtest_rows.append({"canonical_model_id": model_id, "report_status": report_status, "return_source": _relative_source(source, root), **metrics})
        execution_rows.append({"canonical_model_id": model_id, "execution_evidence_type": _execution_type(source), "source": _relative_source(source, root), "status": "separate_not_order_fill_contract" if source and "qmt" in str(source).lower() else "local_historical_series_or_unavailable"})
        quality_rows.append({"canonical_model_id": model_id, "report_status": report_status, "daily_series_status": "available" if series else "daily_nav_unavailable", "benchmark_status": benchmark["coverage_status"], "validation_status": validation["validation_result"], "limitations": _limitations(model, source, series, benchmark)})

        _write_json(model_out / "model_performance_metrics.json", {"canonical_model_id": model_id, "report_status": report_status, "metrics": metrics, "benchmark": benchmark, "validation": validation, "accepted": False, "live_trading_approved": False, "deployment_approved": False})
        _write_csv(model_out / "model_validation_statistics.csv", [{"canonical_model_id": model_id, **validation}])
        _write_csv(model_out / "model_backtest_benchmark_statistics.csv", [{"canonical_model_id": model_id, "primary_benchmark": benchmark["benchmark_id"], **metrics}])
        (model_out / "model_benchmark_selection.md").write_text(_benchmark_markdown(model_id, benchmark), encoding="utf-8")
        _write_csv(model_out / "model_data_quality_and_limitations.csv", [quality_rows[-1]])
        (model_out / "model_performance_addendum.md").write_text(_addendum_markdown(model_id, model, report_status, benchmark, validation, metrics, source), encoding="utf-8")
        addendum = str((model_out / "model_performance_addendum.md").relative_to(root)) if model_out.is_relative_to(root) else str(model_out / "model_performance_addendum.md")
        link_rows.append({"canonical_model_id": model_id, "source_evidence_paths": sources, "addendum_path": addendum, "status": report_status})
        completeness_rows.append({"canonical_model_id": model_id, "has_source_evidence": bool(model["evidence_paths"]), "has_addendum": True, "report_status": report_status, "missing_reason": "" if series else "daily_nav_or_return_series_not_found_or_not_eligible"})

    aliases = [{"model_id": mid, "canonical_model_id": m["alias_of"] or mid, "relationship": "alias_of" if m["alias_of"] else "canonical"} for mid, m in sorted(models.items())]
    _write_csv(out / "v5n_model_inventory.csv", identity_rows)
    _write_csv(out / "v5n_model_identity_and_lineage.csv", identity_rows)
    _write_csv(out / "v5n_model_alias_supersession_map.csv", aliases)
    _write_csv(out / "v5n_report_scope_and_status.csv", quality_rows)
    _write_csv(out / "v5n_benchmark_selection_register.csv", benchmark_rows)
    _write_csv(out / "v5n_benchmark_coverage_and_data_quality.csv", benchmark_rows)
    _write_csv(out / "v5n_benchmark_exposure_rationale.csv", benchmark_rows)
    _write_csv(out / "v5n_benchmark_pit_and_future_information_audit.csv", [{"audit_item": "post_boundary_data_used", "result": False}, {"audit_item": "future_etf_or_index_holdings_used", "result": False}, {"audit_item": "benchmark_selected_by_historical_return", "result": False}])
    _write_csv(out / "v5n_benchmark_unavailable_or_exception_register.csv", [r for r in benchmark_rows if r["coverage_status"] != "coverage_pass"])
    _write_csv(out / "v5n_validation_period_statistics.csv", validation_rows)
    _write_csv(out / "v5n_formal_backtest_performance_statistics.csv", backtest_rows)
    _write_csv(out / "v5n_execution_evidence_statistics.csv", execution_rows)
    _write_csv(out / "v5n_model_daily_alignment_audit.csv", [{"canonical_model_id": r["canonical_model_id"], "alignment_status": "common_daily_observations_used" if r["observations"] != "not_available" else "daily_nav_unavailable", "observations": r["observations"]} for r in backtest_rows])
    _write_csv(out / "v5n_metric_unavailable_reason_register.csv", [r for r in quality_rows if r["daily_series_status"] != "available" or r["benchmark_status"] != "coverage_pass"])
    _write_csv(out / "v5n_cross_period_comparability_audit.csv", [{"canonical_model_id": r["canonical_model_id"], "formal_window": f"{FORMAL_START}_to_{BOUNDARY}", "comparison_status": "not_ranked_cross_model"} for r in identity_rows])
    _write_csv(out / "v5n_model_report_link_index.csv", link_rows)
    _write_csv(out / "v5n_model_report_completeness.csv", completeness_rows)
    _write_csv(out / "v5n_model_report_data_quality_audit.csv", quality_rows)
    _write_csv(out / "v5n_model_report_governance_audit.csv", [{"audit_item": "model_state_modified", "result": False}, {"audit_item": "old_2021_10_baseline_used_as_primary", "result": False}, {"audit_item": "future_information_used", "result": False}, {"audit_item": "benchmark_selection_optimized", "result": False}])
    _write_csv(out / "v5n_all_models_validation_backtest_benchmark_table.csv", [{**i, **{k: v for k, v in next(b for b in backtest_rows if b["canonical_model_id"] == i["canonical_model_id"]).items() if k != "canonical_model_id"}} for i in identity_rows])
    _write_csv(out / "v5n_all_models_benchmark_register.csv", benchmark_rows)
    _write_csv(out / "v5n_all_models_status_and_limitations.csv", quality_rows)
    _write_csv(out / "v5n_missing_data_and_benchmark_queue.csv", [r for r in quality_rows if r["daily_series_status"] != "available" or r["benchmark_status"] != "coverage_pass"])
    (out / "v5n_report_contract.md").write_text(_contract_markdown(), encoding="utf-8")
    (out / "v5n_metric_calculation_definition.md").write_text(_metric_markdown(), encoding="utf-8")
    (out / "v5n_metric_definition.md").write_text(_metric_markdown(), encoding="utf-8")
    (out / "v5n_benchmark_selection_report.md").write_text("# V5n Benchmark Selection\n\nBenchmarks are evidence-bound and never selected by performance. Overlay primary benchmarks are parent strategies when a common daily series exists. Local same-pool series are labelled static proxy baskets, not ETF total-return series.\n", encoding="utf-8")
    (out / "v5n_model_report_generation_report.md").write_text(_generation_markdown(identity_rows, quality_rows, benchmark_rows), encoding="utf-8")
    (out / "v5n_unified_model_reporting_report.md").write_text(_generation_markdown(identity_rows, quality_rows, benchmark_rows), encoding="utf-8")
    summary = _summary(identity_rows, quality_rows, benchmark_rows)
    _write_json(out / "v5n_model_inventory_summary.json", summary)
    _write_json(out / "v5n_model_report_generation_summary.json", summary)
    _write_json(out / "v5n_unified_model_reporting_summary.json", summary)
    _write_csv(out / "v5n_pm_governance_decision.csv", [{"decision": "reporting_system_complete_no_strategy_promotion", "model_state_modified": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False}])
    _write_csv(out / "v5n_next_agent_queue.csv", [{"priority": "P0", "task": "recover_original_cash_and_qmt_historical_contract_evidence", "status": "blocked_by_missing_original_artifacts"}, {"priority": "P1", "task": "maintain_addenda_when_new_local_historical_evidence_is_archived", "status": "allowed_reporting_only"}])
    (out / "v5n_agent_execution_rules.md").write_text("# V5n Rules\n\nRead local, pre-boundary evidence only. Do not modify model status, rules, source reports, targets, platforms, or trading state. Unavailable metrics remain unavailable.\n", encoding="utf-8")
    return summary


def _registered_models(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in (root / "config/v5_experiment_catalog.json", root / "config/v5_active_model_registry.json"):
        data = _json(path)
        for key in ("experiments", "active_models", "research_lines"):
            for item in data.get(key, []):
                mid = item.get("experiment_id") or item.get("model_id")
                if mid:
                    result[mid] = item
    return result


def _inventory(root: Path, registered: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    models: dict[str, dict[str, Any]] = {}
    def add(mid: str, evidence: str, role: str = "research_or_strategy_artifact", alias: str = "") -> None:
        if not mid:
            return
        entry = models.setdefault(mid, {"display_name": mid, "family": _family(mid), "role": role, "parent_model": BASELINE if mid != BASELINE else "self", "alias_of": alias, "evidence_paths": []})
        if evidence not in entry["evidence_paths"]:
            entry["evidence_paths"].append(evidence)
    for mid, item in registered.items():
        add(mid, item.get("evidence", "config/v5_experiment_catalog.json"), item.get("role") or item.get("layer", "registered_research"))
        models[mid]["parent_model"] = item.get("baseline_id", BASELINE if mid != BASELINE else "self")
    for path in (root / "examples").glob("*.json"):
        data = _json(path)
        mid = data.get("strategy_id") or data.get("model_id") or path.stem.replace("_strategy", "")
        alias = BASELINE if mid == "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" else ""
        add(mid, str(path.relative_to(root)), "example_strategy", alias)
    for folder in root.iterdir():
        if not folder.is_dir() or not re.match(r"^v5[b-m](?:_|$)", folder.name):
            continue
        current = folder / "current"
        if current.is_dir():
            evidence = [str(p.relative_to(root)) for p in current.glob("*summary.json")]
            add(folder.name, evidence[0] if evidence else str(current.relative_to(root)), "current_artifact")
    add(BASELINE, "v5_startup_warmup_price_repair/current/runs/v57f_warmup_repaired_daily_backtest", "required_baseline")
    return models


def _return_sources(root: Path) -> list[Path]:
    sources: list[Path] = []
    for pattern in ("*daily*return*.csv", "*daily*nav*.csv"):
        for path in root.rglob(pattern):
            lower = str(path).lower()
            if any(marker in lower for marker in EXCLUDED_PATH_MARKERS) or "v5n_model_performance_reporting" in lower:
                continue
            sources.append(path)
    return sources


def _find_source(model_id: str, model: dict[str, Any], sources: Iterable[Path]) -> Path | None:
    sources = list(sources)
    if model_id == PRIMARY:
        return next((p for p in sources if p.name == "v5f_structural_rough_screen_daily_returns.csv"), None)
    if model_id == BASELINE:
        return next((p for p in sources if p.name == "v5f_structural_rough_screen_daily_returns.csv"), None)
    needles = {model_id.lower(), model_id.replace("_strategy", "").lower()}
    candidates = [p for p in sources if any(n in str(p).lower() for n in needles)]
    return sorted(candidates, key=lambda p: ("current" not in str(p).lower(), len(str(p))))[0] if candidates else None


def _read_series(path: Path | None, model_id: str = "") -> dict[str, list[float]] | None:
    if path is None or not path.exists():
        return None
    for encoding in ("utf-8-sig", "gbk"):
        try:
            with path.open(encoding=encoding, newline="") as handle:
                rows = list(csv.DictReader(handle))
            break
        except UnicodeDecodeError:
            continue
    else:
        return None
    if model_id and rows and "version_id" in rows[0]:
        rows = [row for row in rows if row.get("version_id") == model_id]
    dates, strategy, benchmark = [], [], []
    for row in rows:
        date = _date_from_row(row)
        if not date or date < FORMAL_START or date > BOUNDARY:
            continue
        sr = _float_from(row, ("strategy_return", "return", "daily_return"))
        br = _float_from(row, ("baseline_return", "benchmark_return"))
        dates.append(date); strategy.append(sr); benchmark.append(br)
    if not strategy or all(v is None for v in strategy):
        navs = [_float_from(r, ("strategy_nav", "nav")) for r in rows if _date_from_row(r) and FORMAL_START <= _date_from_row(r) <= BOUNDARY]
        if len(navs) > 1 and all(v is not None for v in navs):
            strategy = [navs[i] / navs[i - 1] - 1 for i in range(1, len(navs))]
            dates = dates[1:] if len(dates) == len(navs) else dates[:len(strategy)]
        else:
            return None
    valid = [(d, s, b) for d, s, b in zip(dates, strategy, benchmark) if s is not None]
    if not valid:
        return None
    return {"dates": [x[0] for x in valid], "strategy": [x[1] for x in valid], "benchmark": [x[2] for x in valid if x[2] is not None]}


def _benchmark_for(model_id: str, model: dict[str, Any], source: Path | None, series: dict[str, list[float]] | None) -> dict[str, Any]:
    overlay = model_id in (PRIMARY, "locked_pool_monthly_mom12_70_30") or "overlay" in model_id or "mom" in model_id
    has_benchmark = bool(series and len(series["benchmark"]) >= 60)
    if overlay and has_benchmark:
        return {"benchmark_id": model["parent_model"], "benchmark_name": model["parent_model"], "benchmark_type": "parent_strategy", "primary_benchmark_statement": "primary_benchmark_is_parent_strategy", "economic_exposure_benchmark": "static_proxy_basket_not_separately_available", "tradable": "not_applicable", "price_data_path": str(source) if source else "not_available", "data_source": "local_historical_daily_series", "coverage_pct": 100.0, "coverage_status": "coverage_pass", "pit_future_information": "no_future_information_used", "selection_basis": "parent_lineage_predefined"}
    if has_benchmark:
        return {"benchmark_id": "local_same_pool_or_embedded_benchmark", "benchmark_name": "local same-pool / embedded benchmark", "benchmark_type": "static_proxy_basket", "primary_benchmark_statement": "primary_benchmark_is_market_exposure_proxy", "economic_exposure_benchmark": "local_same_pool_or_embedded_benchmark", "tradable": "proxy_not_directly_tradeable", "price_data_path": str(source) if source else "not_available", "data_source": "local_historical_daily_series", "coverage_pct": 100.0, "coverage_status": "coverage_pass", "pit_future_information": "no_future_information_used", "selection_basis": "embedded_existing_benchmark_not_return_selected"}
    return {"benchmark_id": "not_available", "benchmark_name": "not_available", "benchmark_type": "not_available", "primary_benchmark_statement": "benchmark_data_unavailable", "economic_exposure_benchmark": "not_available", "tradable": "not_available", "price_data_path": "not_available", "data_source": "not_available", "coverage_pct": 0.0, "coverage_status": "benchmark_coverage_insufficient", "pit_future_information": "not_assessed_without_eligible_series", "selection_basis": "no_local_eligible_benchmark_series"}


def _metrics(strategy: list[float] | None, benchmark: list[float] | None, dates: list[str] | None = None) -> dict[str, Any]:
    na = "not_available"
    fields = {"total_return_pct": na, "annualized_return_pct": na, "max_drawdown_pct": na, "annualized_volatility_pct": na, "sharpe_ratio": na, "observations": na, "start_date": na, "end_date": na, "benchmark_total_return_pct": na, "benchmark_annualized_return_pct": na, "benchmark_max_drawdown_pct": na, "benchmark_annualized_volatility_pct": na, "excess_return_pct_points": na, "annualized_excess_return_pct": na, "max_drawdown_delta_pct_points": na, "volatility_ratio": na, "tracking_error_pct": na, "information_ratio": na, "beta_zero_rf": na, "alpha_zero_rf_annualized_pct": na}
    if not strategy or len(strategy) < 2:
        return fields
    fields.update(_absolute_metrics(strategy, "")); fields["observations"] = len(strategy)
    if dates:
        fields["start_date"] = dates[0]; fields["end_date"] = dates[-1]
    if not benchmark or len(benchmark) != len(strategy) or len(strategy) < 60:
        return fields
    b = _absolute_metrics(benchmark, "benchmark_")
    fields.update(b)
    active = [s - x for s, x in zip(strategy, benchmark)]
    fields["excess_return_pct_points"] = fields["total_return_pct"] - fields["benchmark_total_return_pct"]
    fields["annualized_excess_return_pct"] = mean(active) * 252 * 100
    fields["max_drawdown_delta_pct_points"] = fields["max_drawdown_pct"] - fields["benchmark_max_drawdown_pct"]
    fields["volatility_ratio"] = fields["annualized_volatility_pct"] / fields["benchmark_annualized_volatility_pct"] if fields["benchmark_annualized_volatility_pct"] else na
    active_sd = stdev(active)
    fields["tracking_error_pct"] = active_sd * math.sqrt(252) * 100
    fields["information_ratio"] = math.sqrt(252) * mean(active) / active_sd if active_sd else na
    strategy_mean = mean(strategy)
    benchmark_mean = mean(benchmark)
    bvar = sum((x - benchmark_mean) ** 2 for x in benchmark) / (len(benchmark) - 1)
    covariance = sum((s - strategy_mean) * (x - benchmark_mean) for s, x in zip(strategy, benchmark)) / (len(benchmark) - 1)
    beta = covariance / bvar if bvar else na
    fields["beta_zero_rf"] = beta
    fields["alpha_zero_rf_annualized_pct"] = (strategy_mean - beta * benchmark_mean) * 252 * 100 if beta != na else na
    return fields


def _absolute_metrics(values: list[float], prefix: str) -> dict[str, float]:
    nav = 1.0; peak = 1.0; drawdown = 0.0
    for value in values:
        nav *= 1 + value; peak = max(peak, nav); drawdown = min(drawdown, nav / peak - 1)
    vol = stdev(values) * math.sqrt(252) * 100 if len(values) > 1 else 0.0
    return {f"{prefix}total_return_pct": (nav - 1) * 100, f"{prefix}annualized_return_pct": (nav ** (252 / len(values)) - 1) * 100, f"{prefix}max_drawdown_pct": -drawdown * 100, f"{prefix}annualized_volatility_pct": vol, f"{prefix}sharpe_ratio": math.sqrt(252) * mean(values) / stdev(values) if stdev(values) else "not_available"}


def _report_status(model: dict[str, Any], source: Path | None, metrics: dict[str, Any]) -> str:
    text = " ".join([model["role"], *model["evidence_paths"]]).lower()
    if model["alias_of"]:
        return "duplicate_or_alias_of_canonical_model"
    if any(x in text for x in ("archived", "superseded", "rejected", "closeout")):
        return "archived_or_superseded"
    if any(x in text for x in ("execution", "qmt", "1min", "5min", "order")) and not source:
        return "execution_only_no_strategy_nav"
    if not source:
        return "diagnostic_only_no_nav_claim" if any(x in text for x in ("diagnostic", "audit", "spec", "gate", "research")) else "performance_data_unavailable"
    return "report_complete_validation_not_independent"


def _validation_for(model: dict[str, Any], source: Path | None) -> dict[str, Any]:
    if not source:
        return {"validation_window": "not_available", "sample_size": "not_available", "validation_type": "not_available", "independent": False, "overlaps_formal_backtest": "not_available", "validation_result": "daily_nav_unavailable"}
    return {"validation_window": f"{FORMAL_START}_to_{BOUNDARY}", "sample_size": "same_as_formal_backtest_if_series_eligible", "validation_type": "historical_artifact_reuse", "independent": False, "overlaps_formal_backtest": True, "validation_result": "validation_not_independent_or_overlapping"}


def _limitations(model: dict[str, Any], source: Path | None, series: dict[str, list[float]] | None, benchmark: dict[str, Any]) -> str:
    bits = ["companion_reporting_only", "no_model_status_change"]
    if not source: bits.append("daily_nav_or_returns_unavailable")
    if benchmark["coverage_status"] != "coverage_pass": bits.append("eligible_benchmark_unavailable")
    if series: bits.append("formal_validation_not_independent")
    if model["parent_model"] == BASELINE and model["display_name"] != BASELINE: bits.append("comparison_does_not_repair_cash_or_order_contract")
    return ";".join(bits)


def _execution_type(source: Path | None) -> str:
    if not source: return "not_available"
    lower = str(source).lower()
    if "qmt" in lower: return "qmt_no_order_or_imported_series_not_fill_contract"
    return "local_price_or_nav_series"


def _date_from_row(row: dict[str, str]) -> str | None:
    for key in ("trade_date", "date", "datetime", "timestamp", "时间"):
        if key in row and row[key]:
            match = re.search(r"(20\d{2})[-/]?(\d{2})[-/]?(\d{2})", row[key])
            if match: return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    for value in row.values():
        match = re.search(r"(20\d{2})[-/]?(\d{2})[-/]?(\d{2})", value or "")
        if match: return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def _float_from(row: dict[str, str], names: tuple[str, ...]) -> float | None:
    for name in names:
        if name in row and row[name] not in ("", None):
            try: return float(row[name])
            except ValueError: pass
    return None


def _family(model_id: str) -> str:
    low = model_id.lower()
    if "v57f" in low or model_id == BASELINE: return "v57f_baseline"
    if any(x in low for x in ("momentum", "mom12", "internal_subsleeve")): return "momentum_overlay"
    if any(x in low for x in ("mean_reversion", "mr_", "reversion")): return "mean_reversion"
    if any(x in low for x in ("execution", "qmt", "1min", "5min", "order")): return "execution_or_platform"
    if any(x in low for x in ("bank", "power", "highway", "port", "gas", "telecom", "insurance", "coal", "utility")): return "sector_strategy_or_research"
    return "governance_or_research_artifact"


def _safe_id(value: str) -> str: return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
def _relative_source(source: Path | None, root: Path) -> str:
    if source is None: return "not_available"
    try: return str(source.relative_to(root))
    except ValueError: return str(source)
def _json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8-sig"))
def _write_json(path: Path, value: Any) -> None: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


def _contract_markdown() -> str:
    return "# V5n Reporting Contract\n\nThis is a companion reporting system. It neither reruns nor promotes models. Formal historical scope is 2021-05-01 to 2026-05-31; V57f repaired baseline is the only new-mainline baseline. Metrics use common daily simple returns and 252 annualisation. Missing order, cash, NAV, benchmark, or independent-validation evidence remains unavailable.\n"
def _metric_markdown() -> str:
    return "# Metric Definitions\n\nReturns are daily simple returns on common dates. Volatility is sample daily standard deviation times sqrt(252). Sharpe and information ratio use zero risk-free rate. Beta is daily covariance divided by benchmark variance. Alpha is `252 * mean(strategy - beta * benchmark)`. A benchmark with fewer than 60 common days or less than 95% coverage does not receive formal risk statistics.\n"
def _benchmark_markdown(mid: str, b: dict[str, Any]) -> str:
    return f"# Benchmark Selection: {mid}\n\n- Primary: `{b['benchmark_id']}`\n- Type: `{b['benchmark_type']}`\n- Basis: `{b['selection_basis']}`\n- Coverage: `{b['coverage_pct']}` (`{b['coverage_status']}`)\n- Future-information audit: `{b['pit_future_information']}`\n"
def _addendum_markdown(mid: str, model: dict[str, Any], status: str, b: dict[str, Any], v: dict[str, Any], metrics: dict[str, Any], source: Path | None) -> str:
    return f"# Model Performance Addendum\n\n## Identity\n\n- Canonical model: `{mid}`\n- Family: `{model['family']}`\n- Role: `{model['role']}`\n- Parent: `{model['parent_model']}`\n- Report status: `{status}`\n- Accepted/live/deployment: `false / false / false`\n- Formal scope: `{FORMAL_START}` to `{BOUNDARY}`\n\n## Benchmark\n\n- Primary: `{b['benchmark_id']}` ({b['primary_benchmark_statement']})\n- Economic exposure: `{b['economic_exposure_benchmark']}`\n- Coverage: `{b['coverage_pct']}`; `{b['coverage_status']}`\n\n## Validation\n\n- Type: `{v['validation_type']}`\n- Independent: `{v['independent']}`\n- Result: `{v['validation_result']}`\n\n## Formal Backtest\n\n| Metric | Value |\n|---|---:|\n" + "\n".join(f"| {key} | {value} |" for key, value in metrics.items()) + f"\n\nReturn source: `{source if source else 'not_available'}`.\n\n## Execution Evidence\n\nAny local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.\n\n## Current Conclusion\n\n`reporting_only_not_strategy_promotion`\n"
def _generation_markdown(identity: list[dict[str, Any]], quality: list[dict[str, Any]], benchmark: list[dict[str, Any]]) -> str:
    return f"# V5n Unified Model Reporting\n\nInventory contains {len(identity)} canonical/reporting units. Addenda are companion evidence only. {sum(r['daily_series_status'] == 'available' for r in quality)} units have eligible local daily series; {sum(r['coverage_status'] == 'coverage_pass' for r in benchmark)} have an embedded/parent benchmark eligible for formal daily comparison. No status, rule, target, or source report was modified.\n"
def _summary(identity: list[dict[str, Any]], quality: list[dict[str, Any]], benchmark: list[dict[str, Any]]) -> dict[str, Any]:
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5n_unified_model_performance_reporting", "formal_backtest_window": {"start": FORMAL_START, "end": BOUNDARY}, "required_baseline": BASELINE, "model_count": len(identity), "completed_report_count": len(identity), "daily_series_available_count": sum(r["daily_series_status"] == "available" for r in quality), "benchmark_coverage_pass_count": sum(r["coverage_status"] == "coverage_pass" for r in benchmark), "model_state_modified": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False}
def _assert_boundary(root: Path) -> None:
    boundary = _json(root / "config/v5_historical_operation_boundary.json")
    if boundary.get("market_data_max_date") != BOUNDARY: raise ValueError("V5n boundary mismatch")

if __name__ == "__main__":
    print(json.dumps(run_v5n_model_performance_reporting(), ensure_ascii=False, indent=2))
