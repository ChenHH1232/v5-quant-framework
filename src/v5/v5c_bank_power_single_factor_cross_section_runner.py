from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
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
OUT_DIR = Path("v5c_bank_power_single_factor_cross_section_test") / "current"
PIT_DIR = Path("v5c_bank_power_financial_report_pit_panel") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
PRIMARY = "internal_subsleeve_mom12_70_30"
BANK = "bank"
POWER = "utilities_electricity"


@dataclass(frozen=True)
class SingleFactorSpec:
    factor_id: str
    sleeve: str
    column: str
    direction: str
    status_vs_prior: str
    priority: str
    overlay_allowed: bool
    rationale: str


FACTOR_SPECS: tuple[SingleFactorSpec, ...] = (
    SingleFactorSpec("bank_nim", BANK, "net_interest_margin_pct", "higher_better", "new_financial_report_factor", "P0", True, "Bank core spread profitability."),
    SingleFactorSpec("bank_deposit_cost", BANK, "deposit_cost_pct", "lower_better", "new_financial_report_factor", "P0", True, "Bank liability-cost advantage."),
    SingleFactorSpec("bank_special_mention_loan", BANK, "special_mention_loan_ratio_pct", "lower_better", "new_financial_report_factor", "P0", True, "Earlier asset-quality warning than NPL."),
    SingleFactorSpec("bank_net_interest_spread", BANK, "net_interest_spread_pct", "higher_better", "new_financial_report_factor", "P1", True, "Spread proxy related to NIM."),
    SingleFactorSpec("bank_interest_earning_assets", BANK, "interest_earning_assets_amount", "higher_better", "new_financial_report_factor_size_bias_risk", "P2", True, "Scale proxy; likely large-bank biased."),
    SingleFactorSpec("bank_npl_control", BANK, "non_performing_loan_ratio_pct", "lower_better", "previously_used_control", "control", True, "Control factor already represented in P1 proxy tests."),
    SingleFactorSpec("bank_provision_coverage_control", BANK, "provision_coverage_ratio_pct", "higher_better", "previously_used_control", "control", True, "Control factor already represented in P1 proxy tests."),
    SingleFactorSpec("bank_core_tier1_control", BANK, "core_tier1_capital_ratio_pct", "higher_better", "previously_used_control", "control", True, "Control factor already represented in P1 proxy tests."),
    SingleFactorSpec("power_tariff", POWER, "tariff_yuan_per_kwh", "higher_better", "new_financial_report_factor", "P0", True, "Power realized tariff / average on-grid price."),
    SingleFactorSpec("power_utilization_hours", POWER, "utilization_hours", "higher_better", "new_financial_report_factor", "P0", True, "Power asset utilization."),
    SingleFactorSpec("power_generation_volume_yoy", POWER, "generation_volume_yoy", "higher_better", "new_financial_report_factor", "P0", True, "Operating momentum in output."),
    SingleFactorSpec("power_utilization_hours_yoy", POWER, "utilization_hours_yoy", "higher_better", "new_financial_report_factor", "P1", True, "Operating utilization improvement."),
    SingleFactorSpec("power_tariff_yoy", POWER, "tariff_yuan_per_kwh_yoy", "higher_better", "new_financial_report_factor", "P1", True, "Realized tariff improvement."),
    SingleFactorSpec("power_fuel_cost_yoy", POWER, "fuel_cost_amount_yoy", "lower_better", "new_financial_report_factor_low_coverage", "P2", True, "Fuel-cost pressure improvement; current coverage is sparse."),
    SingleFactorSpec("power_capacity_payment_flag", POWER, "capacity_payment_flag", "higher_better", "new_financial_report_factor_policy_flag", "diagnostic", False, "Policy flag; needs external policy panel before model use."),
    SingleFactorSpec("power_hydro_water_flag", POWER, "hydro_water_flag", "higher_better", "new_financial_report_factor_keyword_flag", "diagnostic", False, "Keyword flag, not a water-strength numeric panel."),
)


VERSION_FAMILIES = {
    BASELINE: "baseline",
    PRIMARY: "v5f_primary_reference",
}


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_bank_power_single_factor_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_inputs", blockers=blockers)
        _write_json(out / "v5c_bank_power_single_factor_summary.json", summary)
        return out / "v5c_bank_power_single_factor_summary.json"

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    primary_weights = pd.read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_weights.csv", dtype={"rebalance_date": str, "code": str})
    pit_panel = pd.read_csv(root / PIT_DIR / "v5c_bank_power_rebalance_pit_field_panel.csv", dtype={"trade_date": str, "code": str})

    schema = _schema(pit_panel)
    bucket_result = _bucket_result(signals, pit_panel, prices, baseline_daily)
    ic_rows = _ic_rows(bucket_result)
    weights = _build_weights(signals, primary_weights, pit_panel)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    comparison = _comparison(metrics, schema, bucket_result, ic_rows)
    governance = _governance(weights, schema)
    decision = _pm_decision(comparison, governance)
    next_queue = _next_queue(comparison, decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5c_bank_power_single_factor_schema.csv", schema)
    _write_csv(out / "v5c_bank_power_single_factor_bucket_result.csv", bucket_result)
    _write_csv(out / "v5c_bank_power_single_factor_ic.csv", ic_rows)
    _write_csv(out / "v5c_bank_power_single_factor_overlay_weights.csv", weights)
    _write_csv(out / "v5c_bank_power_single_factor_daily_returns.csv", daily)
    _write_csv(out / "v5c_bank_power_single_factor_metrics.csv", metrics)
    _write_csv(out / "v5c_bank_power_single_factor_yearly.csv", yearly)
    _write_csv(out / "v5c_bank_power_single_factor_comparison.csv", comparison)
    _write_csv(out / "v5c_bank_power_single_factor_governance_audit.csv", governance)
    _write_csv(out / "v5c_bank_power_single_factor_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_bank_power_single_factor_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_bank_power_single_factor_blockers.csv", blockers_out)
    (out / "v5c_bank_power_single_factor_report.md").write_text(_report(comparison, decision, schema), encoding="utf-8")
    (out / "v5c_bank_power_single_factor_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = comparison[0]
    summary = _summary(
        "completed_single_factor_cross_section_test",
        best_factor=best["factor_id"],
        best_version=best["version_id"],
        best_delta_vs_v5f=float(best["delta_return_pct_points_vs_v5f_primary"]),
        best_delta_vs_baseline=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        pm_gate_decision=decision[0]["pm_gate_decision"],
        blockers=blockers_out,
    )
    _write_json(out / "v5c_bank_power_single_factor_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_bank_power_single_factor_summary.json"


def _schema(pit_panel: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for spec in FACTOR_SPECS:
        group = pit_panel[pit_panel["sleeve"].eq(spec.sleeve)]
        values = pd.to_numeric(group.get(spec.column, pd.Series(dtype=float)), errors="coerce")
        coverage = float(values.notna().mean()) if len(group) else 0.0
        if not spec.overlay_allowed:
            test_scope = "bucket_diagnostic_only"
        elif coverage >= 0.5:
            test_scope = "bucket_and_fixed_10pct_overlay"
        else:
            test_scope = "low_coverage_bucket_and_fixed_10pct_overlay_diagnostic"
        rows.append(
            {
                "factor_id": spec.factor_id,
                "sleeve": spec.sleeve,
                "source_column": spec.column,
                "direction": spec.direction,
                "status_vs_prior": spec.status_vs_prior,
                "priority": spec.priority,
                "rebalance_row_count": len(group),
                "available_row_count": int(values.notna().sum()),
                "coverage": coverage,
                "overlay_allowed": spec.overlay_allowed,
                "test_scope": test_scope,
                "rationale": spec.rationale,
                "accepted": False,
            }
        )
    return rows


def _bucket_result(signals: pd.DataFrame, pit_panel: pd.DataFrame, prices: pd.DataFrame, baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    rebalance_dates = sorted(signals["trade_date"].unique())
    date_to_next = {date: (rebalance_dates[index + 1] if index + 1 < len(rebalance_dates) else "") for index, date in enumerate(rebalance_dates)}
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    daily_dates = sorted(baseline_daily["trade_date"].tolist())
    pit_by_key = pit_panel.set_index(["trade_date", "code"]).to_dict("index")
    rows: list[dict[str, Any]] = []
    for spec in FACTOR_SPECS:
        for date, group in signals[signals["sector_id"].eq(spec.sleeve)].groupby("trade_date", sort=True):
            items = []
            for _, signal in group.iterrows():
                raw = pit_by_key.get((date, signal["code"]), {}).get(spec.column, "")
                value = _safe_float(raw)
                if value is None or math.isnan(value):
                    continue
                score = value if spec.direction == "higher_better" else -value
                forward_return = _period_stock_return(signal["code"], date, date_to_next.get(date, ""), daily_dates, ret_map)
                if forward_return is None:
                    continue
                items.append({"code": signal["code"], "value": value, "score": score, "forward_return": forward_return, "weight": float(signal["target_weight"])})
            if not items:
                continue
            item_df = pd.DataFrame(items)
            item_df["rank"] = item_df["score"].rank(method="first")
            item_df["bucket"] = "middle"
            item_df.loc[item_df["rank"] > len(item_df) * 2 / 3, "bucket"] = "top"
            item_df.loc[item_df["rank"] <= len(item_df) / 3, "bucket"] = "bottom"
            for bucket, bucket_df in item_df.groupby("bucket", sort=True):
                rows.append(
                    {
                        "factor_id": spec.factor_id,
                        "sleeve": spec.sleeve,
                        "rebalance_date": date,
                        "next_rebalance_date": date_to_next.get(date, ""),
                        "bucket": bucket,
                        "stock_count": len(bucket_df),
                        "avg_factor_value": bucket_df["value"].mean(),
                        "avg_forward_period_return": bucket_df["forward_return"].mean(),
                        "weighted_forward_period_return": _weighted_mean(bucket_df["forward_return"], bucket_df["weight"]),
                    }
                )
            top = item_df[item_df["bucket"].eq("top")]
            bottom = item_df[item_df["bucket"].eq("bottom")]
            if len(top) and len(bottom):
                rows.append(
                    {
                        "factor_id": spec.factor_id,
                        "sleeve": spec.sleeve,
                        "rebalance_date": date,
                        "next_rebalance_date": date_to_next.get(date, ""),
                        "bucket": "top_minus_bottom",
                        "stock_count": len(top) + len(bottom),
                        "avg_factor_value": top["value"].mean() - bottom["value"].mean(),
                        "avg_forward_period_return": top["forward_return"].mean() - bottom["forward_return"].mean(),
                        "weighted_forward_period_return": _weighted_mean(top["forward_return"], top["weight"]) - _weighted_mean(bottom["forward_return"], bottom["weight"]),
                    }
                )
    return rows


def _ic_rows(bucket_result: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(bucket_result)
    rows = []
    if df.empty:
        return rows
    spread = df[df["bucket"].eq("top_minus_bottom")].copy()
    for factor_id, group in spread.groupby("factor_id", sort=True):
        returns = pd.to_numeric(group["avg_forward_period_return"], errors="coerce").dropna()
        weighted = pd.to_numeric(group["weighted_forward_period_return"], errors="coerce").dropna()
        rows.append(
            {
                "factor_id": factor_id,
                "observation_count": len(returns),
                "avg_top_minus_bottom_return": returns.mean() if len(returns) else "",
                "median_top_minus_bottom_return": returns.median() if len(returns) else "",
                "positive_spread_rate": float((returns > 0).mean()) if len(returns) else "",
                "avg_weighted_top_minus_bottom_return": weighted.mean() if len(weighted) else "",
                "diagnostic_status": _diagnostic_status(returns),
            }
        )
    return rows


def _build_weights(signals: pd.DataFrame, primary_weights: pd.DataFrame, pit_panel: pd.DataFrame) -> list[dict[str, Any]]:
    primary = primary_weights[primary_weights["version_id"].eq(PRIMARY)].copy()
    primary_map = primary.set_index(["rebalance_date", "code"])["target_weight"].astype(float).to_dict()
    pit_by_key = pit_panel.set_index(["trade_date", "code"]).to_dict("index")
    rows: list[dict[str, Any]] = []
    for date, group in signals.groupby("trade_date", sort=True):
        base = group.copy()
        base["base_target_weight"] = base["target_weight"].astype(float)
        base["primary_target_weight"] = [primary_map.get((date, row["code"]), float(row["target_weight"])) for _, row in base.iterrows()]
        rows.extend(_rows_for_version(base, BASELINE, "baseline", base["base_target_weight"], "baseline", "", ""))
        rows.extend(_rows_for_version(base, PRIMARY, "v5f_primary_reference", base["primary_target_weight"], "v5f_primary", "", ""))
        for spec in FACTOR_SPECS:
            if not spec.overlay_allowed:
                continue
            variant = _version_id(spec)
            tmp = base.copy()
            tmp["factor_value"] = [_safe_float(pit_by_key.get((date, row["code"]), {}).get(spec.column, "")) for _, row in tmp.iterrows()]
            target = _apply_single_factor_overlay(tmp, spec, 0.10)
            rows.extend(_rows_for_version(tmp, variant, "single_factor_10pct_overlay", target, "single_factor_top_overlay", spec.factor_id, spec.column))
    return rows


def _apply_single_factor_overlay(base: pd.DataFrame, spec: SingleFactorSpec, budget: float) -> pd.Series:
    target = base["primary_target_weight"].copy()
    sleeve_df = base[base["sector_id"].eq(spec.sleeve)].copy()
    valid = sleeve_df[pd.to_numeric(sleeve_df["factor_value"], errors="coerce").notna()].copy()
    if valid.empty:
        return target
    values = pd.to_numeric(valid["factor_value"], errors="coerce")
    valid["score"] = values if spec.direction == "higher_better" else -values
    rank = valid["score"].rank(method="first")
    top_idx = valid[rank > len(valid) * 2 / 3].index.tolist() or [int(valid["score"].idxmax())]
    idx = sleeve_df.index
    sleeve_total = sleeve_df["primary_target_weight"].astype(float).sum()
    core = (1.0 - budget) * sleeve_df["primary_target_weight"].astype(float)
    alloc = pd.Series(0.0, index=idx)
    alloc.loc[top_idx] = budget * sleeve_total / len(top_idx)
    target.loc[idx] = core + alloc
    return target


def _rows_for_version(base: pd.DataFrame, version: str, family: str, target: pd.Series, bucket: str, factor_id: str, source_column: str) -> list[dict[str, Any]]:
    rows = []
    for idx, row in base.iterrows():
        target_weight = float(target.loc[idx])
        rows.append(
            {
                "version_id": version,
                "family": family,
                "factor_id": factor_id,
                "source_column": source_column,
                "rebalance_date": row["trade_date"],
                "code": row["code"],
                "sleeve": row["sector_id"],
                "base_target_weight": float(row["base_target_weight"]),
                "target_weight": target_weight,
                "weight_delta": target_weight - float(row["base_target_weight"]),
                "factor_value": row.get("factor_value", ""),
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
        turnover = pd.to_numeric(group["turnover_proxy"]).sum() if "turnover_proxy" in group else 0.0
        commission = pd.to_numeric(group["incremental_commission"]).sum() if "incremental_commission" in group else 0.0
        out.append(
            {
                "version_id": version,
                "family": _family(version),
                "factor_id": _factor_from_version(version),
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "turnover_proxy": turnover,
                "incremental_commission_total": commission,
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
        out.append(
            {
                "version_id": version,
                "family": _family(version),
                "factor_id": _factor_from_version(version),
                "year": year,
                "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1,
                "trade_days": len(group),
            }
        )
    primary = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == PRIMARY}
    for row in out:
        row["delta_return_pct_points_vs_v5f_primary"] = (float(row["period_return"]) - primary.get(row["year"], 0.0)) * 100
    return out


def _comparison(metrics: list[dict[str, Any]], schema: list[dict[str, Any]], bucket_result: list[dict[str, Any]], ic_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schema_map = {row["factor_id"]: row for row in schema}
    ic_map = {row["factor_id"]: row for row in ic_rows}
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        factor_id = row["factor_id"]
        if row["version_id"] == PRIMARY:
            status = "current_v5f_primary_reference"
        elif float(row["delta_return_pct_points_vs_v5f_primary"]) > 0.5 and float(row["delta_max_drawdown_pct_points_vs_v5f_primary"]) <= 0.25:
            status = "single_factor_positive_needs_forward_review"
        elif float(row["delta_return_pct_points_vs_v5f_primary"]) > 0:
            status = "weak_positive_diagnostic"
        else:
            status = "no_incremental_value_vs_v5f_primary"
        item = {
            **row,
            "coverage": schema_map.get(factor_id, {}).get("coverage", ""),
            "status_vs_prior": schema_map.get(factor_id, {}).get("status_vs_prior", ""),
            "priority": schema_map.get(factor_id, {}).get("priority", ""),
            "avg_top_minus_bottom_return": ic_map.get(factor_id, {}).get("avg_top_minus_bottom_return", ""),
            "positive_spread_rate": ic_map.get(factor_id, {}).get("positive_spread_rate", ""),
            "single_factor_status": status,
            "accepted": False,
        }
        rows.append(item)
    return sorted(rows, key=lambda item: float(item["strategy_return"]), reverse=True)


def _governance(weights: list[dict[str, Any]], schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    preserved = []
    for (_, _, sleeve), group in df.groupby(["version_id", "rebalance_date", "sleeve"], sort=True):
        preserved.append(abs(group["target_weight"].astype(float).sum() - group["base_target_weight"].astype(float).sum()) < 1e-8)
    return [
        {"audit_id": "repaired_baseline_only", "status": "pass", "detail": BASELINE},
        {"audit_id": "v57f_selected_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if all(preserved) else "fail", "detail": 0 if all(preserved) else 1},
        {"audit_id": "single_factor_only", "status": "pass", "detail": "one factor per overlay variant; no factor blending"},
        {"audit_id": "fixed_10pct_overlay_only", "status": "pass", "detail": "no parameter scan"},
        {"audit_id": "diagnostic_flags_not_overlaid", "status": "pass" if all((row["overlay_allowed"] or row["test_scope"] == "bucket_diagnostic_only") for row in schema) else "fail", "detail": "capacity/hydro flags stay diagnostic-only"},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
    ]


def _pm_decision(comparison: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_fail = [row for row in governance if row["status"] == "fail"]
    positive = [row for row in comparison if row["single_factor_status"] == "single_factor_positive_needs_forward_review"]
    best = comparison[0]
    if gov_fail:
        decision = "blocked_by_governance_issue"
    elif positive:
        decision = "single_factor_positive_candidates_for_deep_research_not_accepted"
    elif float(best["delta_return_pct_points_vs_v5f_primary"]) > 0:
        decision = "single_factor_weak_positive_diagnostic_only"
    else:
        decision = "single_factor_no_clear_incremental_value_vs_v5f_primary"
    return [
        {
            "pm_gate_decision": decision,
            "best_version": best["version_id"],
            "best_factor_id": best["factor_id"],
            "best_delta_return_pct_points_vs_v5f_primary": best["delta_return_pct_points_vs_v5f_primary"],
            "best_delta_return_pct_points_vs_repaired_baseline": best["delta_return_pct_points_vs_repaired_baseline"],
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "next_action": "deep_research_only_for_positive_single_factors; keep_v5f_primary_unmodified",
        }
    ]


def _next_queue(comparison: list[dict[str, Any]], decision: str) -> list[dict[str, Any]]:
    positives = [row for row in comparison if row["single_factor_status"] in {"single_factor_positive_needs_forward_review", "weak_positive_diagnostic"} and row["version_id"] != PRIMARY]
    rows = [{"rank": 1, "next_task": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary", "status": "ready", "reason": f"gate={decision}"}]
    rank = 2
    for row in positives[:5]:
        rows.append(
            {
                "rank": rank,
                "next_task": f"single_factor_deep_research_{row['factor_id']}",
                "status": "ready_if_pm_approves",
                "reason": f"delta_vs_v5f={float(row['delta_return_pct_points_vs_v5f_primary']):+.2f} pct; spread={row['avg_top_minus_bottom_return']}",
            }
        )
        rank += 1
    rows.append({"rank": rank, "next_task": "do_not_combine_single_factors_until_forward_or_walkforward_confirms", "status": "ready", "reason": "avoid factor overfit"})
    return rows


def _period_stock_return(code: str, start_date: str, next_rebalance: str, daily_dates: list[str], ret_map: dict[tuple[str, str], Any]) -> float | None:
    selected_dates = [date for date in daily_dates if date >= start_date and (not next_rebalance or date < next_rebalance)]
    if not selected_dates:
        return None
    value = 1.0
    used = 0
    for date in selected_dates:
        ret = _safe_float(ret_map.get((date, code)))
        if ret is None or math.isnan(ret):
            continue
        value *= 1.0 + ret
        used += 1
    return value - 1.0 if used else None


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    total = float(weights.sum())
    return float((values * weights).sum() / total) if total else float(values.mean())


def _diagnostic_status(returns: pd.Series) -> str:
    if len(returns) < 5:
        return "insufficient_observations"
    if returns.mean() > 0 and (returns > 0).mean() >= 0.55:
        return "positive_directional_diagnostic"
    if returns.mean() < 0 and (returns > 0).mean() <= 0.45:
        return "negative_directional_diagnostic"
    return "mixed_or_weak_direction"


def _version_id(spec: SingleFactorSpec) -> str:
    return f"single_factor_{spec.factor_id}_overlay_10pct"


def _factor_from_version(version: str) -> str:
    if version in {BASELINE, PRIMARY}:
        return ""
    if version.startswith("single_factor_") and version.endswith("_overlay_10pct"):
        return version.removeprefix("single_factor_").removesuffix("_overlay_10pct")
    return ""


def _family(version: str) -> str:
    return VERSION_FAMILIES.get(version, "single_factor_10pct_overlay")


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row["detail"])} for row in governance if row["status"] == "fail"]


def _summary(
    status: str,
    best_factor: str = "",
    best_version: str = "",
    best_delta_vs_v5f: float = 0.0,
    best_delta_vs_baseline: float = 0.0,
    pm_gate_decision: str = "blocked_missing_required_inputs",
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    blockers = blockers or []
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_bank_power_single_factor_cross_section_test",
        "status": status,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "benchmark": BASELINE,
        "primary_reference": PRIMARY,
        "best_factor": best_factor,
        "best_version": best_version,
        "best_delta_return_pct_points_vs_v5f_primary": best_delta_vs_v5f,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_vs_baseline,
        "pm_gate_decision": pm_gate_decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "fatal_blockers": [row for row in blockers if row.get("severity") == "fatal"],
    }


def _report(comparison: list[dict[str, Any]], decision: list[dict[str, Any]], schema: list[dict[str, Any]]) -> str:
    lines = [
        "# V5c Bank / Power Single Factor Cross-Section Test",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Best version: `{decision[0]['best_version']}`",
        f"- Best factor: `{decision[0]['best_factor_id']}`",
        "- Accepted: `False`",
        "- V57f core modified: `False`",
        "",
        "## Top Results",
    ]
    for row in comparison[:10]:
        lines.append(
            f"- `{row['version_id']}`: return={float(row['strategy_return'])*100:.2f}%, "
            f"vs V5f={float(row['delta_return_pct_points_vs_v5f_primary']):+.2f} pct, "
            f"top-bottom={row['avg_top_minus_bottom_return']}, status=`{row['single_factor_status']}`"
        )
    lines.extend(["", "## Tested Factors"])
    for row in schema:
        lines.append(f"- `{row['factor_id']}` ({row['sleeve']}): coverage={float(row['coverage']):.2%}, scope={row['test_scope']}")
    lines.extend(["", "This packet is single-factor diagnostic research only. It does not combine factors, optimize thresholds, or replace V5f primary."])
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Bank / Power Single Factor Rules",
            "",
            "- Use startup-preload repaired V57f baseline only.",
            "- Use only V57f selected bank/electricity stocks and PIT-visible financial-report fields.",
            "- Test one factor at a time; no factor blending.",
            "- Fixed overlay budget is 10%; no threshold or budget scan.",
            "- Preserve sleeve total weights and V57f rebalance dates.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PIT_DIR / "v5c_bank_power_rebalance_pit_field_panel.csv",
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
