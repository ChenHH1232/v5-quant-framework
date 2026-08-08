from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_cross_sector_pre2021_factor_screen") / "current"
SPLIT_DIR = Path("v5_sample_split_governance_correction") / "current"
PREVIEW_DIR = Path("v5f_pre2021_repaired_multisleeve_data_gate") / "current"
TRAIN_START = "2013-01-01"
TRAIN_END = "2021-04-30"
FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"


@dataclass(frozen=True)
class SectorPanelSpec:
    sector_id: str
    panel_path: Path
    panel_scope: str


@dataclass(frozen=True)
class FactorSpec:
    sector_id: str
    factor_id: str
    column: str
    direction: str
    family: str
    rationale: str


SECTOR_SPECS: tuple[SectorPanelSpec, ...] = (
    SectorPanelSpec(
        "utilities_electricity",
        Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_panels_v5" / "utilities_v51f" / "panel_with_low_vol.csv",
        "startup_repaired_panel_pre2021",
    ),
    SectorPanelSpec(
        "highway_infrastructure",
        Path("\u6570\u636e\u5e93") / "processed" / "pre2021_repaired_factor_panels_v5" / "highway_v54h" / "strict_pit_panel_with_low_vol.csv",
        "strict_pit_panel_pre2021",
    ),
    SectorPanelSpec(
        "port_rail_infrastructure",
        Path("\u6570\u636e\u5e93") / "processed" / "pre2021_repaired_factor_panels_v5" / "port_rail_v55j" / "strict_pit_panel_with_low_vol.csv",
        "strict_pit_panel_pre2021",
    ),
)


FACTOR_SPECS: tuple[FactorSpec, ...] = (
    FactorSpec("utilities_electricity", "utilities_low_pb", "low_price_to_book", "lower_better", "valuation", "Lower PB within electricity utilities."),
    FactorSpec("utilities_electricity", "utilities_dividend_yield", "dividend_yield", "higher_better", "dividend", "Dividend yield support."),
    FactorSpec("utilities_electricity", "utilities_ocf_yield", "operating_cash_flow_yield", "higher_better", "cashflow", "Operating cash-flow yield."),
    FactorSpec("utilities_electricity", "utilities_roe", "return_on_equity_ttm", "higher_better", "quality", "ROE quality."),
    FactorSpec("utilities_electricity", "utilities_gross_margin", "gross_profit_margin", "higher_better", "quality", "Gross margin."),
    FactorSpec("utilities_electricity", "utilities_net_margin", "net_profit_margin", "higher_better", "quality", "Net margin."),
    FactorSpec("utilities_electricity", "utilities_cash_conversion", "operating_cash_flow_to_net_profit", "higher_better", "cashflow_quality", "Cash conversion quality."),
    FactorSpec("utilities_electricity", "utilities_interest_coverage", "interest_coverage", "higher_better", "balance_sheet", "Debt service cushion."),
    FactorSpec("utilities_electricity", "utilities_capex_burden", "capex_burden", "lower_better", "capex", "Lower capex burden."),
    FactorSpec("utilities_electricity", "utilities_asset_liability", "asset_liability_ratio", "lower_better", "balance_sheet", "Lower leverage."),
    FactorSpec("utilities_electricity", "utilities_cashflow_subindustry_score", "cashflow_yield_subindustry_score", "higher_better", "existing_industry_score", "Existing subindustry cash-flow score."),
    FactorSpec("utilities_electricity", "utilities_low_pb_subindustry_score", "low_pb_subindustry_score", "higher_better", "existing_industry_score", "Existing subindustry valuation score."),
    FactorSpec("utilities_electricity", "utilities_dividend_cashflow_support_score", "dividend_cashflow_support_score", "higher_better", "existing_industry_score", "Existing dividend and cash-flow support score."),
    FactorSpec("utilities_electricity", "utilities_capex_control_score", "capex_control_score", "higher_better", "existing_industry_score", "Existing capex-control score."),
    FactorSpec("utilities_electricity", "utilities_leverage_control_score", "leverage_control_score", "higher_better", "existing_industry_score", "Existing leverage-control score."),
    FactorSpec("utilities_electricity", "utilities_volatility_120d", "volatility_120d", "lower_better", "low_vol", "Lower 120d volatility."),
    FactorSpec("utilities_electricity", "utilities_max_drawdown_120d", "max_drawdown_120d", "lower_better", "low_vol", "Lower 120d drawdown."),
    FactorSpec("utilities_electricity", "utilities_low_vol_score", "low_vol_score", "higher_better", "low_vol", "Higher low-vol score."),
    FactorSpec("highway_infrastructure", "highway_low_pb", "low_price_to_book", "lower_better", "valuation", "Lower PB within highway."),
    FactorSpec("highway_infrastructure", "highway_dividend_yield", "dividend_yield", "higher_better", "dividend", "Dividend yield support."),
    FactorSpec("highway_infrastructure", "highway_pcf_inverse", "pcf_ncf_ttm_inverse_proxy", "higher_better", "cashflow", "Net cash-flow valuation inverse proxy."),
    FactorSpec("highway_infrastructure", "highway_dividend_cash_per_share", "dividend_cash_per_share_used", "higher_better", "dividend", "Cash dividend per share."),
    FactorSpec("highway_infrastructure", "highway_volatility_120d", "volatility_120d", "lower_better", "low_vol", "Lower 120d volatility."),
    FactorSpec("highway_infrastructure", "highway_max_drawdown_120d", "max_drawdown_120d", "lower_better", "low_vol", "Lower 120d drawdown."),
    FactorSpec("highway_infrastructure", "highway_low_vol_score", "low_vol_score", "higher_better", "low_vol", "Higher low-vol score."),
    FactorSpec("port_rail_infrastructure", "port_rail_low_pb", "low_price_to_book", "lower_better", "valuation", "Lower PB within port/rail."),
    FactorSpec("port_rail_infrastructure", "port_rail_dividend_yield", "dividend_yield", "higher_better", "dividend", "Dividend yield support."),
    FactorSpec("port_rail_infrastructure", "port_rail_pcf_inverse", "pcf_ncf_ttm_inverse_proxy", "higher_better", "cashflow", "Net cash-flow valuation inverse proxy."),
    FactorSpec("port_rail_infrastructure", "port_rail_dividend_cash_per_share", "dividend_cash_per_share_used", "higher_better", "dividend", "Cash dividend per share."),
    FactorSpec("port_rail_infrastructure", "port_rail_volatility_120d", "volatility_120d", "lower_better", "low_vol", "Lower 120d volatility."),
    FactorSpec("port_rail_infrastructure", "port_rail_max_drawdown_120d", "max_drawdown_120d", "lower_better", "low_vol", "Lower 120d drawdown."),
    FactorSpec("port_rail_infrastructure", "port_rail_low_vol_score", "low_vol_score", "higher_better", "low_vol", "Higher low-vol score."),
)


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_cross_sector_pre2021_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_inputs", "blocked_missing_required_inputs", blockers=blockers)
        _write_json(out / "v5c_cross_sector_pre2021_summary.json", summary)
        return out / "v5c_cross_sector_pre2021_summary.json"

    panels = _load_panels(root)
    preview = pd.read_csv(root / PREVIEW_DIR / "v5f_pre2021_candidate_signal_preview.csv", dtype=str)
    schema = _schema(panels)
    train_bucket = _bucket_results(panels, "sector_train_test_pre2021")
    train_overlay = _overlay_results(panels, "sector_train_test_pre2021")
    strict_panels = _strict_preview_panels(panels, preview)
    strict_bucket = _bucket_results(strict_panels, "strict_multisleeve_preview_sector_subset")
    strict_overlay = _overlay_results(strict_panels, "strict_multisleeve_preview_sector_subset")
    comparison = _comparison(train_overlay, strict_overlay, train_bucket, strict_bucket)
    coverage = _coverage(panels, strict_panels, schema)
    governance = _governance(panels, strict_panels)
    decision = _pm_decision(comparison, governance)
    queue = _next_queue(comparison, decision)
    blockers_out = _blockers(governance, coverage)

    _write_csv(out / "v5c_cross_sector_pre2021_factor_schema.csv", schema)
    _write_csv(out / "v5c_cross_sector_pre2021_train_bucket_result.csv", train_bucket)
    _write_csv(out / "v5c_cross_sector_pre2021_train_overlay_result.csv", train_overlay)
    _write_csv(out / "v5c_cross_sector_pre2021_strict_preview_bucket_result.csv", strict_bucket)
    _write_csv(out / "v5c_cross_sector_pre2021_strict_preview_overlay_result.csv", strict_overlay)
    _write_csv(out / "v5c_cross_sector_pre2021_factor_comparison.csv", comparison)
    _write_csv(out / "v5c_cross_sector_pre2021_coverage_audit.csv", coverage)
    _write_csv(out / "v5c_cross_sector_pre2021_governance_audit.csv", governance)
    _write_csv(out / "v5c_cross_sector_pre2021_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_cross_sector_pre2021_next_queue.csv", queue)
    _write_csv(out / "v5c_cross_sector_pre2021_blockers.csv", blockers_out)
    (out / "v5c_cross_sector_pre2021_report.md").write_text(_report(comparison, coverage, decision), encoding="utf-8")
    (out / "v5c_cross_sector_pre2021_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = comparison[0] if comparison else {}
    summary = _summary(
        "completed_cross_sector_pre2021_factor_screen",
        decision[0]["pm_gate_decision"],
        best_factor=best.get("factor_id", ""),
        best_sector=best.get("sector_id", ""),
        best_train=float(best.get("train_delta_pct_points", 0.0) or 0.0),
        best_strict=float(best.get("strict_delta_pct_points", 0.0) or 0.0),
        deep_research_count=sum(1 for row in comparison if row.get("screen_status") == "pre2021_supported_deep_research_candidate_not_accepted"),
        blockers=blockers_out,
    )
    _write_json(out / "v5c_cross_sector_pre2021_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_cross_sector_pre2021_summary.json"


def _load_panels(root: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    spec_map = {spec.sector_id: spec for spec in SECTOR_SPECS}
    for spec in SECTOR_SPECS:
        df = pd.read_csv(root / spec.panel_path, dtype={"trade_date": str, "code": str})
        df = df[(df["trade_date"] >= TRAIN_START) & (df["trade_date"] <= TRAIN_END)].copy()
        if df.empty:
            continue
        df["sector_id"] = spec.sector_id
        df["panel_scope"] = spec.panel_scope
        df["future_return"] = pd.to_numeric(df.get("future_return"), errors="coerce")
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def _schema(panels: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in FACTOR_SPECS:
        sector = panels[panels["sector_id"].eq(spec.sector_id)]
        values = pd.to_numeric(sector.get(spec.column), errors="coerce") if spec.column in sector.columns else pd.Series(dtype=float)
        usable = sector[values.notna() & pd.to_numeric(sector.get("future_return"), errors="coerce").notna()] if len(sector) else pd.DataFrame()
        rows.append(
            {
                "sector_id": spec.sector_id,
                "factor_id": spec.factor_id,
                "source_column": spec.column,
                "direction": spec.direction,
                "family": spec.family,
                "row_count": len(sector),
                "available_row_count": int(values.notna().sum()),
                "usable_row_count": len(usable),
                "date_count": int(sector["trade_date"].nunique()) if len(sector) else 0,
                "usable_date_count": int(usable["trade_date"].nunique()) if len(usable) else 0,
                "coverage": float(values.notna().mean()) if len(sector) else 0.0,
                "test_scope": "fixed_single_factor_10pct_overlay_pre2021_train_test",
                "rationale": spec.rationale,
                "accepted": False,
            }
        )
    return rows


def _bucket_results(panels: pd.DataFrame, scope: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if panels.empty:
        return rows
    for spec in FACTOR_SPECS:
        if spec.column not in panels.columns:
            continue
        sector = panels[panels["sector_id"].eq(spec.sector_id)].copy()
        sector["factor_value"] = pd.to_numeric(sector[spec.column], errors="coerce")
        sector["future_return_num"] = pd.to_numeric(sector["future_return"], errors="coerce")
        for date, group in sector.groupby("trade_date", sort=True):
            valid = _valid_factor_group(group, spec)
            if len(valid) < 3:
                continue
            valid = _assign_buckets(valid)
            for bucket, bucket_df in valid.groupby("bucket", sort=True):
                rows.append(
                    {
                        "scope": scope,
                        "sector_id": spec.sector_id,
                        "factor_id": spec.factor_id,
                        "trade_date": date,
                        "bucket": bucket,
                        "stock_count": len(bucket_df),
                        "avg_factor_value": bucket_df["factor_value"].mean(),
                        "avg_forward_period_return": bucket_df["future_return_num"].mean(),
                        "accepted": False,
                    }
                )
            top = valid[valid["bucket"].eq("top")]
            bottom = valid[valid["bucket"].eq("bottom")]
            if len(top) and len(bottom):
                rows.append(
                    {
                        "scope": scope,
                        "sector_id": spec.sector_id,
                        "factor_id": spec.factor_id,
                        "trade_date": date,
                        "bucket": "top_minus_bottom",
                        "stock_count": len(top) + len(bottom),
                        "avg_factor_value": top["factor_value"].mean() - bottom["factor_value"].mean(),
                        "avg_forward_period_return": top["future_return_num"].mean() - bottom["future_return_num"].mean(),
                        "accepted": False,
                    }
                )
    return rows


def _overlay_results(panels: pd.DataFrame, scope: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if panels.empty:
        return rows
    for spec in FACTOR_SPECS:
        if spec.column not in panels.columns:
            continue
        sector = panels[panels["sector_id"].eq(spec.sector_id)].copy()
        sector["factor_value"] = pd.to_numeric(sector[spec.column], errors="coerce")
        sector["future_return_num"] = pd.to_numeric(sector["future_return"], errors="coerce")
        periods: list[dict[str, Any]] = []
        for date, group in sector.groupby("trade_date", sort=True):
            valid = _valid_factor_group(group, spec)
            if len(valid) < 3:
                continue
            valid = _assign_buckets(valid)
            top = valid[valid["bucket"].eq("top")]
            equal_return = valid["future_return_num"].mean()
            top_return = top["future_return_num"].mean()
            overlay_return = 0.90 * equal_return + 0.10 * top_return
            periods.append(
                {
                    "trade_date": date,
                    "valid_stock_count": len(valid),
                    "top_stock_count": len(top),
                    "equal_weight_period_return": equal_return,
                    "overlay_period_return": overlay_return,
                    "delta_period_return": overlay_return - equal_return,
                }
            )
        if not periods:
            continue
        equal_nav = _compound(row["equal_weight_period_return"] for row in periods)
        overlay_nav = _compound(row["overlay_period_return"] for row in periods)
        deltas = [row["delta_period_return"] for row in periods]
        rows.append(
            {
                "scope": scope,
                "sector_id": spec.sector_id,
                "factor_id": spec.factor_id,
                "source_column": spec.column,
                "direction": spec.direction,
                "family": spec.family,
                "period_count": len(periods),
                "avg_valid_stock_count": sum(row["valid_stock_count"] for row in periods) / len(periods),
                "equal_weight_cumulative_return": equal_nav - 1.0,
                "overlay_cumulative_return": overlay_nav - 1.0,
                "delta_cumulative_return_pct_points_vs_equal_weight": (overlay_nav - equal_nav) * 100,
                "avg_period_delta_return": sum(deltas) / len(deltas),
                "positive_delta_period_rate": sum(1 for value in deltas if value > 0) / len(deltas),
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda row: float(row["delta_cumulative_return_pct_points_vs_equal_weight"]), reverse=True)


def _valid_factor_group(group: pd.DataFrame, spec: FactorSpec) -> pd.DataFrame:
    valid = group[group["factor_value"].notna() & group["future_return_num"].notna()].copy()
    valid = valid[valid["future_return_num"].between(-0.95, 3.0)]
    if spec.column in {"pe_ratio", "pcf_ncf_ttm"}:
        valid = valid[valid["factor_value"] > 0]
    valid["score"] = valid["factor_value"] if spec.direction == "higher_better" else -valid["factor_value"]
    return valid


def _assign_buckets(valid: pd.DataFrame) -> pd.DataFrame:
    valid = valid.copy()
    valid["rank"] = valid["score"].rank(method="first")
    valid["bucket"] = "middle"
    valid.loc[valid["rank"] > len(valid) * 2 / 3, "bucket"] = "top"
    valid.loc[valid["rank"] <= len(valid) / 3, "bucket"] = "bottom"
    return valid


def _strict_preview_panels(panels: pd.DataFrame, preview: pd.DataFrame) -> pd.DataFrame:
    if panels.empty:
        return panels
    p = preview.rename(columns={"preview_date": "trade_date"}).copy()
    p = p[p["sector_id"].isin({spec.sector_id for spec in SECTOR_SPECS})]
    keep = p[["trade_date", "code", "sector_id"]].drop_duplicates()
    merged = keep.merge(panels, on=["trade_date", "code", "sector_id"], how="left")
    merged["panel_scope"] = merged.get("panel_scope", "").fillna("strict_preview_missing_panel")
    return merged


def _comparison(
    train_overlay: list[dict[str, Any]],
    strict_overlay: list[dict[str, Any]],
    train_bucket: list[dict[str, Any]],
    strict_bucket: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    strict_map = {(row["sector_id"], row["factor_id"]): row for row in strict_overlay}
    train_spread = _spread_stats(train_bucket)
    strict_spread = _spread_stats(strict_bucket)
    rows: list[dict[str, Any]] = []
    for row in train_overlay:
        key = (row["sector_id"], row["factor_id"])
        strict = strict_map.get(key, {})
        train_delta = float(row["delta_cumulative_return_pct_points_vs_equal_weight"])
        train_rate = float(row["positive_delta_period_rate"])
        strict_delta = _safe_float(strict.get("delta_cumulative_return_pct_points_vs_equal_weight"))
        strict_rate = _safe_float(strict.get("positive_delta_period_rate"))
        strict_periods = int(strict.get("period_count", 0) or 0)
        if train_delta >= 0.5 and train_rate >= 0.55 and strict_delta is not None and strict_delta > 0 and strict_periods >= 2:
            status = "pre2021_supported_deep_research_candidate_not_accepted"
        elif train_delta >= 0.5 and train_rate >= 0.55:
            status = "train_positive_strict_not_confirmed_diagnostic"
        elif train_delta > 0:
            status = "weak_train_positive_diagnostic"
        else:
            status = "no_pre2021_incremental_signal"
        rows.append(
            {
                "sector_id": row["sector_id"],
                "factor_id": row["factor_id"],
                "family": row["family"],
                "source_column": row["source_column"],
                "direction": row["direction"],
                "train_delta_pct_points": train_delta,
                "train_positive_delta_period_rate": train_rate,
                "train_period_count": row["period_count"],
                "train_avg_top_minus_bottom_return": train_spread.get(key, {}).get("avg_spread_return", ""),
                "train_positive_spread_rate": train_spread.get(key, {}).get("positive_spread_rate", ""),
                "strict_delta_pct_points": strict_delta if strict_delta is not None else "",
                "strict_positive_delta_period_rate": strict_rate if strict_rate is not None else "",
                "strict_period_count": strict_periods,
                "strict_avg_top_minus_bottom_return": strict_spread.get(key, {}).get("avg_spread_return", ""),
                "strict_positive_spread_rate": strict_spread.get(key, {}).get("positive_spread_rate", ""),
                "screen_status": status,
                "accepted": False,
                "formal_backtest_used_as_validation": False,
            }
        )
    return sorted(rows, key=lambda item: (item["screen_status"] != "pre2021_supported_deep_research_candidate_not_accepted", -float(item["train_delta_pct_points"])))


def _spread_stats(bucket_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    df = pd.DataFrame(bucket_rows)
    if df.empty:
        return {}
    df = df[df["bucket"].eq("top_minus_bottom")].copy()
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for key, group in df.groupby(["sector_id", "factor_id"], sort=True):
        returns = pd.to_numeric(group["avg_forward_period_return"], errors="coerce").dropna()
        out[key] = {
            "avg_spread_return": float(returns.mean()) if len(returns) else "",
            "positive_spread_rate": float((returns > 0).mean()) if len(returns) else "",
        }
    return out


def _coverage(panels: pd.DataFrame, strict_panels: pd.DataFrame, schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in SECTOR_SPECS:
        sector = panels[panels["sector_id"].eq(spec.sector_id)] if not panels.empty else pd.DataFrame()
        strict = strict_panels[strict_panels["sector_id"].eq(spec.sector_id)] if not strict_panels.empty else pd.DataFrame()
        sector_schema = [row for row in schema if row["sector_id"] == spec.sector_id]
        rows.append(
            {
                "audit_id": f"{spec.sector_id}_pre2021_panel",
                "sector_id": spec.sector_id,
                "panel_scope": spec.panel_scope,
                "row_count": len(sector),
                "date_count": int(sector["trade_date"].nunique()) if len(sector) else 0,
                "code_count": int(sector["code"].nunique()) if len(sector) else 0,
                "strict_preview_row_count": len(strict),
                "strict_preview_date_count": int(strict["trade_date"].nunique()) if len(strict) else 0,
                "tested_factor_count": len(sector_schema),
                "status": "pass" if len(sector) and any(int(row["usable_date_count"]) >= 2 for row in sector_schema) else "insufficient",
                "accepted": False,
            }
        )
    return rows


def _governance(panels: pd.DataFrame, strict_panels: pd.DataFrame) -> list[dict[str, Any]]:
    pit_leak_count = 0
    for visible_col in ["factor_visible_date", "universe_visible_date", "reviewed_operating_visible_date", "dividend_visible_date_used"]:
        if visible_col in panels.columns:
            visible = panels[visible_col].astype(str)
            trade = panels["trade_date"].astype(str)
            pit_leak_count += int(((visible.notna()) & (visible != "") & (visible > trade)).sum())
    return [
        {"audit_id": "sample_split_train_test_window", "status": "pass", "detail": f"{TRAIN_START}_to_{TRAIN_END}"},
        {"audit_id": "formal_backtest_not_used_for_validation", "status": "pass", "detail": f"{FORMAL_BACKTEST_START}_to_{FORMAL_BACKTEST_END}"},
        {"audit_id": "pit_visible_date_audit", "status": "pass" if pit_leak_count == 0 else "fail", "detail": pit_leak_count},
        {"audit_id": "sector_pool_only", "status": "pass", "detail": "Only existing repaired sector panels / strict preview selected stocks used."},
        {"audit_id": "fixed_10pct_overlay_only", "status": "pass", "detail": "No threshold or budget optimization."},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "live_trading_approved_false", "status": "pass", "detail": False},
    ]


def _pm_decision(comparison: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_fail = [row for row in governance if row["status"] == "fail"]
    supported = [row for row in comparison if row["screen_status"] == "pre2021_supported_deep_research_candidate_not_accepted"]
    train_only = [row for row in comparison if row["screen_status"] == "train_positive_strict_not_confirmed_diagnostic"]
    if gov_fail:
        decision = "blocked_by_pit_or_sample_split_issue"
        next_action = "repair_governance"
    elif supported:
        decision = "pre2021_cross_sector_deep_research_candidates_not_accepted"
        next_action = "open_industry_specific_deep_research_for_supported_candidates"
    elif train_only:
        decision = "train_positive_but_strict_preview_not_confirmed_diagnostic"
        next_action = "keep_train_positive_factors_diagnostic_until_more_strict_or_forward_evidence"
    else:
        decision = "diagnostic_only_no_cross_sector_factor_confirmed"
        next_action = "do_not_promote_cross_sector_factors"
    return [
        {
            "pm_gate_decision": decision,
            "supported_candidate_count": len(supported),
            "train_only_diagnostic_count": len(train_only),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "formal_backtest_used_as_validation": False,
            "next_action": next_action,
        }
    ]


def _next_queue(comparison: list[dict[str, Any]], decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "priority": 1,
            "next_task": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary",
            "status": "ready",
            "reason": "No cross-sector diagnostic factor is accepted.",
        }
    ]
    rank = 2
    for row in comparison[:8]:
        if row["screen_status"] in {"pre2021_supported_deep_research_candidate_not_accepted", "train_positive_strict_not_confirmed_diagnostic"}:
            rows.append(
                {
                    "priority": rank,
                    "next_task": f"industry_deep_research_{row['sector_id']}_{row['factor_id']}",
                    "status": "ready_if_pm_approves" if row["screen_status"].startswith("pre2021_supported") else "diagnostic_only",
                    "reason": f"train_delta={float(row['train_delta_pct_points']):+.2f} pct; strict_delta={row['strict_delta_pct_points']}",
                }
            )
            rank += 1
    rows.append(
        {
            "priority": rank,
            "next_task": "do_not_use_2021_2026_as_factor_discovery_or_validation",
            "status": "ready",
            "reason": "2021-2026 is formal backtest only.",
        }
    )
    return rows


def _blockers(governance: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row["detail"])} for row in governance if row["status"] == "fail"]
    rows.extend(
        {
            "blocker_id": row["audit_id"],
            "severity": "nonfatal",
            "status": "logged",
            "description": f"sector={row['sector_id']} status={row['status']}",
        }
        for row in coverage
        if row["status"] != "pass"
    )
    return rows or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Cross-sector screen completed."}]


def _summary(
    status: str,
    pm_gate_decision: str,
    best_factor: str = "",
    best_sector: str = "",
    best_train: float = 0.0,
    best_strict: float = 0.0,
    deep_research_count: int = 0,
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    blockers = blockers or []
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_cross_sector_pre2021_factor_screen",
        "status": status,
        "train_test_scope_start": TRAIN_START,
        "train_test_scope_end": TRAIN_END,
        "formal_backtest_scope_start": FORMAL_BACKTEST_START,
        "formal_backtest_scope_end": FORMAL_BACKTEST_END,
        "benchmark": BASELINE,
        "primary_reference": PRIMARY,
        "best_sector": best_sector,
        "best_factor": best_factor,
        "best_train_delta_pct_points": best_train,
        "best_strict_delta_pct_points": best_strict,
        "deep_research_count": deep_research_count,
        "pm_gate_decision": pm_gate_decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "formal_backtest_used_as_validation": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "nonfatal"),
    }


def _report(comparison: list[dict[str, Any]], coverage: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    lines = [
        "# V5c Cross-Sector Pre-2021 Factor Screen",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Train/test window: `{TRAIN_START}` to `{TRAIN_END}`",
        f"- Formal backtest window: `{FORMAL_BACKTEST_START}` to `{FORMAL_BACKTEST_END}`; not used as validation.",
        "- Accepted: `False`",
        "- V57f core modified: `False`",
        "",
        "## Top Results",
    ]
    for row in comparison[:12]:
        lines.append(
            f"- `{row['sector_id']}` / `{row['factor_id']}`: train={float(row['train_delta_pct_points']):+.2f} pct, "
            f"strict={row['strict_delta_pct_points']}, status=`{row['screen_status']}`"
        )
    lines.extend(["", "## Coverage"])
    for row in coverage:
        lines.append(
            f"- `{row['sector_id']}`: rows={row['row_count']}, dates={row['date_count']}, strict_rows={row['strict_preview_row_count']}, status=`{row['status']}`"
        )
    lines.extend(["", "This is a rough pre-2021 screen only. It does not update bank/power/highway/port-rail weights and does not replace V5f primary."])
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Cross-Sector Pre-2021 Factor Screen Rules",
            "",
            "- 2013-01-01 to 2021-04-30 is train/test research.",
            "- 2021-05-01 to 2026-05-31 is formal backtest, not validation.",
            "- Use existing repaired sector panels only.",
            "- Use fixed 10% diagnostic overlay only; no threshold or budget scan.",
            "- Do not modify V57f, V5f primary, or any accepted status.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPLIT_DIR / "v5_sample_split_rules.md",
        PREVIEW_DIR / "v5f_pre2021_candidate_signal_preview.csv",
        *[spec.panel_path for spec in SECTOR_SPECS],
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _compound(values: Any) -> float:
    nav = 1.0
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        nav *= 1.0 + float(value)
    return nav


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


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
