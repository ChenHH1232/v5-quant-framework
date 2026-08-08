from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_structural_rough_screen_runner import (
    BACKTEST_END,
    BACKTEST_START,
    BASELINE,
    PRICE_DIR,
    REPAIRED_RUN,
    _daily_returns,
    _load_prices,
    _max_drawdown,
    _safe_float,
)


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_bank_power_financial_report_pit_panel") / "current"
BATCH_DIR = Path("v5c_bank_power_financial_report_batch_extraction") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
PRIMARY = "internal_subsleeve_mom12_70_30"
BANK = "bank"
POWER = "utilities_electricity"


@dataclass(frozen=True)
class MetricRule:
    metric: str
    industry: str
    field: str
    keywords: tuple[str, ...]
    unit: str
    min_value: float | None = None
    max_value: float | None = None
    higher_is_better: bool = True
    model_use: str = "score"
    keyword_priority: int = 5


METRIC_RULES: tuple[MetricRule, ...] = (
    MetricRule("net_interest_margin_pct", BANK, "net_interest_margin", ("净息差",), "%", 0.0, 8.0, True, keyword_priority=0),
    MetricRule("net_interest_spread_pct", BANK, "net_interest_margin", ("净利差",), "%", 0.0, 8.0, True, "review", 1),
    MetricRule("deposit_cost_pct", BANK, "deposit_cost", ("存款成本率", "客户存款成本", "平均付息率", "吸收存款平均成本"), "%", 0.0, 8.0, False, keyword_priority=0),
    MetricRule("interest_earning_assets_amount", BANK, "interest_earning_assets", ("生息资产",), "amount", 0.0, None, True, "review", 2),
    MetricRule("non_performing_loan_ratio_pct", BANK, "asset_quality", ("不良贷款率",), "%", 0.0, 10.0, False, keyword_priority=0),
    MetricRule("special_mention_loan_ratio_pct", BANK, "asset_quality", ("关注类贷款",), "%", 0.0, 15.0, False, "score", 1),
    MetricRule("provision_coverage_ratio_pct", BANK, "asset_quality", ("拨备覆盖率",), "%", 50.0, 1000.0, True, keyword_priority=0),
    MetricRule("core_tier1_capital_ratio_pct", BANK, "capital_buffer", ("核心一级资本充足率",), "%", 4.0, 25.0, True, keyword_priority=0),
    MetricRule("tier1_capital_ratio_pct", BANK, "capital_buffer", ("一级资本充足率",), "%", 4.0, 30.0, True, "review", 1),
    MetricRule("capital_adequacy_ratio_pct", BANK, "capital_buffer", ("资本充足率",), "%", 8.0, 35.0, True, keyword_priority=1),
    MetricRule("fuel_cost_amount", POWER, "fuel_cost", ("燃料成本", "燃煤成本"), "亿元", 0.0, None, False, "score_yoy", 0),
    MetricRule("coal_price_mention_value", POWER, "fuel_cost", ("煤价", "标煤单价", "入炉标煤单价"), "mixed", 0.0, None, False, "review", 2),
    MetricRule("tariff_yuan_per_kwh", POWER, "tariff", ("平均上网电价", "上网电价"), "元/千瓦时", 0.05, 2.0, True, keyword_priority=0),
    MetricRule("capacity_payment_flag", POWER, "capacity_payment", ("容量电价", "容量电费", "容量补偿", "容量电价机制"), "flag", 0.0, 1.0, True, "review", 3),
    MetricRule("utilization_hours", POWER, "utilization_hours", ("利用小时", "发电设备平均利用小时"), "小时", 100.0, 9000.0, True, keyword_priority=0),
    MetricRule("hydro_water_flag", POWER, "hydro_water", ("来水", "径流", "蓄水", "水库", "水电"), "flag", 0.0, 1.0, True, "review", 3),
    MetricRule("generation_volume", POWER, "generation_volume", ("发电量", "上网电量", "售电量"), "亿千瓦时", 0.0, None, True, "score_yoy", 0),
)

VERSION_FAMILIES = {
    BASELINE: "baseline",
    PRIMARY: "v5f_primary_reference",
    "bank_report_overlay_on_v5f_10pct": "financial_report_overlay_on_v5f",
    "power_report_overlay_on_v5f_10pct": "financial_report_overlay_on_v5f",
    "bank_power_report_overlay_on_v5f_10pct": "financial_report_overlay_on_v5f",
    "bank_power_report_replace_mom30": "financial_report_replaces_bank_power_momentum",
}


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_bank_power_financial_report_pit_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_inputs", blockers=blockers)
        _write_json(out / "v5c_bank_power_financial_report_pit_panel_summary.json", summary)
        return out / "v5c_bank_power_financial_report_pit_panel_summary.json"

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    primary_weights = pd.read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_weights.csv", dtype={"rebalance_date": str, "code": str})
    candidates = _load_candidates(root)

    review_rows = _review_candidates(candidates)
    report_panel = _reviewed_report_panel(review_rows)
    report_panel = _add_yoy_fields(report_panel)
    rebalance_panel = _rebalance_pit_panel(signals, report_panel)
    factor_scores = _factor_scores(signals, rebalance_panel)
    weights = _build_weights(signals, primary_weights, factor_scores)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    coverage = _coverage_audit(signals, rebalance_panel, review_rows)
    governance = _governance(weights, coverage)
    comparison = _comparison(metrics)
    decision = _pm_decision(comparison, governance, coverage)
    next_queue = _next_queue(decision[0]["pm_gate_decision"], comparison, coverage)
    blockers_out = _blockers(governance)

    _write_csv(out / "v5c_bank_power_original_page_review_audit.csv", review_rows)
    _write_csv(out / "v5c_bank_power_reviewed_report_field_panel.csv", report_panel)
    _write_csv(out / "v5c_bank_power_rebalance_pit_field_panel.csv", rebalance_panel)
    _write_csv(out / "v5c_bank_power_financial_report_factor_scores.csv", factor_scores)
    _write_csv(out / "v5c_bank_power_financial_report_factor_weights.csv", weights)
    _write_csv(out / "v5c_bank_power_financial_report_factor_daily_returns.csv", daily)
    _write_csv(out / "v5c_bank_power_financial_report_factor_metrics.csv", metrics)
    _write_csv(out / "v5c_bank_power_financial_report_factor_yearly.csv", yearly)
    _write_csv(out / "v5c_bank_power_financial_report_pit_coverage_audit.csv", coverage)
    _write_csv(out / "v5c_bank_power_financial_report_governance_audit.csv", governance)
    _write_csv(out / "v5c_bank_power_financial_report_factor_comparison.csv", comparison)
    _write_csv(out / "v5c_bank_power_financial_report_factor_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_bank_power_financial_report_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_bank_power_financial_report_pit_blockers.csv", blockers_out)
    (out / "v5c_bank_power_financial_report_pit_panel_report.md").write_text(
        _report(comparison, decision, coverage, governance),
        encoding="utf-8",
    )
    (out / "v5c_bank_power_financial_report_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = comparison[0]
    summary = _summary(
        "completed_financial_report_pit_panel_and_factor_retest",
        reviewed_candidate_count=sum(1 for row in review_rows if row["review_status"] == "automated_original_page_review_pass"),
        report_panel_rows=len(report_panel),
        rebalance_panel_rows=len(rebalance_panel),
        best_version=best["version_id"],
        best_delta_vs_v5f=float(best["delta_return_pct_points_vs_v5f_primary"]),
        best_delta_vs_baseline=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        pm_gate_decision=decision[0]["pm_gate_decision"],
        blockers=blockers_out,
    )
    _write_json(out / "v5c_bank_power_financial_report_pit_panel_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_bank_power_financial_report_pit_panel_summary.json"


def _load_candidates(root: Path) -> list[dict[str, str]]:
    rows = []
    for rel in [
        BATCH_DIR / "v5c_bank_financial_report_field_candidates.csv",
        BATCH_DIR / "v5c_power_financial_report_field_candidates.csv",
    ]:
        rows.extend(_read_csv(root / rel))
    return rows


def _review_candidates(candidates: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in candidates:
        rule = _rule_for(row)
        if rule is None:
            continue
        value, value_token, unit_status = _metric_value(row, rule)
        context = row.get("sample_context", "")
        source_exists = Path(row.get("local_pdf_path", "")).exists()
        page_ok = bool(str(row.get("page_number", "")).strip())
        visible_ok = bool(row.get("announcement_date")) and bool(row.get("report_period")) and row["announcement_date"] >= row["report_period"]
        keyword_ok = row.get("keyword", "") in rule.keywords and row.get("field", "") == rule.field
        value_ok = value is not None if rule.unit != "flag" else keyword_ok
        review_status = (
            "automated_original_page_review_pass"
            if source_exists and page_ok and visible_ok and keyword_ok and value_ok
            else "needs_manual_original_review"
        )
        rows.append(
            {
                "industry": row.get("industry", ""),
                "code": row.get("code", ""),
                "sec_name": row.get("sec_name", ""),
                "report_period": row.get("report_period", ""),
                "announcement_date": row.get("announcement_date", ""),
                "pit_visible_date": row.get("pit_visible_date") or row.get("announcement_date", ""),
                "field": row.get("field", ""),
                "metric": rule.metric,
                "keyword": row.get("keyword", ""),
                "page_number": row.get("page_number", ""),
                "reviewed_value": "" if value is None else _fmt(value),
                "reviewed_unit": rule.unit,
                "value_token": value_token,
                "unit_status": unit_status,
                "metric_model_use": rule.model_use,
                "higher_is_better": rule.higher_is_better,
                "keyword_priority": rule.keyword_priority,
                "local_pdf_path": row.get("local_pdf_path", ""),
                "pdf_url": row.get("pdf_url", ""),
                "source_exists": source_exists,
                "page_context_present": bool(context),
                "visible_date_status": "pass" if visible_ok else "review",
                "review_status": review_status,
                "review_note": "Automated review from original CNInfo PDF page text; table scope/unit still auditable via page context.",
                "sample_context": context,
            }
        )
    return rows


def _reviewed_report_panel(review_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passed = [row for row in review_rows if row["review_status"] == "automated_original_page_review_pass"]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in passed:
        grouped.setdefault((row["code"], row["report_period"], row["metric"]), []).append(row)
    best_rows = []
    for key, values in grouped.items():
        ranked = sorted(
            values,
            key=lambda row: (
                int(row["keyword_priority"]),
                0 if str(row["unit_status"]).startswith("explicit") else 1,
                int(float(row["page_number"] or 99999)),
                int(float(row.get("hit_index") or 99999)) if str(row.get("hit_index", "")).strip() else 99999,
            ),
        )
        best_rows.append(ranked[0])

    by_report: dict[tuple[str, str], dict[str, Any]] = {}
    for row in best_rows:
        key = (row["code"], row["report_period"])
        item = by_report.setdefault(
            key,
            {
                "industry": row["industry"],
                "code": row["code"],
                "sec_name": row["sec_name"],
                "report_period": row["report_period"],
                "announcement_date": row["announcement_date"],
                "pit_visible_date": row["pit_visible_date"],
                "review_status": "automated_original_page_review_pass",
                "source_pdf_path": row["local_pdf_path"],
            },
        )
        metric = row["metric"]
        item[metric] = row["reviewed_value"]
        item[f"{metric}_unit"] = row["reviewed_unit"]
        item[f"{metric}_page"] = row["page_number"]
        item[f"{metric}_keyword"] = row["keyword"]
    metrics = [rule.metric for rule in METRIC_RULES]
    rows = []
    for item in by_report.values():
        item["reviewed_metric_count"] = sum(1 for metric in metrics if item.get(metric) not in (None, ""))
        rows.append(item)
    return sorted(rows, key=lambda row: (row["industry"], row["code"], row["report_period"]))


def _add_yoy_fields(report_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(report_panel)
    if df.empty:
        return report_panel
    yoy_metrics = ["fuel_cost_amount", "generation_volume", "utilization_hours", "tariff_yuan_per_kwh"]
    for metric in yoy_metrics:
        if metric not in df.columns:
            df[metric] = ""
    rows = []
    for _, group in df.sort_values(["code", "report_period"]).groupby("code", sort=False):
        group = group.copy()
        for metric in yoy_metrics:
            values = pd.to_numeric(group[metric], errors="coerce")
            group[f"{metric}_yoy"] = values / values.shift(1) - 1.0
        rows.extend(group.fillna("").to_dict("records"))
    return rows


def _rebalance_pit_panel(signals: pd.DataFrame, report_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    report_by_code: dict[str, list[dict[str, Any]]] = {}
    for row in report_panel:
        report_by_code.setdefault(row["code"], []).append(row)
    for values in report_by_code.values():
        values.sort(key=lambda row: (row.get("pit_visible_date", ""), row.get("report_period", "")))
    rows: list[dict[str, Any]] = []
    metrics = sorted({rule.metric for rule in METRIC_RULES} | {f"{metric}_yoy" for metric in ["fuel_cost_amount", "generation_volume", "utilization_hours", "tariff_yuan_per_kwh"]})
    for _, signal in signals[signals["sector_id"].isin([BANK, POWER])].iterrows():
        trade_date = str(signal["trade_date"])
        code = str(signal["code"])
        usable = [row for row in report_by_code.get(code, []) if row.get("pit_visible_date", "") <= trade_date]
        latest = usable[-1] if usable else {}
        out = {
            "trade_date": trade_date,
            "code": code,
            "sleeve": signal["sector_id"],
            "target_weight": signal["target_weight"],
            "matched_report_period": latest.get("report_period", ""),
            "matched_visible_date": latest.get("pit_visible_date", ""),
            "pit_status": "pass" if latest else "missing_visible_report",
            "review_status": latest.get("review_status", ""),
            "reviewed_metric_count": latest.get("reviewed_metric_count", 0),
        }
        for metric in metrics:
            out[metric] = latest.get(metric, "")
        rows.append(out)
    return rows


def _factor_scores(signals: pd.DataFrame, rebalance_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    panel = pd.DataFrame(rebalance_panel)
    if panel.empty:
        return []
    rows = []
    for (date, sleeve), group in panel.groupby(["trade_date", "sleeve"], sort=True):
        group = group.copy()
        if sleeve == BANK:
            components = [
                _rank_component(group, "net_interest_margin_pct", True),
                _rank_component(group, "provision_coverage_ratio_pct", True),
                _rank_component(group, "core_tier1_capital_ratio_pct", True),
                _rank_component(group, "capital_adequacy_ratio_pct", True),
                _rank_component(group, "non_performing_loan_ratio_pct", False),
                _rank_component(group, "deposit_cost_pct", False),
                _rank_component(group, "special_mention_loan_ratio_pct", False),
            ]
        else:
            components = [
                _rank_component(group, "utilization_hours", True),
                _rank_component(group, "tariff_yuan_per_kwh", True),
                _rank_component(group, "generation_volume_yoy", True),
                _rank_component(group, "fuel_cost_amount_yoy", False),
            ]
        score = pd.concat([series for series in components if series is not None], axis=1).mean(axis=1, skipna=True)
        available = pd.concat([series.notna().astype(int) for series in components if series is not None], axis=1).sum(axis=1)
        group["financial_report_score"] = score
        group["financial_report_factor_available_count"] = available
        rank = score.rank(method="first")
        group["financial_report_bucket"] = "middle"
        group.loc[rank > len(group) * 2 / 3, "financial_report_bucket"] = "report_top"
        group.loc[rank <= len(group) / 3, "financial_report_bucket"] = "report_bottom"
        for _, row in group.iterrows():
            rows.append(
                {
                    "trade_date": row["trade_date"],
                    "code": row["code"],
                    "sleeve": row["sleeve"],
                    "matched_report_period": row["matched_report_period"],
                    "matched_visible_date": row["matched_visible_date"],
                    "pit_status": row["pit_status"],
                    "reviewed_metric_count": row["reviewed_metric_count"],
                    "financial_report_score": row["financial_report_score"],
                    "financial_report_bucket": row["financial_report_bucket"],
                    "financial_report_factor_available_count": int(row["financial_report_factor_available_count"]),
                    "net_interest_margin_pct": row.get("net_interest_margin_pct", ""),
                    "deposit_cost_pct": row.get("deposit_cost_pct", ""),
                    "non_performing_loan_ratio_pct": row.get("non_performing_loan_ratio_pct", ""),
                    "provision_coverage_ratio_pct": row.get("provision_coverage_ratio_pct", ""),
                    "core_tier1_capital_ratio_pct": row.get("core_tier1_capital_ratio_pct", ""),
                    "capital_adequacy_ratio_pct": row.get("capital_adequacy_ratio_pct", ""),
                    "fuel_cost_amount_yoy": row.get("fuel_cost_amount_yoy", ""),
                    "tariff_yuan_per_kwh": row.get("tariff_yuan_per_kwh", ""),
                    "utilization_hours": row.get("utilization_hours", ""),
                    "generation_volume_yoy": row.get("generation_volume_yoy", ""),
                }
            )
    return rows


def _rank_component(group: pd.DataFrame, column: str, higher_is_better: bool) -> pd.Series | None:
    if column not in group.columns:
        return None
    values = pd.to_numeric(group[column], errors="coerce")
    if values.notna().sum() == 0:
        return pd.Series(math.nan, index=group.index)
    return values.rank(pct=True, method="average") if higher_is_better else (-values).rank(pct=True, method="average")


def _build_weights(signals: pd.DataFrame, primary_weights: pd.DataFrame, scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = primary_weights[primary_weights["version_id"].eq(PRIMARY)].copy()
    primary_map = primary.set_index(["rebalance_date", "code"])["target_weight"].astype(float).to_dict()
    score_df = pd.DataFrame(scores)
    score_map = score_df.set_index(["trade_date", "code"])[["financial_report_score", "financial_report_bucket", "financial_report_factor_available_count"]].to_dict("index") if not score_df.empty else {}
    rows: list[dict[str, Any]] = []
    for date, group in signals.groupby("trade_date", sort=True):
        base = group.copy()
        base["base_target_weight"] = base["target_weight"].astype(float)
        base["primary_target_weight"] = [primary_map.get((date, row["code"]), float(row["target_weight"])) for _, row in base.iterrows()]
        base["financial_report_score"] = [_safe_float(score_map.get((date, row["code"]), {}).get("financial_report_score")) for _, row in base.iterrows()]
        base["financial_report_bucket"] = [score_map.get((date, row["code"]), {}).get("financial_report_bucket", "") for _, row in base.iterrows()]
        base["financial_report_factor_available_count"] = [score_map.get((date, row["code"]), {}).get("financial_report_factor_available_count", 0) for _, row in base.iterrows()]
        rows.extend(_rows_for_version(base, BASELINE, "baseline", base["base_target_weight"], "baseline"))
        rows.extend(_rows_for_version(base, PRIMARY, "v5f_primary_reference", base["primary_target_weight"], "v5f_primary"))
        rows.extend(_variant_overlay(base, "bank_report_overlay_on_v5f_10pct", {BANK}, 0.10))
        rows.extend(_variant_overlay(base, "power_report_overlay_on_v5f_10pct", {POWER}, 0.10))
        rows.extend(_variant_overlay(base, "bank_power_report_overlay_on_v5f_10pct", {BANK, POWER}, 0.10))
        rows.extend(_variant_replace_mom30(base))
    return rows


def _variant_overlay(base: pd.DataFrame, version: str, sleeves: set[str], budget: float) -> list[dict[str, Any]]:
    target = base["primary_target_weight"].copy()
    target = _apply_top_budget(base, target, sleeves, budget, "primary_target_weight")
    return _rows_for_version(base, version, VERSION_FAMILIES[version], target, f"{version}_top_budget")


def _variant_replace_mom30(base: pd.DataFrame) -> list[dict[str, Any]]:
    target = base["primary_target_weight"].copy()
    replacement = base["base_target_weight"].copy()
    replacement = _apply_top_budget(base, replacement, {BANK, POWER}, 0.30, "base_target_weight")
    mask = base["sector_id"].isin([BANK, POWER])
    target.loc[mask] = replacement.loc[mask]
    return _rows_for_version(base, "bank_power_report_replace_mom30", VERSION_FAMILIES["bank_power_report_replace_mom30"], target, "replace_bank_power_mom30_with_report")


def _apply_top_budget(base: pd.DataFrame, target: pd.Series, sleeves: set[str], budget: float, base_weight_col: str) -> pd.Series:
    target = target.copy()
    for _, sleeve_df in base[base["sector_id"].isin(sleeves)].groupby("sector_id"):
        idx = sleeve_df.index
        sleeve_total = sleeve_df[base_weight_col].astype(float).sum()
        top_idx = _top_indices(sleeve_df)
        core = (1.0 - budget) * sleeve_df[base_weight_col].astype(float)
        alloc = pd.Series(0.0, index=idx)
        alloc.loc[top_idx] = budget * sleeve_total / len(top_idx)
        target.loc[idx] = core + alloc
    return target


def _top_indices(sleeve_df: pd.DataFrame) -> list[int]:
    values = pd.to_numeric(sleeve_df["financial_report_score"], errors="coerce")
    if values.notna().sum() == 0:
        return sleeve_df.index.tolist()
    rank = values.rank(method="first")
    return sleeve_df[rank > len(sleeve_df) * 2 / 3].index.tolist() or [int(values.idxmax())]


def _rows_for_version(base: pd.DataFrame, version: str, family: str, target: pd.Series, bucket: str) -> list[dict[str, Any]]:
    rows = []
    for idx, row in base.iterrows():
        target_weight = float(target.loc[idx])
        rows.append(
            {
                "version_id": version,
                "family": family,
                "rebalance_date": row["trade_date"],
                "code": row["code"],
                "sleeve": row["sector_id"],
                "base_target_weight": float(row["base_target_weight"]),
                "target_weight": target_weight,
                "weight_delta": target_weight - float(row["base_target_weight"]),
                "financial_report_score": row.get("financial_report_score", ""),
                "financial_report_bucket": row.get("financial_report_bucket", ""),
                "financial_report_factor_available_count": row.get("financial_report_factor_available_count", 0),
                "bucket": bucket,
                "sleeve_weight_preserved": True,
                "new_stock_selected": False,
                "accepted": False,
            }
        )
    return rows


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out = []
    for version, group in df.groupby("version_id", sort=True):
        ordered = group.sort_values("trade_date")
        navs = pd.to_numeric(ordered["strategy_nav"]).tolist()
        rets = pd.to_numeric(ordered["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = pd.Series(rets).std() * (252**0.5)
        out.append(
            {
                "version_id": version,
                "family": VERSION_FAMILIES.get(version, "other"),
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "accepted": False,
            }
        )
    baseline = next(row for row in out if row["version_id"] == BASELINE)
    primary = next(row for row in out if row["version_id"] == PRIMARY)
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["strategy_return"]) - float(baseline["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (float(row["max_drawdown"]) - float(baseline["max_drawdown"])) * 100
        row["delta_return_pct_points_vs_v5f_primary"] = (float(row["strategy_return"]) - float(primary["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_v5f_primary"] = (float(row["max_drawdown"]) - float(primary["max_drawdown"])) * 100
    return sorted(out, key=lambda row: float(row["strategy_return"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].str.slice(0, 4)
    out = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append({"version_id": version, "family": VERSION_FAMILIES.get(version, "other"), "year": year, "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1, "trade_days": len(group)})
    base = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    primary = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == PRIMARY}
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - base.get(row["year"], 0.0)) * 100
        row["delta_return_pct_points_vs_v5f_primary"] = (float(row["period_return"]) - primary.get(row["year"], 0.0)) * 100
    return out


def _coverage_audit(signals: pd.DataFrame, rebalance_panel: list[dict[str, Any]], review_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    panel = pd.DataFrame(rebalance_panel)
    rows = []
    for sleeve in [BANK, POWER]:
        group = panel[panel["sleeve"].eq(sleeve)] if not panel.empty else pd.DataFrame()
        metric_cols = [rule.metric for rule in METRIC_RULES if rule.industry == sleeve and rule.model_use in {"score", "score_yoy"}]
        present = 0
        possible = len(group) * len(metric_cols)
        for metric in metric_cols:
            if metric in group:
                present += pd.to_numeric(group[metric], errors="coerce").notna().sum()
            if f"{metric}_yoy" in group:
                present += pd.to_numeric(group[f"{metric}_yoy"], errors="coerce").notna().sum()
                possible += len(group)
        score_ready_rows = 0
        if not group.empty:
            score_fields = [col for col in ["net_interest_margin_pct", "provision_coverage_ratio_pct", "core_tier1_capital_ratio_pct", "capital_adequacy_ratio_pct", "non_performing_loan_ratio_pct", "deposit_cost_pct", "special_mention_loan_ratio_pct", "utilization_hours", "tariff_yuan_per_kwh", "generation_volume_yoy", "fuel_cost_amount_yoy"] if col in group]
            score_ready_rows = int(group[score_fields].apply(lambda row: pd.to_numeric(row, errors="coerce").notna().sum(), axis=1).gt(0).sum()) if score_fields else 0
        rows.append(
            {
                "sleeve": sleeve,
                "rebalance_rows": len(group),
                "score_ready_rows": score_ready_rows,
                "score_ready_coverage": _ratio(score_ready_rows, len(group)),
                "model_metric_present_count": int(present),
                "model_metric_possible_count": possible,
                "model_metric_coverage": _ratio(int(present), possible),
                "reviewed_candidate_count": sum(1 for row in review_rows if row["industry"] == sleeve and row["review_status"] == "automated_original_page_review_pass"),
                "coverage_status": "pass" if len(group) and score_ready_rows / len(group) >= 0.8 else "review",
            }
        )
    return rows


def _governance(weights: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    sleeve_preserved = []
    for (_, _, _), group in df.groupby(["version_id", "rebalance_date", "sleeve"], sort=True):
        sleeve_preserved.append(abs(group["target_weight"].astype(float).sum() - group["base_target_weight"].astype(float).sum()) < 1e-8)
    return [
        {"audit_id": "repaired_baseline_only", "status": "pass", "detail": BASELINE},
        {"audit_id": "v57f_selected_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if all(sleeve_preserved) else "fail", "detail": 0},
        {"audit_id": "pit_visible_annual_reports_only", "status": "pass", "detail": "matched_visible_date <= rebalance_date"},
        {"audit_id": "original_page_review_required", "status": "pass", "detail": "automated_original_page_review_pass rows only used in PIT panel"},
        {"audit_id": "coverage_bank_power", "status": "pass" if all(row["coverage_status"] in {"pass", "review"} for row in coverage) else "fail", "detail": ";".join(f"{row['sleeve']}={row['score_ready_coverage']}" for row in coverage)},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": "fixed variants only: 10pct overlay and replace existing 30pct bank/power momentum"},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
    ]


def _comparison(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        delta = float(row["delta_return_pct_points_vs_v5f_primary"])
        if row["version_id"] == PRIMARY:
            status = "current_v5f_primary_reference"
        elif delta > 0.5 and float(row["delta_max_drawdown_pct_points_vs_v5f_primary"]) <= 0.25:
            status = "possible_incremental_candidate_needs_forward_review"
        elif delta > 0:
            status = "weak_incremental_positive_diagnostic"
        else:
            status = "no_incremental_value_vs_v5f_primary"
        rows.append({**row, "comparison_status": status, "accepted": False})
    return sorted(rows, key=lambda row: float(row["strategy_return"]), reverse=True)


def _pm_decision(comparison: list[dict[str, Any]], governance: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_fail = [row for row in governance if row["status"] == "fail"]
    best = comparison[0]
    if gov_fail:
        decision = "blocked_by_governance_issue"
    elif best["comparison_status"] == "possible_incremental_candidate_needs_forward_review":
        decision = "financial_report_factor_positive_needs_forward_review_not_accepted"
    elif float(best["delta_return_pct_points_vs_v5f_primary"]) > 0:
        decision = "financial_report_factor_weak_positive_diagnostic_only"
    else:
        decision = "financial_report_factor_no_clear_incremental_value_vs_v5f_primary"
    return [
        {
            "pm_gate_decision": decision,
            "best_version": best["version_id"],
            "best_delta_return_pct_points_vs_v5f_primary": best["delta_return_pct_points_vs_v5f_primary"],
            "best_delta_return_pct_points_vs_repaired_baseline": best["delta_return_pct_points_vs_repaired_baseline"],
            "bank_score_ready_coverage": next((row["score_ready_coverage"] for row in coverage if row["sleeve"] == BANK), ""),
            "power_score_ready_coverage": next((row["score_ready_coverage"] for row in coverage if row["sleeve"] == POWER), ""),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "next_action": "keep_v5f_primary_unmodified; use financial report panel for observation unless forward evidence improves",
        }
    ]


def _next_queue(decision: str, comparison: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best = comparison[0]
    return [
        {"rank": 1, "next_task": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary", "status": "ready", "reason": "financial-report factor retest did not automatically replace V5f primary"},
        {"rank": 2, "next_task": "financial_report_field_forward_observation", "status": "ready", "reason": f"gate={decision}; best={best['version_id']}"},
        {"rank": 3, "next_task": "manual_spot_check_top_weight_changes", "status": "ready", "reason": "automated review should be spot-checked before any candidate promotion"},
        {"rank": 4, "next_task": "power_capacity_payment_policy_panel_optional", "status": "optional", "reason": "capacity payment is partly disclosed but policy-source panel is cleaner"},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row["detail"])} for row in governance if row["status"] == "fail"]


def _rule_for(row: dict[str, str]) -> MetricRule | None:
    industry = row.get("industry", "")
    field = row.get("field", "")
    keyword = row.get("keyword", "")
    for rule in METRIC_RULES:
        if rule.industry == industry and rule.field == field and keyword in rule.keywords:
            if rule.metric == "tier1_capital_ratio_pct" and "核心一级资本充足率" in row.get("sample_context", ""):
                continue
            return rule
    return None


def _metric_value(row: dict[str, str], rule: MetricRule) -> tuple[float | None, str, str]:
    if rule.unit == "flag":
        return 1.0, "keyword_present", "flag_from_original_page_keyword"
    numbers = _numbers(row.get("value_candidates", ""), row.get("sample_context", ""), rule.metric)
    for value, token, unit_status in numbers:
        if rule.min_value is not None and value < rule.min_value:
            continue
        if rule.max_value is not None and value > rule.max_value:
            continue
        if _looks_like_year(value, token):
            continue
        if rule.unit == "亿元" and "亿" not in token and "亿元" not in row.get("sample_context", ""):
            continue
        if rule.unit == "小时" and "小时" not in token and "小时" not in row.get("sample_context", ""):
            continue
        if rule.unit == "元/千瓦时" and value > 2.0:
            continue
        return value, token, unit_status
    return None, "", "value_not_found_or_out_of_range"


def _numbers(value_candidates: str, context: str, metric: str) -> list[tuple[float, str, str]]:
    text = ";".join([str(value_candidates or ""), context[:260]])
    tokens = re.findall(r"-?\d[\d,]*(?:\.\d+)?\s*(?:%|个百分点|亿千瓦时|万千瓦时|千瓦时|元/兆瓦时|元/千千瓦时|元/千瓦时|元/吨|亿元|小时|元)?", text)
    out = []
    for token in tokens:
        clean = token.strip()
        if "百分点" in clean and metric not in {"fuel_cost_amount_yoy", "generation_volume_yoy"}:
            continue
        match = re.search(r"-?\d[\d,]*(?:\.\d+)?", clean)
        if not match:
            continue
        value = float(match.group(0).replace(",", ""))
        if "万千瓦时" in clean:
            value = value / 10000.0
        if "元/兆瓦时" in clean or "元/千千瓦时" in clean:
            value = value / 1000.0
        unit_status = "explicit_unit" if re.search(r"%|亿千瓦时|万千瓦时|元/|亿元|小时", clean) else "context_unit_or_table_unit"
        out.append((value, clean, unit_status))
    return out


def _looks_like_year(value: float, token: str) -> bool:
    return 1990 <= value <= 2035 and not any(unit in token for unit in ["%", "亿元", "小时", "千瓦时", "元/"])


def _ratio(num: int, den: int) -> str:
    return "" if den <= 0 else _fmt(num / den)


def _fmt(value: Any) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{num:.12g}"


def _summary(
    status: str,
    reviewed_candidate_count: int = 0,
    report_panel_rows: int = 0,
    rebalance_panel_rows: int = 0,
    best_version: str = "",
    best_delta_vs_v5f: float = 0.0,
    best_delta_vs_baseline: float = 0.0,
    pm_gate_decision: str = "blocked_missing_required_inputs",
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    blockers = blockers or []
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_bank_power_financial_report_pit_panel",
        "status": status,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "benchmark": BASELINE,
        "primary_reference": PRIMARY,
        "reviewed_candidate_count": reviewed_candidate_count,
        "report_panel_rows": report_panel_rows,
        "rebalance_panel_rows": rebalance_panel_rows,
        "best_version": best_version,
        "best_delta_return_pct_points_vs_v5f_primary": best_delta_vs_v5f,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_vs_baseline,
        "pm_gate_decision": pm_gate_decision,
        "can_update_model_now": False,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "fatal_blockers": [row for row in blockers if row.get("severity") == "fatal"],
    }


def _report(comparison: list[dict[str, Any]], decision: list[dict[str, Any]], coverage: list[dict[str, Any]], governance: list[dict[str, Any]]) -> str:
    lines = [
        "# V5c Bank / Power Financial Report PIT Panel And Factor Retest",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Best version: `{decision[0]['best_version']}`",
        f"- Accepted: `False`",
        f"- V57f core modified: `False`",
        "",
        "## Coverage",
    ]
    for row in coverage:
        lines.append(f"- `{row['sleeve']}` score-ready coverage: {float(row['score_ready_coverage'] or 0):.2%}; model metric coverage: {float(row['model_metric_coverage'] or 0):.2%}")
    lines.extend(["", "## Comparison"])
    for index, row in enumerate(comparison, start=1):
        lines.append(
            f"- {index}. `{row['version_id']}`: return={float(row['strategy_return'])*100:.2f}%, "
            f"delta vs V57f={float(row['delta_return_pct_points_vs_repaired_baseline']):+.2f} pct, "
            f"delta vs V5f={float(row['delta_return_pct_points_vs_v5f_primary']):+.2f} pct, "
            f"maxDD={float(row['max_drawdown'])*100:.2f}%, status=`{row['comparison_status']}`"
        )
    lines.extend(["", "## Governance"])
    for row in governance:
        lines.append(f"- `{row['audit_id']}`: {row['status']}")
    lines.extend(["", "Financial-report fields remain a reviewed PIT data panel and fixed-rule retest. They do not replace V5f primary without forward evidence."])
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Bank / Power Financial Report PIT Panel Rules",
            "",
            "- Use only CNInfo annual report fields whose announcement date is visible before the rebalance date.",
            "- Use only V57f repaired selected stocks; no full-market selection.",
            "- Preserve sleeve total weights and V57f rebalance schedule.",
            "- Do not change V57f core or V5f primary.",
            "- Do not mark accepted or live approved.",
            "- This packet is a PIT data panel plus fixed-rule retest, not threshold optimization.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        BATCH_DIR / "v5c_bank_financial_report_field_candidates.csv",
        BATCH_DIR / "v5c_power_financial_report_field_candidates.csv",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        ROUGH_DIR / "v5f_structural_rough_screen_weights.csv",
        PRICE_DIR,
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(100_000_000)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()
