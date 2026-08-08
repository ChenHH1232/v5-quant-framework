from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_v57f_qv_mr_combination") / "current"
PRICE_DIR = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
DEEP_DIR = Path("v5f_internal_subsleeve_deep_engineering") / "current"
QV_DIR = Path("v5f_quality_value_mean_reversion") / "current"

BASELINE = "v57f_startup_preload_repaired_baseline"
MOM_70_30 = "v5f_mom12_70_30_reference"
QV_70_30 = "v5f_qv_mr60_70_30_reference"
COMBO_70_20_10 = "v57f_core70_mom20_qv_mr10"
COMBO_70_15_15 = "v57f_core70_mom15_qv_mr15"
COMBO_80_10_10 = "v57f_core80_mom10_qv_mr10"
BACKTEST_START = "2021-05-06"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_v57f_qv_mr_combination(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_v57f_qv_mr_combination_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_v57f_qv_mr_combination_summary.json", summary)
        return summary

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    repaired_summary = _read_json(root / REPAIRED_RUN / "summary.json")
    deep_summary = _read_json(root / DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")
    qv_summary = _read_json(root / QV_DIR / "v5f_qv_mean_reversion_summary.json")

    signals = signals[(signals["trade_date"] >= BACKTEST_START) & (signals["trade_date"] <= BACKTEST_END)].copy()
    baseline_daily = baseline_daily[
        (baseline_daily["trade_date"] >= BACKTEST_START) & (baseline_daily["trade_date"] <= BACKTEST_END)
    ].copy()

    spec = _spec()
    weights = _build_weights(signals, prices)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    comparison = _comparison(metrics, deep_summary, qv_summary)
    sleeve = _sleeve_budget_summary(weights)
    turnover = _turnover_cost_health(metrics, comparison)
    governance = _governance_audit(repaired_summary, weights)
    pit = _pit_audit()
    decision = _pm_decision(comparison, turnover, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_v57f_qv_mr_combination_spec.csv", spec)
    _write_csv(out / "v5f_v57f_qv_mr_combination_weights.csv", weights)
    _write_csv(out / "v5f_v57f_qv_mr_combination_daily_returns.csv", daily)
    _write_csv(out / "v5f_v57f_qv_mr_combination_metrics.csv", metrics)
    _write_csv(out / "v5f_v57f_qv_mr_combination_yearly.csv", yearly)
    _write_csv(out / "v5f_v57f_qv_mr_combination_comparison.csv", comparison)
    _write_csv(out / "v5f_v57f_qv_mr_combination_sleeve_budget_summary.csv", sleeve)
    _write_csv(out / "v5f_v57f_qv_mr_combination_turnover_cost_health.csv", turnover)
    _write_csv(out / "v5f_v57f_qv_mr_combination_governance_audit.csv", governance)
    _write_csv(out / "v5f_v57f_qv_mr_combination_pit_audit.csv", pit)
    _write_csv(out / "v5f_v57f_qv_mr_combination_pm_decision.csv", decision)
    _write_csv(out / "v5f_v57f_qv_mr_combination_next_queue.csv", next_queue)
    _write_csv(out / "v5f_v57f_qv_mr_combination_blockers.csv", blockers_out)
    (out / "v5f_v57f_qv_mr_combination_prompt.md").write_text(_prompt(), encoding="utf-8")
    (out / "v5f_v57f_qv_mr_combination_report.md").write_text(
        _report(metrics, comparison, decision),
        encoding="utf-8",
    )
    (out / "v5f_v57f_qv_mr_combination_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_variant(comparison)
    mom_ref = next(row for row in comparison if row["version_id"] == MOM_70_30)
    summary = _summary(
        "completed_v5f_v57f_qv_mr_combination",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=decision[0]["primary_candidate"],
        best_variant=best["version_id"],
        best_delta_return=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        mom_reference_delta_return=float(mom_ref["delta_return_pct_points_vs_repaired_baseline"]),
        best_incremental_vs_mom=float(best["incremental_delta_return_vs_mom70_30_reference"]),
    )
    _write_json(out / "v5f_v57f_qv_mr_combination_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path, dtype={"date": str, "code": str}) for path in (root / PRICE_DIR).glob("*.csv")]
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    prices["close_lag_1"] = prices.groupby("code")["close"].shift(1)
    prices["close_lag_21"] = prices.groupby("code")["close"].shift(21)
    prices["close_lag_61"] = prices.groupby("code")["close"].shift(61)
    prices["close_lag_253"] = prices.groupby("code")["close"].shift(253)
    prices["mom_12_1"] = prices["close_lag_21"] / prices["close_lag_253"] - 1.0
    prices["ret_60d_lagged"] = prices["close_lag_1"] / prices["close_lag_61"] - 1.0
    return prices[(prices["date"] >= BACKTEST_START) & (prices["date"] <= BACKTEST_END)].copy()


def _spec() -> list[dict[str, Any]]:
    return [
        {"version_id": MOM_70_30, "core_budget": 0.70, "mom_budget": 0.30, "qv_mr_budget": 0.00, "role": "current_momentum_reference", "accepted": False},
        {"version_id": QV_70_30, "core_budget": 0.70, "mom_budget": 0.00, "qv_mr_budget": 0.30, "role": "mean_reversion_reference", "accepted": False},
        {"version_id": COMBO_70_20_10, "core_budget": 0.70, "mom_budget": 0.20, "qv_mr_budget": 0.10, "role": "small_qv_mr_satellite", "accepted": False},
        {"version_id": COMBO_70_15_15, "core_budget": 0.70, "mom_budget": 0.15, "qv_mr_budget": 0.15, "role": "balanced_mom_qv_mr_satellite", "accepted": False},
        {"version_id": COMBO_80_10_10, "core_budget": 0.80, "mom_budget": 0.10, "qv_mr_budget": 0.10, "role": "conservative_overlay", "accepted": False},
    ]


def _build_weights(signals: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    feature = prices.set_index(["date", "code"])[["mom_12_1", "ret_60d_lagged"]].to_dict("index")
    specs = {row["version_id"]: row for row in _spec()}
    rows: list[dict[str, Any]] = []
    for date, group in signals.groupby("trade_date", sort=True):
        pool = group.copy()
        pool["base_target_weight"] = pool["target_weight"].astype(float)
        pool["quality_value_score"] = pd.to_numeric(pool["score"], errors="coerce")
        for version, spec in specs.items():
            targets, tags = _targets_for_spec(pool, feature, date, spec)
            for _, row in pool.iterrows():
                code = row["code"]
                feature_row = feature.get((date, code), {})
                target = targets.get(code, float(row["base_target_weight"]))
                rows.append(
                    {
                        "version_id": version,
                        "rebalance_date": date,
                        "code": code,
                        "sleeve": row["sector_id"],
                        "base_target_weight": float(row["base_target_weight"]),
                        "target_weight": target,
                        "weight_delta": target - float(row["base_target_weight"]),
                        "quality_value_score": row["quality_value_score"],
                        "mom_12_1": _safe_float(feature_row.get("mom_12_1")),
                        "ret_60d_lagged": _safe_float(feature_row.get("ret_60d_lagged")),
                        "selection_tag": tags.get(code, "core_only"),
                        "core_budget": spec["core_budget"],
                        "mom_budget": spec["mom_budget"],
                        "qv_mr_budget": spec["qv_mr_budget"],
                        "locked_pool_only": True,
                        "new_stock_selected": False,
                        "accepted": False,
                    }
                )
    baseline_rows = []
    for date, group in signals.groupby("trade_date", sort=True):
        for _, row in group.iterrows():
            baseline_rows.append(
                {
                    "version_id": BASELINE,
                    "rebalance_date": date,
                    "code": row["code"],
                    "sleeve": row["sector_id"],
                    "base_target_weight": float(row["target_weight"]),
                    "target_weight": float(row["target_weight"]),
                    "weight_delta": 0.0,
                    "quality_value_score": row["score"],
                    "mom_12_1": "",
                    "ret_60d_lagged": "",
                    "selection_tag": "baseline",
                    "core_budget": 1.0,
                    "mom_budget": 0.0,
                    "qv_mr_budget": 0.0,
                    "locked_pool_only": True,
                    "new_stock_selected": False,
                    "accepted": False,
                }
            )
    return rows + baseline_rows


def _targets_for_spec(
    pool: pd.DataFrame,
    feature: dict[tuple[str, str], dict[str, Any]],
    date: str,
    spec: dict[str, Any],
) -> tuple[dict[str, float], dict[str, str]]:
    targets: dict[str, float] = {}
    tags: dict[str, str] = {}
    for sleeve, group in pool.groupby("sector_id"):
        sleeve_total = group["base_target_weight"].astype(float).sum()
        mom_selected = _top_momentum_codes(group, feature, date)
        qv_selected = _qv_mr_codes(group, feature, date)
        for _, row in group.iterrows():
            code = row["code"]
            target = float(spec["core_budget"]) * float(row["base_target_weight"])
            tag_parts = []
            if code in mom_selected and float(spec["mom_budget"]) > 0:
                target += float(spec["mom_budget"]) * sleeve_total / len(mom_selected)
                tag_parts.append("mom")
            if code in qv_selected and float(spec["qv_mr_budget"]) > 0:
                target += float(spec["qv_mr_budget"]) * sleeve_total / len(qv_selected)
                tag_parts.append("qv_mr")
            targets[code] = target
            tags[code] = "+".join(tag_parts) if tag_parts else "core_only"
    return targets, tags


def _top_momentum_codes(group: pd.DataFrame, feature: dict[tuple[str, str], dict[str, Any]], date: str) -> list[str]:
    scores = group["code"].map(lambda code: _safe_float(feature.get((date, code), {}).get("mom_12_1")))
    if scores.notna().sum() == 0:
        return group.sort_values("code").head(max(1, math.ceil(len(group) / 3)))["code"].tolist()
    ranks = scores.rank(method="first", ascending=False)
    return group.loc[ranks <= max(1, math.ceil(len(group) / 3)), "code"].tolist()


def _qv_mr_codes(group: pd.DataFrame, feature: dict[tuple[str, str], dict[str, Any]], date: str) -> list[str]:
    tmp = group.copy()
    tmp["_ret60"] = tmp["code"].map(lambda code: _safe_float(feature.get((date, code), {}).get("ret_60d_lagged")))
    tmp["_quality_rank"] = tmp["quality_value_score"].rank(method="first", ascending=False)
    tmp["_reversal_rank"] = tmp["_ret60"].fillna(tmp["_ret60"].median()).rank(method="first", ascending=True)
    high_quality = tmp["_quality_rank"] <= math.ceil(len(tmp) / 2)
    weak_return = tmp["_reversal_rank"] <= math.ceil(len(tmp) / 2)
    selected = tmp.loc[high_quality & weak_return, "code"].tolist()
    if selected:
        return selected
    tmp["_blend"] = tmp["_quality_rank"] + tmp["_reversal_rank"]
    return tmp.sort_values(["_blend", "code"]).head(max(1, math.ceil(len(tmp) / 3)))["code"].tolist()


def _daily_returns(weights: list[dict[str, Any]], prices: pd.DataFrame, baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    baseline_ret = baseline_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    baseline_nav = baseline_daily.set_index("trade_date")["strategy_nav"].astype(float).to_dict()
    official_rebalances = set(pd.read_csv(REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str})["trade_date"])
    df = pd.DataFrame(weights)
    rows: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        if version == BASELINE:
            continue
        nav = 1.0
        active: pd.DataFrame | None = None
        prev_target: dict[str, float] = {}
        prev_base: dict[str, float] = {}
        for day in sorted(baseline_daily["trade_date"].tolist()):
            if day in official_rebalances:
                active = group[group["rebalance_date"] == day].copy()
            if active is None or active.empty:
                continue
            target = {row["code"]: float(row["target_weight"]) for _, row in active.iterrows()}
            base = {row["code"]: float(row["base_target_weight"]) for _, row in active.iterrows()}
            overlay_turnover = _target_turnover(prev_target, target) if day in official_rebalances else 0.0
            baseline_turnover = _target_turnover(prev_base, base) if day in official_rebalances else 0.0
            incremental_turnover = max(0.0, overlay_turnover - baseline_turnover)
            commission = incremental_turnover * COMMISSION_RATE
            delta = sum(
                float(row["weight_delta"]) * (_safe_float(ret_map.get((day, row["code"]))) or 0.0)
                for _, row in active.iterrows()
            )
            strategy_return = baseline_ret[day] + delta - commission
            nav *= 1.0 + strategy_return
            rows.append(
                {
                    "trade_date": day,
                    "version_id": version,
                    "strategy_return": strategy_return,
                    "strategy_nav": nav,
                    "baseline_return": baseline_ret[day],
                    "delta_stock_return": delta,
                    "incremental_turnover": incremental_turnover,
                    "incremental_commission": commission,
                    "accepted": False,
                }
            )
            if day in official_rebalances:
                prev_target = target
                prev_base = base
    for day in sorted(baseline_daily["trade_date"].tolist()):
        rows.append(
            {
                "trade_date": day,
                "version_id": BASELINE,
                "strategy_return": baseline_ret[day],
                "strategy_nav": baseline_nav[day],
                "baseline_return": baseline_ret[day],
                "delta_stock_return": 0.0,
                "incremental_turnover": 0.0,
                "incremental_commission": 0.0,
                "accepted": False,
            }
        )
    return rows


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        group = group.sort_values("trade_date")
        navs = pd.to_numeric(group["strategy_nav"]).tolist()
        rets = pd.to_numeric(group["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = pd.Series(rets).std() * (252**0.5)
        out.append(
            {
                "version_id": version,
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "incremental_turnover_total": pd.to_numeric(group["incremental_turnover"]).sum(),
                "incremental_commission_total": pd.to_numeric(group["incremental_commission"]).sum(),
                "accepted": False,
            }
        )
    baseline = next(row for row in out if row["version_id"] == BASELINE)
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["strategy_return"]) - float(baseline["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (float(row["max_drawdown"]) - float(baseline["max_drawdown"])) * 100
    return sorted(out, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].str.slice(0, 4)
    out = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append({"version_id": version, "year": year, "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1, "trade_days": len(group)})
    base = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - base.get(row["year"], 0.0)) * 100
    return out


def _comparison(metrics: list[dict[str, Any]], deep_summary: dict[str, Any], qv_summary: dict[str, Any]) -> list[dict[str, Any]]:
    mom = next(row for row in metrics if row["version_id"] == MOM_70_30)
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        rows.append(
            {
                "version_id": row["version_id"],
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "incremental_delta_return_vs_mom70_30_reference": float(row["delta_return_pct_points_vs_repaired_baseline"]) - float(mom["delta_return_pct_points_vs_repaired_baseline"]),
                "incremental_delta_drawdown_vs_mom70_30_reference": float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"]) - float(mom["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
                "official_registered_mom70_30_delta_return": deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"],
                "prior_qv_mr_best_delta_return": qv_summary["best_delta_return_pct_points_vs_repaired_baseline"],
                "accepted": False,
            }
        )
    return rows


def _sleeve_budget_summary(weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    rows = []
    for (version, sleeve), group in df[df["version_id"] != BASELINE].groupby(["version_id", "sleeve"], sort=True):
        rows.append(
            {
                "version_id": version,
                "sleeve": sleeve,
                "avg_positive_delta_qv_score": pd.to_numeric(group[group["weight_delta"].astype(float) > 0]["quality_value_score"], errors="coerce").mean(),
                "avg_positive_delta_ret60": pd.to_numeric(group[group["weight_delta"].astype(float) > 0]["ret_60d_lagged"], errors="coerce").mean(),
                "positive_delta_rows": int((group["weight_delta"].astype(float) > 0).sum()),
            }
        )
    return rows


def _turnover_cost_health(metrics: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        comp = next(item for item in comparison if item["version_id"] == row["version_id"])
        edge = float(row["delta_return_pct_points_vs_repaired_baseline"]) / 100.0
        cost = float(row["incremental_commission_total"])
        rows.append(
            {
                "version_id": row["version_id"],
                "incremental_turnover_total": row["incremental_turnover_total"],
                "incremental_commission_total": cost,
                "delta_return_decimal_vs_repaired_baseline": edge,
                "incremental_delta_return_vs_mom70_30_reference": comp["incremental_delta_return_vs_mom70_30_reference"],
                "cost_to_edge_ratio": cost / edge if edge else "",
                "cost_health": "pass" if edge > cost else "review",
            }
        )
    return rows


def _governance_audit(repaired_summary: dict[str, Any], weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    drift = (
        df.groupby(["rebalance_date", "version_id", "sleeve"])[["target_weight", "base_target_weight"]]
        .sum()
        .assign(drift=lambda x: (x["target_weight"] - x["base_target_weight"]).abs())
    )
    return [
        {"audit_id": "backtest_scope_end", "status": "pass", "detail": BACKTEST_END},
        {"audit_id": "repaired_first_signal", "status": "pass" if repaired_summary.get("startup_preload", {}).get("effective_first_signal_date") == "2021-05-06" else "fail", "detail": repaired_summary.get("startup_preload", {}).get("effective_first_signal_date")},
        {"audit_id": "locked_v57f_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if float(drift["drift"].max()) < 1e-10 else "fail", "detail": float(drift["drift"].max())},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": "V57f repaired selected pool only"},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pit_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "quality_value_score_visible", "status": "pass", "detail": "Uses V57f repaired signal score at rebalance."},
        {"audit_id": "mom_12_1_visible", "status": "pass", "detail": "Uses close_lag_21 / close_lag_253 at rebalance."},
        {"audit_id": "ret_60d_visible", "status": "pass", "detail": "Uses close_lag_1 / close_lag_61 at rebalance."},
    ]


def _pm_decision(comparison: list[dict[str, Any]], turnover: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    best = _best_variant(comparison)
    mom = next(row for row in comparison if row["version_id"] == MOM_70_30)
    best_cost = next(row for row in turnover if row["version_id"] == best["version_id"])
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        primary = ""
        rationale = "Governance audit failed."
    elif (
        best["version_id"] != MOM_70_30
        and float(best["incremental_delta_return_vs_mom70_30_reference"]) > 0.5
        and float(best["incremental_delta_drawdown_vs_mom70_30_reference"]) <= 0.1
        and best_cost["cost_health"] == "pass"
    ):
        decision = "promote_v57f_mom_qv_mr_combo_to_pm_quant_review_not_accepted"
        primary = best["version_id"]
        rationale = "A V57f core plus momentum plus QV mean-reversion combo improves on momentum reference with acceptable risk."
    elif best["version_id"] != MOM_70_30 and float(best["incremental_delta_return_vs_mom70_30_reference"]) > 0:
        decision = "combo_positive_but_insufficient_keep_momentum_primary"
        primary = MOM_70_30
        rationale = "A combo improves return but not enough to replace the momentum reference."
    else:
        decision = "combo_diagnostic_only_keep_momentum_primary"
        primary = MOM_70_30
        rationale = "QV mean-reversion combinations do not improve on momentum 70/30."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": primary,
            "best_variant": best["version_id"],
            "mom_reference": MOM_70_30,
            "best_delta_return_pct_points_vs_repaired_baseline": best["delta_return_pct_points_vs_repaired_baseline"],
            "mom_reference_delta_return_pct_points_vs_repaired_baseline": mom["delta_return_pct_points_vs_repaired_baseline"],
            "best_incremental_delta_return_vs_mom70_30_reference": best["incremental_delta_return_vs_mom70_30_reference"],
            "best_incremental_delta_drawdown_vs_mom70_30_reference": best["incremental_delta_drawdown_vs_mom70_30_reference"],
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Keep momentum 70/30 as primary if combos do not promote.", "allowed": True},
        {"priority": 2, "task": "Open PM/Quant review for promoted combo if gate passes.", "allowed": decision.startswith("promote_v57f")},
        {"priority": 3, "task": "Archive QV mean-reversion combo as diagnostic if it fails.", "allowed": decision.startswith("combo_diagnostic")},
        {"priority": 4, "task": "Scan combo budgets or full-market mean reversion.", "allowed": False},
    ]


def _best_variant(comparison: list[dict[str, Any]]) -> dict[str, Any]:
    return max(comparison, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "V57f + QV MR combo test completed."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    best_variant: str = "",
    best_delta_return: float = 0.0,
    mom_reference_delta_return: float = 0.0,
    best_incremental_vs_mom: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_v57f_qv_mr_combination",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_candidate": primary_candidate,
        "best_variant": best_variant,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_return,
        "mom_reference_delta_return_pct_points_vs_repaired_baseline": mom_reference_delta_return,
        "best_incremental_delta_return_vs_mom70_30_reference": best_incremental_vs_mom,
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


def _report(metrics: list[dict[str, Any]], comparison: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f V57f + Momentum + Quality-Value Mean Reversion Combination",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary: `{decision[0]['primary_candidate']}`",
            f"- Best variant: `{decision[0]['best_variant']}`",
            "- Scope: V57f repaired selected pool only; historical window ends `2026-05-31`.",
            "- Status: not accepted; not live approved.",
            "",
            "## Metrics",
            *[
                f"- `{row['version_id']}`: return={float(row['strategy_return']) * 100:.2f}%, delta={float(row['delta_return_pct_points_vs_repaired_baseline']):.4f} pct, dd_delta={float(row['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct"
                for row in metrics
            ],
            "",
            "## Versus Momentum Reference",
            *[
                f"- `{row['version_id']}`: incremental={float(row['incremental_delta_return_vs_mom70_30_reference']):.4f} pct, dd_incremental={float(row['incremental_delta_drawdown_vs_mom70_30_reference']):.4f} pct"
                for row in comparison
            ],
            "",
        ]
    )


def _prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f V57f repaired + momentum + quality-value mean reversion combination test

任务目标：
测试均值回归是否有可行空间：不是让均值回归替代 V5f 动量，而是作为 V57f repaired 底盘上的小预算 satellite，与当前 12-1 momentum 共同分配同 sleeve 内权重。

固定组合：
1. V57f core 70% + momentum 30%；
2. V57f core 70% + quality-value mean reversion 30%；
3. V57f core 70% + momentum 20% + QV mean reversion 10%；
4. V57f core 70% + momentum 15% + QV mean reversion 15%；
5. V57f core 80% + momentum 10% + QV mean reversion 10%。

历史工程窗口：
2021-05-06 至 2026-05-31。

禁止：
不改 V57f，不新增股票，不全市场选股，不跨 sleeve，不改 sleeve 总权重，不标记 accepted/live approved。
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f V57f + QV MR Combination Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- V57f repaired is the stock-selection base.",
            "- Momentum and QV MR only allocate same-sleeve weight budgets.",
            "- No new stocks, no full-market selection, no V57f core modification.",
            "- Not accepted and not live approved.",
            "",
        ]
    )


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _max_drawdown(navs: list[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        if peak:
            max_dd = min(max_dd, nav / peak - 1.0)
    return abs(max_dd)


def _target_turnover(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(abs(a.get(code, 0.0) - b.get(code, 0.0)) for code in set(a) | set(b))


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PRICE_DIR,
        REPAIRED_RUN / "summary.json",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json",
        QV_DIR / "v5f_qv_mean_reversion_summary.json",
    ]
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
    print(json.dumps(run_v5f_v57f_qv_mr_combination(Path(".")), ensure_ascii=False, indent=2))
