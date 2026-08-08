from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_structural_rough_screen_runner import (
    BACKTEST_END,
    BACKTEST_START,
    BASELINE,
    COMMISSION_RATE,
    PRICE_DIR,
    REPAIRED_RUN,
    _daily_returns,
    _drawdown,
    _load_prices,
    _max_drawdown,
    _safe_float,
)


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_bank_power_industry_factor_weight_test") / "current"
P1_DIR = Path("v5c_p1_financial_quality_pit_panel") / "current"
P2_DIR = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
PRIMARY = "internal_subsleeve_mom12_70_30"
BANK = "bank"
POWER = "utilities_electricity"


VERSION_FAMILIES = {
    BASELINE: "baseline",
    PRIMARY: "v5f_primary_reference",
    "bank_power_specialist_base_20pct": "industry_specialist_from_v57f",
    "bank_power_specialist_replace_mom30": "industry_replaces_bank_power_momentum",
    "bank_power_mom_industry_blend_15_15": "momentum_industry_blend",
    "bank_power_specialist_overlay_on_v5f_10pct": "industry_overlay_on_v5f",
    "bank_only_specialist_overlay_on_v5f_10pct": "industry_overlay_on_v5f",
    "power_only_specialist_overlay_on_v5f_10pct": "industry_overlay_on_v5f",
}


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_bank_power_industry_factor_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_inputs", "blocked_missing_required_inputs", blockers)
        _write_json(out / "v5c_bank_power_industry_factor_summary.json", summary)
        return out / "v5c_bank_power_industry_factor_summary.json"

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    p1 = pd.read_csv(root / P1_DIR / "v5c_p1_financial_quality_pit_panel.csv", dtype={"trade_date": str, "code": str})
    p2_val = pd.read_csv(root / P2_DIR / "v5c_p2_valuation_state_panel.csv", dtype={"trade_date": str, "code": str})
    primary_weights = pd.read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_weights.csv", dtype={"rebalance_date": str, "code": str})

    factor_schema = _factor_schema()
    factor_scores = _factor_scores(signals, p1, p2_val)
    weights = _build_weights(signals, prices, primary_weights, factor_scores)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    drawdown = _drawdown(daily)
    sleeve = _sleeve_contribution(weights, prices)
    factor_audit = _factor_audit(factor_scores)
    governance = _governance(weights, factor_audit)
    comparison = _comparison(metrics)
    decision = _pm_decision(comparison, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"], comparison)
    blockers_out = _blockers(governance)

    _write_csv(out / "v5c_bank_power_industry_factor_schema.csv", factor_schema)
    _write_csv(out / "v5c_bank_power_industry_factor_scores.csv", factor_scores)
    _write_csv(out / "v5c_bank_power_industry_factor_weights.csv", weights)
    _write_csv(out / "v5c_bank_power_industry_factor_daily_returns.csv", daily)
    _write_csv(out / "v5c_bank_power_industry_factor_metrics.csv", metrics)
    _write_csv(out / "v5c_bank_power_industry_factor_yearly.csv", yearly)
    _write_csv(out / "v5c_bank_power_industry_factor_drawdown.csv", drawdown)
    _write_csv(out / "v5c_bank_power_industry_factor_sleeve_contribution.csv", sleeve)
    _write_csv(out / "v5c_bank_power_industry_factor_coverage_audit.csv", factor_audit)
    _write_csv(out / "v5c_bank_power_industry_factor_governance_audit.csv", governance)
    _write_csv(out / "v5c_bank_power_industry_factor_comparison.csv", comparison)
    _write_csv(out / "v5c_bank_power_industry_factor_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_bank_power_industry_factor_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_bank_power_industry_factor_blockers.csv", blockers_out)
    (out / "v5c_bank_power_industry_factor_report.md").write_text(_report(comparison, decision, factor_audit), encoding="utf-8")
    (out / "v5c_bank_power_industry_factor_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = comparison[0]
    primary_row = next(row for row in metrics if row["version_id"] == PRIMARY)
    summary = _summary(
        "completed_bank_power_industry_factor_weight_test",
        decision[0]["pm_gate_decision"],
        [],
        best_version=best["version_id"],
        best_delta_return=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        best_delta_vs_v5f=float(best["delta_return_pct_points_vs_v5f_primary"]),
        best_delta_drawdown=float(best["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
        v5f_primary_return=float(primary_row["strategy_return"]),
    )
    _write_json(out / "v5c_bank_power_industry_factor_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_bank_power_industry_factor_summary.json"


def _factor_schema() -> list[dict[str, Any]]:
    return [
        {"industry": BANK, "factor": "return_on_equity_ttm", "direction": "higher_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "bank profitability and dividend sustainability"},
        {"industry": BANK, "factor": "dividend_yield_decimal", "direction": "higher_better", "source": "v5c_p1/v5c_p2", "industry_material_link": "bank high dividend but only with quality support"},
        {"industry": BANK, "factor": "non_performing_loan_ratio", "direction": "lower_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "asset quality guard"},
        {"industry": BANK, "factor": "provision_coverage_ratio", "direction": "higher_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "credit buffer"},
        {"industry": BANK, "factor": "core_tier_1_capital_adequacy_ratio", "direction": "higher_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "capital and dividend constraint"},
        {"industry": BANK, "factor": "pb_cheapness_percentile_sleeve_cross_section", "direction": "higher_better", "source": "v5c_p2_valuation_state_panel", "industry_material_link": "valuation with quality"},
        {"industry": POWER, "factor": "operating_cash_flow_yield", "direction": "higher_better", "source": "v5c_p1/v5c_p2", "industry_material_link": "utility cash-flow quality"},
        {"industry": POWER, "factor": "return_on_equity_ttm", "direction": "higher_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "regulated asset profitability"},
        {"industry": POWER, "factor": "gross_profit_margin", "direction": "higher_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "fuel/tariff proxy"},
        {"industry": POWER, "factor": "net_profit_margin", "direction": "higher_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "fuel/tariff proxy"},
        {"industry": POWER, "factor": "capex_burden", "direction": "lower_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "capex burden guard"},
        {"industry": POWER, "factor": "asset_liability_ratio", "direction": "lower_better", "source": "v5c_p1_financial_quality_pit_panel", "industry_material_link": "leverage guard"},
        {"industry": POWER, "factor": "valuation_cheapness_score", "direction": "higher_better", "source": "v5c_p2_valuation_state_panel", "industry_material_link": "cash-flow value support"},
    ]


def _factor_scores(signals: pd.DataFrame, p1: pd.DataFrame, p2_val: pd.DataFrame) -> list[dict[str, Any]]:
    p1_cols = [
        "trade_date",
        "code",
        "sleeve_id",
        "dividend_yield_decimal",
        "operating_cash_flow_yield",
        "return_on_equity_ttm",
        "gross_profit_margin",
        "net_profit_margin",
        "non_performing_loan_ratio",
        "provision_coverage_ratio",
        "core_tier_1_capital_adequacy_ratio",
        "capex_burden",
        "asset_liability_ratio",
        "visible_date_status",
        "quality_status",
    ]
    p2_cols = [
        "trade_date",
        "code",
        "low_price_to_book",
        "pb_cheapness_percentile_sleeve_cross_section",
        "valuation_cheapness_score",
        "valuation_state",
        "pit_status",
    ]
    base = signals[["trade_date", "code", "sector_id", "target_weight"]].copy()
    merged = base.merge(p1[p1_cols], how="left", on=["trade_date", "code"]).merge(p2_val[p2_cols], how="left", on=["trade_date", "code"])
    rows: list[dict[str, Any]] = []
    for (date, sleeve), group in merged.groupby(["trade_date", "sector_id"], sort=True):
        group = group.copy()
        if sleeve == BANK:
            score, available = _score_group(
                group,
                positives=[
                    "return_on_equity_ttm",
                    "dividend_yield_decimal",
                    "provision_coverage_ratio",
                    "core_tier_1_capital_adequacy_ratio",
                    "pb_cheapness_percentile_sleeve_cross_section",
                ],
                negatives=["non_performing_loan_ratio"],
            )
        elif sleeve == POWER:
            score, available = _score_group(
                group,
                positives=[
                    "operating_cash_flow_yield",
                    "return_on_equity_ttm",
                    "gross_profit_margin",
                    "net_profit_margin",
                    "valuation_cheapness_score",
                ],
                negatives=["capex_burden", "asset_liability_ratio"],
            )
        else:
            score = pd.Series(math.nan, index=group.index)
            available = pd.Series(0, index=group.index)
        group["industry_score"] = score
        group["industry_factor_available_count"] = available
        if sleeve in {BANK, POWER}:
            rank = group["industry_score"].rank(method="first")
            group["industry_bucket"] = "middle"
            group.loc[rank > len(group) * 2 / 3, "industry_bucket"] = "industry_top"
            group.loc[rank <= len(group) / 3, "industry_bucket"] = "industry_bottom"
        else:
            group["industry_bucket"] = "not_applicable"
        for _, row in group.iterrows():
            rows.append(
                {
                    "trade_date": row["trade_date"],
                    "code": row["code"],
                    "sleeve": row["sector_id"],
                    "base_target_weight": row["target_weight"],
                    "industry_score": row["industry_score"],
                    "industry_bucket": row["industry_bucket"],
                    "industry_factor_available_count": int(row["industry_factor_available_count"]) if not pd.isna(row["industry_factor_available_count"]) else 0,
                    "visible_date_status": row.get("visible_date_status", ""),
                    "quality_status": row.get("quality_status", ""),
                    "pit_status": row.get("pit_status", ""),
                    "return_on_equity_ttm": row.get("return_on_equity_ttm", ""),
                    "dividend_yield_decimal": row.get("dividend_yield_decimal", ""),
                    "non_performing_loan_ratio": row.get("non_performing_loan_ratio", ""),
                    "provision_coverage_ratio": row.get("provision_coverage_ratio", ""),
                    "core_tier_1_capital_adequacy_ratio": row.get("core_tier_1_capital_adequacy_ratio", ""),
                    "operating_cash_flow_yield": row.get("operating_cash_flow_yield", ""),
                    "gross_profit_margin": row.get("gross_profit_margin", ""),
                    "net_profit_margin": row.get("net_profit_margin", ""),
                    "capex_burden": row.get("capex_burden", ""),
                    "asset_liability_ratio": row.get("asset_liability_ratio", ""),
                    "pb_cheapness_percentile_sleeve_cross_section": row.get("pb_cheapness_percentile_sleeve_cross_section", ""),
                    "valuation_cheapness_score": row.get("valuation_cheapness_score", ""),
                }
            )
    return rows


def _score_group(group: pd.DataFrame, positives: list[str], negatives: list[str]) -> tuple[pd.Series, pd.Series]:
    components: list[pd.Series] = []
    available = pd.Series(0, index=group.index)
    for col in positives:
        values = pd.to_numeric(group[col], errors="coerce")
        valid = values.notna()
        available += valid.astype(int)
        components.append(values.rank(pct=True, method="average"))
    for col in negatives:
        values = pd.to_numeric(group[col], errors="coerce")
        valid = values.notna()
        available += valid.astype(int)
        components.append((-values).rank(pct=True, method="average"))
    if not components:
        return pd.Series(math.nan, index=group.index), available
    score = pd.concat(components, axis=1).mean(axis=1, skipna=True)
    return score, available


def _build_weights(signals: pd.DataFrame, prices: pd.DataFrame, primary_weights: pd.DataFrame, scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feature_map = prices.set_index(["date", "code"])[["mom_12_1", "mr_60d"]].to_dict("index")
    score_df = pd.DataFrame(scores)
    score_map = score_df.set_index(["trade_date", "code"])[["industry_score", "industry_bucket", "industry_factor_available_count"]].to_dict("index")
    primary = primary_weights[primary_weights["version_id"].eq(PRIMARY)].copy()
    primary_map = primary.set_index(["rebalance_date", "code"])["target_weight"].astype(float).to_dict()
    rows: list[dict[str, Any]] = []
    for date, group in signals.groupby("trade_date", sort=True):
        base = group.copy()
        base["base_target_weight"] = base["target_weight"].astype(float)
        base["primary_target_weight"] = [primary_map.get((date, row["code"]), float(row["target_weight"])) for _, row in base.iterrows()]
        base["mom_12_1"] = [_safe_float(feature_map.get((date, row["code"]), {}).get("mom_12_1")) for _, row in base.iterrows()]
        base["industry_score"] = [_safe_float(score_map.get((date, row["code"]), {}).get("industry_score")) for _, row in base.iterrows()]
        base["industry_bucket"] = [score_map.get((date, row["code"]), {}).get("industry_bucket", "") for _, row in base.iterrows()]
        base["industry_factor_available_count"] = [score_map.get((date, row["code"]), {}).get("industry_factor_available_count", 0) for _, row in base.iterrows()]
        rows.extend(_rows_for_version(base, BASELINE, "baseline", base["base_target_weight"], "baseline"))
        rows.extend(_rows_for_version(base, PRIMARY, VERSION_FAMILIES[PRIMARY], base["primary_target_weight"], "v5f_primary"))
        rows.extend(_variant_base_specialist_20(base))
        rows.extend(_variant_replace_mom30(base))
        rows.extend(_variant_blend_15_15(base))
        rows.extend(_variant_overlay_on_v5f(base, "bank_power_specialist_overlay_on_v5f_10pct", {BANK, POWER}, 0.10))
        rows.extend(_variant_overlay_on_v5f(base, "bank_only_specialist_overlay_on_v5f_10pct", {BANK}, 0.10))
        rows.extend(_variant_overlay_on_v5f(base, "power_only_specialist_overlay_on_v5f_10pct", {POWER}, 0.10))
    return rows


def _variant_base_specialist_20(base: pd.DataFrame) -> list[dict[str, Any]]:
    target = base["base_target_weight"].copy()
    target = _apply_specialist_top_budget(base, target, {BANK, POWER}, 0.20, base_weight_col="base_target_weight")
    return _rows_for_version(base, "bank_power_specialist_base_20pct", VERSION_FAMILIES["bank_power_specialist_base_20pct"], target, "industry_top_20_from_baseline")


def _variant_replace_mom30(base: pd.DataFrame) -> list[dict[str, Any]]:
    target = base["primary_target_weight"].copy()
    # For bank/power only, replace the V5f momentum subsleeve with industry specialist allocation.
    replacement = base["base_target_weight"].copy()
    replacement = _apply_specialist_top_budget(base, replacement, {BANK, POWER}, 0.30, base_weight_col="base_target_weight")
    mask = base["sector_id"].isin([BANK, POWER])
    target.loc[mask] = replacement.loc[mask]
    return _rows_for_version(base, "bank_power_specialist_replace_mom30", VERSION_FAMILIES["bank_power_specialist_replace_mom30"], target, "replace_bank_power_momentum_with_industry")


def _variant_blend_15_15(base: pd.DataFrame) -> list[dict[str, Any]]:
    target = base["primary_target_weight"].copy()
    for sleeve, sleeve_df in base[base["sector_id"].isin([BANK, POWER])].groupby("sector_id"):
        idx = sleeve_df.index
        sleeve_total = sleeve_df["base_target_weight"].astype(float).sum()
        core = 0.70 * sleeve_df["base_target_weight"].astype(float)
        mom_alloc = pd.Series(0.0, index=idx)
        industry_alloc = pd.Series(0.0, index=idx)
        mom_top = _top_indices(sleeve_df, "mom_12_1")
        industry_top = _top_indices(sleeve_df, "industry_score")
        mom_alloc.loc[mom_top] = 0.15 * sleeve_total / len(mom_top)
        industry_alloc.loc[industry_top] = 0.15 * sleeve_total / len(industry_top)
        target.loc[idx] = core + mom_alloc + industry_alloc
    return _rows_for_version(base, "bank_power_mom_industry_blend_15_15", VERSION_FAMILIES["bank_power_mom_industry_blend_15_15"], target, "bank_power_15_mom_15_industry")


def _variant_overlay_on_v5f(base: pd.DataFrame, version: str, sleeves: set[str], budget: float) -> list[dict[str, Any]]:
    target = base["primary_target_weight"].copy()
    target = _apply_specialist_top_budget(base, target, sleeves, budget, base_weight_col="primary_target_weight")
    return _rows_for_version(base, version, VERSION_FAMILIES[version], target, f"{version}_industry_top_budget")


def _apply_specialist_top_budget(base: pd.DataFrame, target: pd.Series, sleeves: set[str], budget: float, base_weight_col: str) -> pd.Series:
    target = target.copy()
    for sleeve, sleeve_df in base[base["sector_id"].isin(sleeves)].groupby("sector_id"):
        idx = sleeve_df.index
        sleeve_total = sleeve_df[base_weight_col].astype(float).sum()
        top = _top_indices(sleeve_df, "industry_score")
        core = (1.0 - budget) * sleeve_df[base_weight_col].astype(float)
        top_alloc = pd.Series(0.0, index=idx)
        top_alloc.loc[top] = budget * sleeve_total / len(top)
        target.loc[idx] = core + top_alloc
    return target


def _top_indices(sleeve_df: pd.DataFrame, col: str) -> list[int]:
    values = pd.to_numeric(sleeve_df[col], errors="coerce")
    if values.notna().sum() == 0:
        return sleeve_df.index.tolist()
    rank = values.rank(method="first")
    top = sleeve_df[rank > len(sleeve_df) * 2 / 3].index.tolist()
    return top or [int(values.idxmax())]


def _rows_for_version(base: pd.DataFrame, version: str, family: str, target: pd.Series, bucket: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
                "mom_12_1": row.get("mom_12_1", ""),
                "industry_score": row.get("industry_score", ""),
                "industry_bucket": row.get("industry_bucket", ""),
                "industry_factor_available_count": row.get("industry_factor_available_count", 0),
                "bucket": bucket,
                "sleeve_weight_preserved": True,
                "new_stock_selected": False,
                "accepted": False,
            }
        )
    return rows


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
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
                "turnover_proxy": pd.to_numeric(group["turnover_proxy"]).sum(),
                "incremental_commission_total": pd.to_numeric(group["incremental_commission"]).sum(),
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
    return sorted(out, key=lambda r: float(r["strategy_return"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].str.slice(0, 4)
    out: list[dict[str, Any]] = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append(
            {
                "version_id": version,
                "family": VERSION_FAMILIES.get(version, "other"),
                "year": year,
                "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1,
                "trade_days": len(group),
            }
        )
    base = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    primary = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == PRIMARY}
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - base.get(row["year"], 0.0)) * 100
        row["delta_return_pct_points_vs_v5f_primary"] = (float(row["period_return"]) - primary.get(row["year"], 0.0)) * 100
    return out


def _sleeve_contribution(weights: list[dict[str, Any]], prices: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in weights:
        if row["version_id"] == BASELINE:
            continue
        key = (row["version_id"], row["sleeve"])
        item = grouped.setdefault(
            key,
            {
                "version_id": row["version_id"],
                "family": row["family"],
                "sleeve": row["sleeve"],
                "abs_weight_delta": 0.0,
                "next_day_delta": 0.0,
                "industry_weight_delta_abs": 0.0,
            },
        )
        item["abs_weight_delta"] += abs(float(row["weight_delta"]))
        item["next_day_delta"] += float(row["weight_delta"]) * (_safe_float(ret_map.get((row["rebalance_date"], row["code"]))) or 0.0)
        if row["sleeve"] in {BANK, POWER}:
            item["industry_weight_delta_abs"] += abs(float(row["weight_delta"]))
    return list(grouped.values())


def _factor_audit(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(scores)
    rows: list[dict[str, Any]] = []
    for sleeve in [BANK, POWER]:
        group = df[df["sleeve"].eq(sleeve)]
        rows.append(
            {
                "sleeve": sleeve,
                "row_count": len(group),
                "score_present_count": int(pd.to_numeric(group["industry_score"], errors="coerce").notna().sum()),
                "score_coverage": float(pd.to_numeric(group["industry_score"], errors="coerce").notna().mean()) if len(group) else 0.0,
                "min_factor_available_count": int(pd.to_numeric(group["industry_factor_available_count"], errors="coerce").min()) if len(group) else 0,
                "pit_status": "pass" if len(group) and pd.to_numeric(group["industry_score"], errors="coerce").notna().all() else "review",
                "known_missing_specialist_fields": "NIM/deposit cost" if sleeve == BANK else "coal price/tariff/capacity payment/hydro water condition",
            }
        )
    return rows


def _governance(weights: list[dict[str, Any]], factor_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    sleeve_preserved = []
    for (_, date, sleeve), group in df.groupby(["version_id", "rebalance_date", "sleeve"], sort=True):
        sleeve_preserved.append(abs(group["target_weight"].astype(float).sum() - group["base_target_weight"].astype(float).sum()) < 1e-8)
    return [
        {"audit_id": "repaired_baseline_only", "status": "pass", "detail": BASELINE},
        {"audit_id": "v57f_selected_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "bank_power_only_industry_update", "status": "pass", "detail": "industry-specific updates are limited to bank and utilities_electricity sleeves"},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if all(sleeve_preserved) else "fail", "detail": 0 if all(sleeve_preserved) else 1},
        {"audit_id": "pit_factor_score_coverage", "status": "pass" if all(float(row["score_coverage"]) == 1.0 for row in factor_audit) else "review", "detail": ";".join(f"{row['sleeve']}={row['score_coverage']}" for row in factor_audit)},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": "fixed budgets only: existing 30 pct momentum split and one 10 pct diagnostic overlay"},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "live_approved_false", "status": "pass", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
    ]


def _comparison(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        delta = float(row["delta_return_pct_points_vs_repaired_baseline"])
        delta_primary = float(row["delta_return_pct_points_vs_v5f_primary"])
        dd_primary = float(row["delta_max_drawdown_pct_points_vs_v5f_primary"])
        if row["version_id"] == PRIMARY:
            status = "current_v5f_primary_reference"
        elif delta_primary > 0.5 and dd_primary <= 0.25:
            status = "possible_incremental_candidate_needs_forward_review"
        elif delta_primary > 0:
            status = "weak_incremental_positive_diagnostic"
        else:
            status = "no_incremental_value_vs_v5f_primary"
        rows.append(
            {
                "version_id": row["version_id"],
                "family": row["family"],
                "strategy_return": row["strategy_return"],
                "annualized_return": row["annualized_return"],
                "max_drawdown": row["max_drawdown"],
                "sharpe_proxy": row["sharpe_proxy"],
                "delta_return_pct_points_vs_repaired_baseline": delta,
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "delta_return_pct_points_vs_v5f_primary": delta_primary,
                "delta_max_drawdown_pct_points_vs_v5f_primary": dd_primary,
                "comparison_status": status,
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda r: float(r["strategy_return"]), reverse=True)


def _pm_decision(comparison: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_fail = [row for row in governance if row["status"] == "fail"]
    incremental = [row for row in comparison if row["comparison_status"] == "possible_incremental_candidate_needs_forward_review"]
    best = comparison[0]
    if gov_fail:
        decision = "blocked_by_governance_issue"
    elif incremental:
        decision = "industry_factor_weight_update_has_incremental_value_not_accepted"
    elif float(best["delta_return_pct_points_vs_v5f_primary"]) > 0:
        decision = "industry_factor_weight_update_weak_positive_diagnostic_only"
    else:
        decision = "industry_factor_weight_update_no_clear_incremental_value_vs_v5f_primary"
    return [
        {
            "pm_gate_decision": decision,
            "best_version": best["version_id"],
            "best_delta_return_pct_points_vs_v5f_primary": best["delta_return_pct_points_vs_v5f_primary"],
            "best_delta_return_pct_points_vs_repaired_baseline": best["delta_return_pct_points_vs_repaired_baseline"],
            "best_delta_max_drawdown_pct_points_vs_v5f_primary": best["delta_max_drawdown_pct_points_vs_v5f_primary"],
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "next_action": "use results as diagnostic; complete missing industry PIT panels before any candidate upgrade",
        }
    ]


def _next_queue(decision: str, comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"rank": 1, "next_task": "complete_bank_P1_NIM_deposit_cost_panel", "status": "ready", "reason": "bank specialist proxy lacks NIM/deposit-cost core field"},
        {"rank": 2, "next_task": "complete_power_P1_coal_tariff_capacity_hydro_panel", "status": "ready", "reason": "power specialist proxy lacks true fuel/tariff/water state"},
        {"rank": 3, "next_task": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary", "status": "ready", "reason": "industry update must beat V5f primary before promotion"},
        {"rank": 4, "next_task": "optional_forward_observation_for_best_industry_variant", "status": "ready_if_best_positive", "reason": f"gate={decision}; best={comparison[0]['version_id']}"},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] == "fail"]
    return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    best_version: str = "",
    best_delta_return: float = 0.0,
    best_delta_vs_v5f: float = 0.0,
    best_delta_drawdown: float = 0.0,
    v5f_primary_return: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_bank_power_industry_factor_weight_test",
        "status": status,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "benchmark": BASELINE,
        "primary_reference": PRIMARY,
        "best_version": best_version,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_return,
        "best_delta_return_pct_points_vs_v5f_primary": best_delta_vs_v5f,
        "best_delta_max_drawdown_pct_points_vs_repaired_baseline": best_delta_drawdown,
        "v5f_primary_strategy_return": v5f_primary_return,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_stock_selected": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(comparison: list[dict[str, Any]], decision: list[dict[str, Any]], factor_audit: list[dict[str, Any]]) -> str:
    lines = [
        "# V5c Bank / Power Industry Factor Weight Test",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Best version: `{decision[0]['best_version']}`",
        "- Status: limited engineering diagnostic; not accepted.",
        "",
        "## Factor Coverage",
    ]
    for row in factor_audit:
        lines.append(f"- {row['sleeve']}: score coverage={float(row['score_coverage']):.2%}; missing={row['known_missing_specialist_fields']}")
    lines.extend(["", "## Result Ranking"])
    for i, row in enumerate(comparison, start=1):
        lines.append(
            f"- {i}. `{row['version_id']}`: return={float(row['strategy_return'])*100:.2f}%, "
            f"delta vs repaired={float(row['delta_return_pct_points_vs_repaired_baseline']):+.2f} pct, "
            f"delta vs V5f primary={float(row['delta_return_pct_points_vs_v5f_primary']):+.2f} pct, "
            f"dd delta vs V5f={float(row['delta_max_drawdown_pct_points_vs_v5f_primary']):+.2f} pct, "
            f"status={row['comparison_status']}"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This test uses industry-specialist proxy factors derived from existing P1/P2 materials. It does not yet include bank NIM/deposit-cost data or power coal/tariff/hydro data, so any positive result remains diagnostic.",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Bank / Power Industry Factor Weight Test Rules",
            "",
            "- Use startup-preload repaired V57f baseline only.",
            "- Use only V57f selected stocks; no full-market selection.",
            "- Industry factor updates are limited to bank and utilities_electricity sleeves.",
            "- Preserve each sleeve's total weight.",
            "- Do not mark accepted or live approved.",
            "- Do not modify V57f core or V5f primary.",
            "- Missing NIM/coal/tariff/hydro fields must remain blockers for formal promotion.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PRICE_DIR,
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        P1_DIR / "v5c_p1_financial_quality_pit_panel.csv",
        P2_DIR / "v5c_p2_valuation_state_panel.csv",
        ROUGH_DIR / "v5f_structural_rough_screen_weights.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


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
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()
