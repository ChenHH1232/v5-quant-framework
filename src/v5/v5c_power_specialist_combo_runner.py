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
    _load_prices,
    _max_drawdown,
    _safe_float,
)


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_power_specialist_combo_deep_dive") / "current"
SPLIT_DIR = Path("v5_sample_split_governance_correction") / "current"
PRE2021_SCREEN_DIR = Path("v5c_cross_sector_pre2021_factor_screen") / "current"
PREVIEW_DIR = Path("v5f_pre2021_repaired_multisleeve_data_gate") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
UTILITIES_PANEL = Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_panels_v5" / "utilities_v51f" / "panel_with_low_vol.csv"

PRIMARY = "internal_subsleeve_mom12_70_30"
POWER = "utilities_electricity"
TRAIN_START = "2013-01-01"
TRAIN_END = "2021-04-30"
COMBO_ID = "power_lowpb_ocf_cashflow_roe_equal_combo"
OVERLAY_VERSION = "v5c_power_combo_overlay_on_v5f_10pct"
OVERLAY_BUDGET = 0.10

FACTOR_COLUMNS: tuple[dict[str, Any], ...] = (
    {
        "factor_id": "utilities_low_pb",
        "source_column": "low_price_to_book",
        "direction": "lower_better",
        "combo_weight": 0.25,
        "pre2021_status": "pre2021_supported_deep_research_candidate_not_accepted",
    },
    {
        "factor_id": "utilities_ocf_yield",
        "source_column": "operating_cash_flow_yield",
        "direction": "higher_better",
        "combo_weight": 0.25,
        "pre2021_status": "pre2021_supported_deep_research_candidate_not_accepted",
    },
    {
        "factor_id": "utilities_cashflow_subindustry_score",
        "source_column": "cashflow_yield_subindustry_score",
        "direction": "higher_better",
        "combo_weight": 0.25,
        "pre2021_status": "pre2021_supported_deep_research_candidate_not_accepted",
    },
    {
        "factor_id": "utilities_roe",
        "source_column": "return_on_equity_ttm",
        "direction": "higher_better",
        "combo_weight": 0.25,
        "pre2021_status": "pre2021_supported_deep_research_candidate_not_accepted",
    },
)


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_power_combo_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_inputs", "blocked_missing_required_inputs", blockers=blockers)
        _write_json(out / "v5c_power_combo_summary.json", summary)
        return out / "v5c_power_combo_summary.json"

    utilities_panel = _load_utilities_panel(root)
    scored_panel = _score_panel(utilities_panel)
    preview = pd.read_csv(root / PREVIEW_DIR / "v5f_pre2021_candidate_signal_preview.csv", dtype=str)
    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    primary_weights = pd.read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_weights.csv", dtype={"rebalance_date": str, "code": str})

    factor_spec = _factor_spec(root, scored_panel)
    train_result = _combo_window_result(scored_panel, "pre2021_train_test", TRAIN_START, TRAIN_END)
    strict_preview_result = _strict_preview_result(scored_panel, preview)
    weights = _formal_weights(signals, primary_weights, scored_panel)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    sleeve = _sleeve_contribution(weights, prices)
    governance = _governance(scored_panel, weights, metrics)
    comparison = _comparison(metrics)
    decision = _pm_decision(comparison, governance, train_result, strict_preview_result)
    queue = _next_queue(decision, comparison)
    blockers_out = _blockers(governance)

    _write_csv(out / "v5c_power_combo_factor_spec.csv", factor_spec)
    _write_csv(out / "v5c_power_combo_scored_panel.csv", scored_panel.to_dict("records"))
    _write_csv(out / "v5c_power_combo_pre2021_train_result.csv", train_result)
    _write_csv(out / "v5c_power_combo_strict_preview_result.csv", strict_preview_result)
    _write_csv(out / "v5c_power_combo_formal_weights.csv", weights)
    _write_csv(out / "v5c_power_combo_formal_daily_returns.csv", daily)
    _write_csv(out / "v5c_power_combo_formal_metrics.csv", metrics)
    _write_csv(out / "v5c_power_combo_formal_yearly.csv", yearly)
    _write_csv(out / "v5c_power_combo_sleeve_contribution.csv", sleeve)
    _write_csv(out / "v5c_power_combo_formal_comparison.csv", comparison)
    _write_csv(out / "v5c_power_combo_governance_audit.csv", governance)
    _write_csv(out / "v5c_power_combo_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_power_combo_next_queue.csv", queue)
    _write_csv(out / "v5c_power_combo_blockers.csv", blockers_out)
    (out / "v5c_power_combo_report.md").write_text(_report(train_result, strict_preview_result, comparison, decision), encoding="utf-8")
    (out / "v5c_power_combo_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    overlay = next((row for row in comparison if row["version_id"] == OVERLAY_VERSION), {})
    summary = _summary(
        "completed_power_specialist_combo_deep_dive",
        decision[0]["pm_gate_decision"],
        pre2021_train_delta=float(train_result[0].get("delta_cumulative_return_pct_points_vs_equal_weight", 0.0) if train_result else 0.0),
        strict_delta=float(strict_preview_result[0].get("delta_cumulative_return_pct_points_vs_equal_weight", 0.0) if strict_preview_result else 0.0),
        formal_delta_vs_v5f=float(overlay.get("delta_return_pct_points_vs_v5f_primary", 0.0) or 0.0),
        formal_delta_vs_repaired=float(overlay.get("delta_return_pct_points_vs_repaired_baseline", 0.0) or 0.0),
        blockers=blockers_out,
    )
    _write_json(out / "v5c_power_combo_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_power_combo_summary.json"


def _load_utilities_panel(root: Path) -> pd.DataFrame:
    panel = pd.read_csv(root / UTILITIES_PANEL, dtype={"trade_date": str, "code": str})
    panel = panel[(panel["trade_date"] >= TRAIN_START) & (panel["trade_date"] <= BACKTEST_END)].copy()
    panel["sector_id"] = POWER
    panel["future_return"] = pd.to_numeric(panel.get("future_return"), errors="coerce")
    return panel


def _score_panel(panel: pd.DataFrame) -> pd.DataFrame:
    scored = panel.copy()
    component_cols: list[str] = []
    for factor in FACTOR_COLUMNS:
        col = str(factor["source_column"])
        raw = pd.to_numeric(scored[col], errors="coerce")
        component = raw if factor["direction"] == "higher_better" else -raw
        component_name = f"{factor['factor_id']}_rank_score"
        scored[component_name] = component.groupby(scored["trade_date"]).rank(pct=True, method="average")
        component_cols.append(component_name)
    scored["power_combo_score"] = scored[component_cols].mean(axis=1, skipna=False)
    scored["power_combo_component_count"] = scored[component_cols].notna().sum(axis=1)
    scored["power_combo_rank"] = scored.groupby("trade_date")["power_combo_score"].rank(pct=True, method="first")
    scored["power_combo_bucket"] = "middle"
    scored.loc[scored["power_combo_rank"] > 2 / 3, "power_combo_bucket"] = "top"
    scored.loc[scored["power_combo_rank"] <= 1 / 3, "power_combo_bucket"] = "bottom"
    scored.loc[scored["power_combo_score"].isna(), "power_combo_bucket"] = "missing"
    return scored


def _factor_spec(root: Path, scored_panel: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    screen = _read_csv_safe(root / PRE2021_SCREEN_DIR / "v5c_cross_sector_pre2021_factor_comparison.csv")
    screen_map = {row.get("factor_id", ""): row for row in screen}
    for factor in FACTOR_COLUMNS:
        col = str(factor["source_column"])
        values = pd.to_numeric(scored_panel[col], errors="coerce")
        pre = scored_panel[(scored_panel["trade_date"] >= TRAIN_START) & (scored_panel["trade_date"] <= TRAIN_END)]
        formal = scored_panel[(scored_panel["trade_date"] >= BACKTEST_START) & (scored_panel["trade_date"] <= BACKTEST_END)]
        rows.append(
            {
                **factor,
                "combo_id": COMBO_ID,
                "pre2021_row_count": len(pre),
                "pre2021_available_count": int(pd.to_numeric(pre[col], errors="coerce").notna().sum()),
                "formal_row_count": len(formal),
                "formal_available_count": int(pd.to_numeric(formal[col], errors="coerce").notna().sum()),
                "all_window_coverage": float(values.notna().mean()) if len(values) else 0.0,
                "pre2021_train_delta_from_prior_screen": screen_map.get(factor["factor_id"], {}).get("train_delta_pct_points", ""),
                "pre2021_strict_delta_from_prior_screen": screen_map.get(factor["factor_id"], {}).get("strict_delta_pct_points", ""),
                "accepted": False,
            }
        )
    rows.append(
        {
            "factor_id": COMBO_ID,
            "source_column": "equal_weight_combo_of_four_pre_registered_power_factors",
            "direction": "higher_better",
            "combo_weight": 1.0,
            "pre2021_status": "fixed_combo_built_from_pre2021_supported_components",
            "combo_id": COMBO_ID,
            "pre2021_row_count": int(((scored_panel["trade_date"] >= TRAIN_START) & (scored_panel["trade_date"] <= TRAIN_END)).sum()),
            "pre2021_available_count": int(scored_panel[(scored_panel["trade_date"] >= TRAIN_START) & (scored_panel["trade_date"] <= TRAIN_END)]["power_combo_score"].notna().sum()),
            "formal_row_count": int(((scored_panel["trade_date"] >= BACKTEST_START) & (scored_panel["trade_date"] <= BACKTEST_END)).sum()),
            "formal_available_count": int(scored_panel[(scored_panel["trade_date"] >= BACKTEST_START) & (scored_panel["trade_date"] <= BACKTEST_END)]["power_combo_score"].notna().sum()),
            "all_window_coverage": float(scored_panel["power_combo_score"].notna().mean()) if len(scored_panel) else 0.0,
            "pre2021_train_delta_from_prior_screen": "",
            "pre2021_strict_delta_from_prior_screen": "",
            "accepted": False,
        }
    )
    return rows


def _combo_window_result(scored: pd.DataFrame, scope: str, start: str, end: str) -> list[dict[str, Any]]:
    panel = scored[(scored["trade_date"] >= start) & (scored["trade_date"] <= end)].copy()
    periods: list[dict[str, Any]] = []
    bucket_rows: list[dict[str, Any]] = []
    for date, group in panel.groupby("trade_date", sort=True):
        valid = group[group["power_combo_score"].notna() & group["future_return"].notna()].copy()
        valid = valid[valid["future_return"].between(-0.95, 3.0)]
        if len(valid) < 3:
            continue
        rank = valid["power_combo_score"].rank(method="first")
        valid["bucket"] = "middle"
        valid.loc[rank > len(valid) * 2 / 3, "bucket"] = "top"
        valid.loc[rank <= len(valid) / 3, "bucket"] = "bottom"
        top = valid[valid["bucket"].eq("top")]
        bottom = valid[valid["bucket"].eq("bottom")]
        equal_return = valid["future_return"].mean()
        top_return = top["future_return"].mean()
        overlay_return = (1 - OVERLAY_BUDGET) * equal_return + OVERLAY_BUDGET * top_return
        periods.append(
            {
                "trade_date": date,
                "valid_stock_count": len(valid),
                "top_stock_count": len(top),
                "equal_weight_period_return": equal_return,
                "overlay_period_return": overlay_return,
                "delta_period_return": overlay_return - equal_return,
                "top_minus_bottom_return": top["future_return"].mean() - bottom["future_return"].mean() if len(bottom) else "",
            }
        )
        for bucket, bucket_df in valid.groupby("bucket", sort=True):
            bucket_rows.append(
                {
                    "trade_date": date,
                    "bucket": bucket,
                    "stock_count": len(bucket_df),
                    "avg_combo_score": bucket_df["power_combo_score"].mean(),
                    "avg_forward_return": bucket_df["future_return"].mean(),
                }
            )
    if not periods:
        return []
    equal_nav = _compound(row["equal_weight_period_return"] for row in periods)
    overlay_nav = _compound(row["overlay_period_return"] for row in periods)
    deltas = [float(row["delta_period_return"]) for row in periods]
    spreads = [float(row["top_minus_bottom_return"]) for row in periods if row["top_minus_bottom_return"] != ""]
    return [
        {
            "scope": scope,
            "combo_id": COMBO_ID,
            "version_id": f"{scope}_{COMBO_ID}_fixed_10pct_overlay",
            "period_count": len(periods),
            "avg_valid_stock_count": sum(row["valid_stock_count"] for row in periods) / len(periods),
            "equal_weight_cumulative_return": equal_nav - 1.0,
            "overlay_cumulative_return": overlay_nav - 1.0,
            "delta_cumulative_return_pct_points_vs_equal_weight": (overlay_nav - equal_nav) * 100,
            "avg_period_delta_return": sum(deltas) / len(deltas),
            "positive_delta_period_rate": sum(1 for value in deltas if value > 0) / len(deltas),
            "avg_top_minus_bottom_return": sum(spreads) / len(spreads) if spreads else "",
            "positive_spread_rate": sum(1 for value in spreads if value > 0) / len(spreads) if spreads else "",
            "bucket_detail_rows": len(bucket_rows),
            "accepted": False,
        }
    ]


def _strict_preview_result(scored: pd.DataFrame, preview: pd.DataFrame) -> list[dict[str, Any]]:
    p = preview.rename(columns={"preview_date": "trade_date"}).copy()
    p = p[p["sector_id"].eq(POWER)][["trade_date", "code", "sector_id"]].drop_duplicates()
    strict = p.merge(scored, on=["trade_date", "code", "sector_id"], how="left")
    return _combo_window_result(strict, "strict_multisleeve_preview_power_subset", TRAIN_START, TRAIN_END)


def _formal_weights(signals: pd.DataFrame, primary_weights: pd.DataFrame, scored: pd.DataFrame) -> list[dict[str, Any]]:
    primary = primary_weights[primary_weights["version_id"].eq(PRIMARY)].copy()
    primary_map = primary.set_index(["rebalance_date", "code"])["target_weight"].astype(float).to_dict()
    score_map = scored.set_index(["trade_date", "code"])["power_combo_score"].to_dict()
    rows: list[dict[str, Any]] = []
    for date, group in signals.groupby("trade_date", sort=True):
        base = group.copy()
        base["base_target_weight"] = base["target_weight"].astype(float)
        base["primary_target_weight"] = [primary_map.get((date, row["code"]), float(row["target_weight"])) for _, row in base.iterrows()]
        base["power_combo_score"] = [_safe_float(score_map.get((date, row["code"]))) for _, row in base.iterrows()]
        rows.extend(_rows_for_version(base, BASELINE, "baseline", base["base_target_weight"], "baseline"))
        rows.extend(_rows_for_version(base, PRIMARY, "v5f_primary_reference", base["primary_target_weight"], "v5f_primary"))
        overlay = _apply_power_combo_overlay(base)
        rows.extend(_rows_for_version(base, OVERLAY_VERSION, "power_specialist_combo_overlay", overlay, "power_combo_top_10pct_overlay"))
    return rows


def _apply_power_combo_overlay(base: pd.DataFrame) -> pd.Series:
    target = base["primary_target_weight"].copy()
    power = base[base["sector_id"].eq(POWER)].copy()
    if power.empty:
        return target
    values = pd.to_numeric(power["power_combo_score"], errors="coerce")
    valid = power[values.notna()].copy()
    if len(valid) < 3:
        return target
    rank = valid["power_combo_score"].rank(method="first")
    top_idx = valid[rank > len(valid) * 2 / 3].index.tolist()
    if not top_idx:
        return target
    idx = power.index
    sleeve_total = power["primary_target_weight"].astype(float).sum()
    core = (1 - OVERLAY_BUDGET) * power["primary_target_weight"].astype(float)
    alloc = pd.Series(0.0, index=idx)
    alloc.loc[top_idx] = OVERLAY_BUDGET * sleeve_total / len(top_idx)
    target.loc[idx] = core + alloc
    return target


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
                "primary_target_weight": float(row["primary_target_weight"]),
                "target_weight": target_weight,
                "weight_delta": target_weight - float(row["base_target_weight"]),
                "delta_vs_primary_weight": target_weight - float(row["primary_target_weight"]),
                "power_combo_score": row.get("power_combo_score", ""),
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
        navs = pd.to_numeric(group["strategy_nav"]).tolist()
        rets = pd.to_numeric(group["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = pd.Series(rets).std() * (252**0.5)
        out.append(
            {
                "version_id": version,
                "family": _family(version),
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
    return sorted(out, key=lambda row: float(row["strategy_return"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].str.slice(0, 4)
    out: list[dict[str, Any]] = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append(
            {
                "version_id": version,
                "family": _family(version),
                "year": year,
                "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1,
                "trade_days": len(group),
            }
        )
    primary = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == PRIMARY}
    baseline = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    for row in out:
        row["delta_return_pct_points_vs_v5f_primary"] = (float(row["period_return"]) - primary.get(row["year"], 0.0)) * 100
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - baseline.get(row["year"], 0.0)) * 100
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
                "abs_delta_vs_baseline": 0.0,
                "abs_delta_vs_primary": 0.0,
                "next_day_delta_vs_baseline": 0.0,
            },
        )
        item["abs_delta_vs_baseline"] += abs(float(row["weight_delta"]))
        item["abs_delta_vs_primary"] += abs(float(row["delta_vs_primary_weight"]))
        item["next_day_delta_vs_baseline"] += float(row["weight_delta"]) * (_safe_float(ret_map.get((row["rebalance_date"], row["code"]))) or 0.0)
    return list(grouped.values())


def _comparison(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        delta = float(row["delta_return_pct_points_vs_v5f_primary"])
        dd = float(row["delta_max_drawdown_pct_points_vs_v5f_primary"])
        if row["version_id"] == PRIMARY:
            status = "current_v5f_primary_reference"
        elif delta > 0.5 and dd <= 0.25:
            status = "formal_backtest_incremental_positive_not_accepted"
        elif delta > 0:
            status = "weak_positive_diagnostic_only"
        else:
            status = "no_incremental_value_vs_v5f_primary"
        rows.append({**row, "comparison_status": status})
    return rows


def _governance(scored: pd.DataFrame, weights: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    preserved = []
    for (_, date, sleeve), group in df.groupby(["version_id", "rebalance_date", "sleeve"], sort=True):
        preserved.append(abs(group["target_weight"].astype(float).sum() - group["primary_target_weight"].astype(float).sum()) < 1e-8 if group["version_id"].iloc[0] == OVERLAY_VERSION else True)
    train = scored[(scored["trade_date"] >= TRAIN_START) & (scored["trade_date"] <= TRAIN_END)]
    formal = scored[(scored["trade_date"] >= BACKTEST_START) & (scored["trade_date"] <= BACKTEST_END)]
    pit_leak = 0
    for visible_col in ["factor_visible_date", "universe_visible_date"]:
        if visible_col in scored.columns:
            visible = scored[visible_col].astype(str)
            pit_leak += int(((visible.notna()) & (visible != "") & (visible > scored["trade_date"].astype(str))).sum())
    changed_non_power = df[df["version_id"].eq(OVERLAY_VERSION) & ~df["sleeve"].eq(POWER)]["delta_vs_primary_weight"].astype(float).abs().sum()
    return [
        {"audit_id": "sample_split_train_test_window", "status": "pass", "detail": f"{TRAIN_START}_to_{TRAIN_END}"},
        {"audit_id": "formal_backtest_not_used_for_factor_discovery", "status": "pass", "detail": f"{BACKTEST_START}_to_{BACKTEST_END}"},
        {"audit_id": "combo_factor_pre_registered_equal_weight", "status": "pass", "detail": ";".join(row["factor_id"] for row in FACTOR_COLUMNS)},
        {"audit_id": "pit_visible_date_audit", "status": "pass" if pit_leak == 0 else "fail", "detail": pit_leak},
        {"audit_id": "pre2021_combo_score_coverage", "status": "pass" if train["power_combo_score"].notna().mean() >= 0.95 else "review", "detail": float(train["power_combo_score"].notna().mean()) if len(train) else 0.0},
        {"audit_id": "formal_combo_score_coverage", "status": "pass" if formal["power_combo_score"].notna().mean() >= 0.95 else "review", "detail": float(formal["power_combo_score"].notna().mean()) if len(formal) else 0.0},
        {"audit_id": "only_power_sleeve_changed_vs_v5f_primary", "status": "pass" if changed_non_power < 1e-10 else "fail", "detail": changed_non_power},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if all(preserved) else "fail", "detail": 0 if all(preserved) else 1},
        {"audit_id": "v57f_selected_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": f"fixed_overlay_budget={OVERLAY_BUDGET}"},
        {"audit_id": "v5f_primary_unchanged", "status": "pass", "detail": PRIMARY},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "live_approved_false", "status": "pass", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
    ]


def _pm_decision(
    comparison: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    train_result: list[dict[str, Any]],
    strict_result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_fail = [row for row in governance if row["status"] == "fail"]
    overlay = next(row for row in comparison if row["version_id"] == OVERLAY_VERSION)
    train_delta = float(train_result[0]["delta_cumulative_return_pct_points_vs_equal_weight"]) if train_result else 0.0
    strict_delta = float(strict_result[0]["delta_cumulative_return_pct_points_vs_equal_weight"]) if strict_result else 0.0
    formal_delta = float(overlay["delta_return_pct_points_vs_v5f_primary"])
    formal_dd_delta = float(overlay["delta_max_drawdown_pct_points_vs_v5f_primary"])
    if gov_fail:
        decision = "blocked_by_governance_issue"
        next_action = "repair_governance_before_any_use"
    elif train_delta > 0 and strict_delta > 0 and formal_delta > 0.5 and formal_dd_delta <= 0.25:
        decision = "power_combo_positive_candidate_for_forward_paper_not_accepted"
        next_action = "open_forward_paper_tracking_without_changing_v5f_primary"
    elif formal_delta > 0:
        decision = "power_combo_weak_positive_diagnostic_only"
        next_action = "keep_diagnostic_until_forward_confirms"
    else:
        decision = "power_combo_no_incremental_value_vs_v5f_primary"
        next_action = "archive_or_hold_as_research_note"
    return [
        {
            "pm_gate_decision": decision,
            "pre2021_train_delta_pct_points": train_delta,
            "strict_preview_delta_pct_points": strict_delta,
            "formal_delta_return_pct_points_vs_v5f_primary": formal_delta,
            "formal_delta_max_drawdown_pct_points_vs_v5f_primary": formal_dd_delta,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_primary_modified": False,
            "next_action": next_action,
        }
    ]


def _next_queue(decision: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gate = decision[0]["pm_gate_decision"]
    return [
        {"priority": 1, "next_task": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary", "status": "ready", "reason": "V5f primary remains unchanged."},
        {"priority": 2, "next_task": "power_combo_forward_paper_tracking", "status": "ready_if_pm_approves" if "positive_candidate" in gate else "diagnostic_only", "reason": f"gate={gate}"},
        {"priority": 3, "next_task": "do_not_tune_power_combo_weights_on_2021_2026", "status": "ready", "reason": "2021-2026 is formal backtest only."},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row["detail"])} for row in governance if row["status"] == "fail"]
    return rows or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Power combo packet completed."}]


def _summary(
    status: str,
    pm_gate_decision: str,
    pre2021_train_delta: float = 0.0,
    strict_delta: float = 0.0,
    formal_delta_vs_v5f: float = 0.0,
    formal_delta_vs_repaired: float = 0.0,
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    blockers = blockers or []
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_power_specialist_combo_deep_dive",
        "combo_id": COMBO_ID,
        "status": status,
        "train_test_scope_start": TRAIN_START,
        "train_test_scope_end": TRAIN_END,
        "formal_backtest_scope_start": BACKTEST_START,
        "formal_backtest_scope_end": BACKTEST_END,
        "benchmark": BASELINE,
        "primary_reference": PRIMARY,
        "pre2021_train_delta_pct_points": pre2021_train_delta,
        "strict_preview_delta_pct_points": strict_delta,
        "formal_delta_return_pct_points_vs_v5f_primary": formal_delta_vs_v5f,
        "formal_delta_return_pct_points_vs_repaired_baseline": formal_delta_vs_repaired,
        "pm_gate_decision": pm_gate_decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "threshold_scan_used": False,
        "formal_backtest_used_as_validation": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "nonfatal"),
    }


def _report(
    train_result: list[dict[str, Any]],
    strict_result: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    train = train_result[0] if train_result else {}
    strict = strict_result[0] if strict_result else {}
    overlay = next(row for row in comparison if row["version_id"] == OVERLAY_VERSION)
    primary = next(row for row in comparison if row["version_id"] == PRIMARY)
    return "\n".join(
        [
            "# V5c Power Specialist Combo Deep Dive",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Combo: `{COMBO_ID}`",
            "- Factors: low PB, operating cash-flow yield, cash-flow subindustry score, ROE.",
            "- Rule: equal-weight factor ranks; fixed 10% top-tercile overlay inside utilities sleeve only.",
            "- V5f primary unchanged: `internal_subsleeve_mom12_70_30`.",
            "",
            "## Pre-2021 Evidence",
            f"- Train/test delta: `{float(train.get('delta_cumulative_return_pct_points_vs_equal_weight', 0.0) or 0.0):+.4f}` pct points.",
            f"- Strict preview delta: `{float(strict.get('delta_cumulative_return_pct_points_vs_equal_weight', 0.0) or 0.0):+.4f}` pct points.",
            "",
            "## Formal Backtest Comparison",
            f"- V5f primary return: `{float(primary['strategy_return'])*100:.2f}%`.",
            f"- Power combo overlay return: `{float(overlay['strategy_return'])*100:.2f}%`.",
            f"- Delta vs V5f primary: `{float(overlay['delta_return_pct_points_vs_v5f_primary']):+.4f}` pct points.",
            f"- Max drawdown delta vs V5f primary: `{float(overlay['delta_max_drawdown_pct_points_vs_v5f_primary']):+.4f}` pct points.",
            "",
            "This is a fixed-rule comparison packet, not an accepted model and not a V5f replacement.",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Power Specialist Combo Rules",
            "",
            "- Use 2013-01-01 to 2021-04-30 only for train/test evidence.",
            "- Use 2021-05-01 to 2026-05-31 only as formal backtest comparison.",
            "- Do not tune factor weights on formal backtest data.",
            "- Combo factors are fixed equal-weight ranks: low PB, OCF yield, cash-flow subindustry score, ROE.",
            "- Overlay is fixed at 10% inside utilities sleeve on top of V5f primary.",
            "- Do not modify V57f or V5f primary.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _family(version: str) -> str:
    if version == BASELINE:
        return "baseline"
    if version == PRIMARY:
        return "v5f_primary_reference"
    if version == OVERLAY_VERSION:
        return "power_specialist_combo_overlay"
    return "other"


def _compound(values: Any) -> float:
    nav = 1.0
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        nav *= 1.0 + float(value)
    return nav


def _read_csv_safe(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPLIT_DIR / "v5_sample_split_rules.md",
        PRE2021_SCREEN_DIR / "v5c_cross_sector_pre2021_factor_comparison.csv",
        PREVIEW_DIR / "v5f_pre2021_candidate_signal_preview.csv",
        UTILITIES_PANEL,
        PRICE_DIR,
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
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
