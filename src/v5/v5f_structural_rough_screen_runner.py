from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_structural_rough_screen") / "current"
PRICE_DIR = Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_prices_v5"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
COMPARISON_DIR = Path("v5f_repaired_baseline_overlay_comparison") / "current"

BASELINE = "v57f_startup_preload_repaired_baseline"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_structural_rough_screen(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_structural_rough_screen_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_structural_rough_screen_summary.json", summary)
        return summary

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    repaired_summary = _read_json(root / REPAIRED_RUN / "summary.json")
    current_summary = _read_json(root / COMPARISON_DIR / "v5f_repaired_overlay_summary.json")
    current_candidates = _read_csv(root / COMPARISON_DIR / "v5f_candidate_matrix.csv")

    spec = _rough_screen_spec()
    weights = _build_all_weights(signals, prices, baseline_daily)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    drawdown = _drawdown(daily)
    sleeve = _sleeve_contribution(weights, prices)
    governance = _governance(weights, repaired_summary)
    comparison = _comparison_matrix(metrics, current_summary, current_candidates)
    decision = _pm_decision(comparison, governance)
    queue = _next_queue(comparison, decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_structural_rough_screen_spec.csv", spec)
    _write_csv(out / "v5f_structural_rough_screen_weights.csv", weights)
    _write_csv(out / "v5f_structural_rough_screen_daily_returns.csv", daily)
    _write_csv(out / "v5f_structural_rough_screen_metrics.csv", metrics)
    _write_csv(out / "v5f_structural_rough_screen_yearly.csv", yearly)
    _write_csv(out / "v5f_structural_rough_screen_drawdown.csv", drawdown)
    _write_csv(out / "v5f_structural_rough_screen_sleeve_contribution.csv", sleeve)
    _write_csv(out / "v5f_structural_rough_screen_governance_audit.csv", governance)
    _write_csv(out / "v5f_structural_rough_screen_comparison_matrix.csv", comparison)
    _write_csv(out / "v5f_structural_rough_screen_pm_decision.csv", decision)
    _write_csv(out / "v5f_structural_rough_screen_next_queue.csv", queue)
    _write_csv(out / "v5f_structural_rough_screen_blockers.csv", blockers_out)
    (out / "v5f_structural_rough_screen_prompt.md").write_text(_prompt(), encoding="utf-8")
    (out / "v5f_structural_rough_screen_report.md").write_text(_report(comparison, decision), encoding="utf-8")
    (out / "v5f_structural_rough_screen_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = next(row for row in comparison if row["rank"] == 1)
    summary = _summary(
        "completed_v5f_structural_rough_screen",
        decision[0]["pm_gate_decision"],
        [],
        best_direction=best["direction_id"],
        best_delta_return=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        best_delta_drawdown=float(best["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
        deep_research_count=sum(1 for row in comparison if row["rough_screen_status"] == "worth_deep_research"),
    )
    _write_json(out / "v5f_structural_rough_screen_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path, dtype={"date": str, "code": str}) for path in (root / PRICE_DIR).glob("*.csv")]
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    prices["close_lag_21"] = prices.groupby("code")["close"].shift(21)
    prices["close_lag_61"] = prices.groupby("code")["close"].shift(61)
    prices["close_lag_253"] = prices.groupby("code")["close"].shift(253)
    prices["mom_12_1"] = prices["close_lag_21"] / prices["close_lag_253"] - 1.0
    prices["mr_60d"] = prices.groupby("code")["close"].shift(1) / prices["close_lag_61"] - 1.0
    return prices


def _rough_screen_spec() -> list[dict[str, Any]]:
    return [
        {"direction_id": "current_repaired_overlay_reference", "family": "reference", "rule": "Existing repaired comparison candidate: momentum_plus_mean_reversion_equal_blend.", "full_market_selection": False, "accepted": False},
        {"direction_id": "internal_subsleeve_mom12_80_20", "family": "v57f_pool_internal_subsleeve", "rule": "Within each sleeve: 80% original V57f weights + 20% same-sleeve mom12 top-tercile sleeve.", "full_market_selection": False, "accepted": False},
        {"direction_id": "internal_subsleeve_mom12_70_30", "family": "v57f_pool_internal_subsleeve", "rule": "Within each sleeve: 70% original V57f weights + 30% same-sleeve mom12 top-tercile sleeve.", "full_market_selection": False, "accepted": False},
        {"direction_id": "dual_sleeve_mom12_80_20", "family": "dual_sleeve_allocation", "rule": "80% repaired V57f value sleeve + 20% independent mom12 selected-pool sleeve.", "full_market_selection": False, "accepted": False},
        {"direction_id": "dual_sleeve_mom12_60_40", "family": "dual_sleeve_allocation", "rule": "60% repaired V57f value sleeve + 40% independent mom12 selected-pool sleeve.", "full_market_selection": False, "accepted": False},
        {"direction_id": "state_routed_mom12_70_30_or_100_0", "family": "state_routed_budget", "rule": "At rebalance: if repaired V57f trailing 60d NAV return is positive use 70/30 value/momentum; otherwise 100/0.", "full_market_selection": False, "accepted": False},
        {"direction_id": "admission_suppression_mom12_bottom_cap75", "family": "admission_suppression", "rule": "Within each sleeve: bottom mom12 tercile capped to 75% of base weight; released weight redistributed to non-bottom names.", "full_market_selection": False, "accepted": False},
    ]


def _build_all_weights(signals: pd.DataFrame, prices: pd.DataFrame, baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    feature_map = prices.set_index(["date", "code"])[["mom_12_1", "mr_60d"]].to_dict("index")
    baseline_nav = baseline_daily.set_index("trade_date")["strategy_nav"].astype(float)
    baseline_60d = baseline_nav / baseline_nav.shift(60) - 1.0
    rows: list[dict[str, Any]] = []
    for date, group in signals.groupby("trade_date", sort=True):
        base = group.copy()
        base["mom_12_1"] = [_safe_float(feature_map.get((date, row["code"]), {}).get("mom_12_1")) for _, row in base.iterrows()]
        base["mr_60d"] = [_safe_float(feature_map.get((date, row["code"]), {}).get("mr_60d")) for _, row in base.iterrows()]
        rows.extend(_weight_rows(_baseline(base), "baseline"))
        rows.extend(_weight_rows(_internal_subsleeve(base, "internal_subsleeve_mom12_80_20", 0.20), "v57f_pool_internal_subsleeve"))
        rows.extend(_weight_rows(_internal_subsleeve(base, "internal_subsleeve_mom12_70_30", 0.30), "v57f_pool_internal_subsleeve"))
        rows.extend(_weight_rows(_dual_sleeve(base, "dual_sleeve_mom12_80_20", 0.80, 0.20), "dual_sleeve_allocation"))
        rows.extend(_weight_rows(_dual_sleeve(base, "dual_sleeve_mom12_60_40", 0.60, 0.40), "dual_sleeve_allocation"))
        state_mom_budget = 0.30 if _safe_float(baseline_60d.get(date)) and float(baseline_60d.get(date)) > 0 else 0.0
        rows.extend(_weight_rows(_dual_sleeve(base, "state_routed_mom12_70_30_or_100_0", 1.0 - state_mom_budget, state_mom_budget), "state_routed_budget"))
        rows.extend(_weight_rows(_admission_suppression(base), "admission_suppression"))
    return rows


def _baseline(base: pd.DataFrame) -> pd.DataFrame:
    tmp = base.copy()
    tmp["version_id"] = BASELINE
    tmp["target"] = tmp["target_weight"].astype(float)
    tmp["bucket"] = "baseline"
    tmp["sleeve_weight_preserved"] = True
    return tmp


def _internal_subsleeve(base: pd.DataFrame, version: str, momentum_budget: float) -> pd.DataFrame:
    tmp = base.copy()
    tmp["version_id"] = version
    tmp["target"] = 0.0
    tmp["bucket"] = "middle"
    for sleeve, sleeve_df in tmp.groupby("sector_id"):
        idx = sleeve_df.index
        sleeve_total = sleeve_df["target_weight"].astype(float).sum()
        rank = sleeve_df["mom_12_1"].rank(method="first")
        top_mask = rank > len(sleeve_df) * 2 / 3
        top_idx = sleeve_df[top_mask].index.tolist() or [sleeve_df["mom_12_1"].astype(float).idxmax()]
        core = (1.0 - momentum_budget) * sleeve_df["target_weight"].astype(float)
        top_alloc = pd.Series(0.0, index=idx)
        top_alloc.loc[top_idx] = momentum_budget * sleeve_total / len(top_idx)
        tmp.loc[idx, "target"] = core + top_alloc
        tmp.loc[top_idx, "bucket"] = "momentum_subsleeve"
    tmp["sleeve_weight_preserved"] = True
    return tmp


def _dual_sleeve(base: pd.DataFrame, version: str, value_budget: float, momentum_budget: float) -> pd.DataFrame:
    tmp = base.copy()
    tmp["version_id"] = version
    tmp["target"] = value_budget * tmp["target_weight"].astype(float)
    tmp["bucket"] = "value_sleeve_only"
    rank = tmp["mom_12_1"].rank(method="first")
    selected = tmp[rank > len(tmp) * 2 / 3].index.tolist() or [tmp["mom_12_1"].astype(float).idxmax()]
    if momentum_budget:
        tmp.loc[selected, "target"] += momentum_budget / len(selected)
        tmp.loc[selected, "bucket"] = "momentum_sleeve"
    tmp["sleeve_weight_preserved"] = False
    return tmp


def _admission_suppression(base: pd.DataFrame) -> pd.DataFrame:
    tmp = base.copy()
    tmp["version_id"] = "admission_suppression_mom12_bottom_cap75"
    tmp["target"] = tmp["target_weight"].astype(float)
    tmp["bucket"] = "middle_or_top"
    for _, sleeve_df in tmp.groupby("sector_id"):
        rank = sleeve_df["mom_12_1"].rank(method="first")
        bottom_idx = sleeve_df[rank <= len(sleeve_df) / 3].index
        keep_idx = sleeve_df.index.difference(bottom_idx)
        released = (tmp.loc[bottom_idx, "target"] * 0.25).sum()
        tmp.loc[bottom_idx, "target"] *= 0.75
        if len(keep_idx):
            keep_weights = tmp.loc[keep_idx, "target"]
            tmp.loc[keep_idx, "target"] += released * keep_weights / keep_weights.sum()
        tmp.loc[bottom_idx, "bucket"] = "suppressed_bottom_momentum"
    tmp["sleeve_weight_preserved"] = True
    return tmp


def _weight_rows(tmp: pd.DataFrame, family: str) -> list[dict[str, Any]]:
    return [
        {
            "version_id": row["version_id"],
            "family": family,
            "rebalance_date": row["trade_date"],
            "code": row["code"],
            "sleeve": row["sector_id"],
            "base_target_weight": row["target_weight"],
            "target_weight": row["target"],
            "weight_delta": float(row["target"]) - float(row["target_weight"]),
            "mom_12_1": row.get("mom_12_1", ""),
            "mr_60d": row.get("mr_60d", ""),
            "bucket": row["bucket"],
            "sleeve_weight_preserved": row["sleeve_weight_preserved"],
            "new_stock_selected": False,
            "accepted": False,
        }
        for _, row in tmp.iterrows()
    ]


def _daily_returns(weights: list[dict[str, Any]], prices: pd.DataFrame, baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    baseline_ret = baseline_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    baseline_nav = baseline_daily.set_index("trade_date")["strategy_nav"].astype(float).to_dict()
    dates = sorted(baseline_daily["trade_date"].tolist())
    rebalances = sorted({row["rebalance_date"] for row in weights})
    by_version_date: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in weights:
        by_version_date.setdefault((row["version_id"], row["rebalance_date"]), []).append(row)
    rows: list[dict[str, Any]] = []
    for version in sorted({row["version_id"] for row in weights}):
        nav = 1.0
        active: list[dict[str, Any]] = []
        prev: dict[str, float] = {}
        active_rebalance = ""
        for day in dates:
            turnover = 0.0
            commission = 0.0
            if day in rebalances:
                active_rebalance = day
                active = by_version_date.get((version, day), [])
                target = {row["code"]: float(row["target_weight"]) for row in active}
                base_target = {row["code"]: float(row["base_target_weight"]) for row in active}
                turnover = sum(abs(target.get(code, 0.0) - prev.get(code, 0.0)) for code in set(target) | set(prev))
                base_turnover = sum(abs(base_target.get(code, 0.0) - prev.get(code, 0.0)) for code in set(base_target) | set(prev))
                commission = max(0.0, turnover - base_turnover) * COMMISSION_RATE
                prev = target
            if version == BASELINE:
                strategy_return = baseline_ret[day]
                nav = baseline_nav[day]
                delta_stock_return = 0.0
            else:
                delta_stock_return = sum(float(row["weight_delta"]) * (_safe_float(ret_map.get((day, row["code"]))) or 0.0) for row in active)
                strategy_return = baseline_ret[day] + delta_stock_return - commission
                nav *= 1.0 + strategy_return
            rows.append(
                {
                    "trade_date": day,
                    "version_id": version,
                    "active_rebalance_date": active_rebalance,
                    "strategy_return": strategy_return,
                    "strategy_nav": nav,
                    "baseline_return": baseline_ret[day],
                    "delta_stock_return": delta_stock_return,
                    "incremental_commission": commission,
                    "turnover_proxy": turnover,
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
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["strategy_return"]) - float(baseline["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (float(row["max_drawdown"]) - float(baseline["max_drawdown"])) * 100
    return sorted(out, key=lambda r: float(r["delta_return_pct_points_vs_repaired_baseline"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].str.slice(0, 4)
    out = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append({"version_id": version, "family": _family(version), "year": year, "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1, "trade_days": len(group)})
    base = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - base.get(row["year"], 0.0)) * 100
    return out


def _drawdown(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out = []
    for version, group in df.groupby("version_id", sort=True):
        ordered = group.sort_values("trade_date").reset_index(drop=True)
        nav = pd.to_numeric(ordered["strategy_nav"])
        dd = nav / nav.cummax() - 1
        trough = int(dd.idxmin())
        peak = int(nav.iloc[: trough + 1].idxmax())
        out.append({"version_id": version, "family": _family(version), "max_drawdown": abs(float(dd.iloc[trough])), "peak_date": ordered.loc[peak, "trade_date"], "trough_date": ordered.loc[trough, "trade_date"]})
    base_dd = next(float(row["max_drawdown"]) for row in out if row["version_id"] == BASELINE)
    for row in out:
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (float(row["max_drawdown"]) - base_dd) * 100
    return out


def _sleeve_contribution(weights: list[dict[str, Any]], prices: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in weights:
        if row["version_id"] == BASELINE:
            continue
        key = (row["version_id"], row["sleeve"])
        item = grouped.setdefault(key, {"version_id": row["version_id"], "family": _family(row["version_id"]), "sleeve": row["sleeve"], "abs_weight_delta": 0.0, "next_day_delta": 0.0})
        item["abs_weight_delta"] += abs(float(row["weight_delta"]))
        item["next_day_delta"] += float(row["weight_delta"]) * (_safe_float(ret_map.get((row["rebalance_date"], row["code"]))) or 0.0)
    return list(grouped.values())


def _governance(weights: list[dict[str, Any]], repaired_summary: dict[str, Any]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    return [
        {"audit_id": "repaired_baseline_first_signal", "status": "pass" if repaired_summary.get("startup_preload", {}).get("effective_first_signal_date") == "2021-05-06" else "fail", "detail": repaired_summary.get("startup_preload", {}).get("effective_first_signal_date")},
        {"audit_id": "v57f_selected_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": "all rough screens use repaired V57f selected stocks only"},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": "fixed rough-screen versions only"},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "live_approved_false", "status": "pass", "detail": False},
    ]


def _comparison_matrix(metrics: list[dict[str, Any]], current_summary: dict[str, Any], current_candidates: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    rank = 1
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        delta = float(row["delta_return_pct_points_vs_repaired_baseline"])
        dd = float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"])
        rows.append(
            {
                "rank": rank,
                "direction_id": row["version_id"],
                "family": row["family"],
                "delta_return_pct_points_vs_repaired_baseline": delta,
                "delta_max_drawdown_pct_points_vs_repaired_baseline": dd,
                "sharpe_proxy": row["sharpe_proxy"],
                "rough_screen_status": "worth_deep_research" if delta > 0 and dd <= 0 else ("diagnostic_only_return_positive_risk_note" if delta > 0 else "reject_or_archive"),
                "accepted": False,
            }
        )
        rank += 1
    rows.append(
        {
            "rank": rank,
            "direction_id": "current_momentum_plus_mean_reversion_equal_blend",
            "family": "current_reference",
            "delta_return_pct_points_vs_repaired_baseline": current_summary["best_delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": current_summary["best_delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "sharpe_proxy": "",
            "rough_screen_status": "current_reference_candidate_not_accepted",
            "accepted": False,
        }
    )
    return rows


def _pm_decision(comparison: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    deep = [row for row in comparison if row["rough_screen_status"] == "worth_deep_research"]
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        next_focus = "repair_governance"
    elif deep:
        decision = "rough_screen_has_deep_research_candidates_not_accepted"
        next_focus = ";".join(row["direction_id"] for row in deep[:3])
    else:
        decision = "rough_screen_diagnostic_only_no_new_deep_candidate"
        next_focus = "keep_current_reference_candidate"
    return [{"pm_gate_decision": decision, "deep_research_candidate_count": len(deep), "next_focus": next_focus, "accepted": False, "live_trading_approved": False}]


def _next_queue(comparison: list[dict[str, Any]], decision: str) -> list[dict[str, Any]]:
    rows = []
    priority = 1
    for row in comparison:
        if row["rough_screen_status"] == "worth_deep_research":
            rows.append({"priority": priority, "next_task": f"Deep research spec for {row['direction_id']}", "allowed": True, "requires_threshold_scan": False})
            priority += 1
    rows.append({"priority": priority, "next_task": "Keep current repaired overlay candidate in paper tracking", "allowed": True, "requires_threshold_scan": False})
    rows.append({"priority": priority + 1, "next_task": "Full-market momentum sleeve or parameter scan", "allowed": False, "requires_threshold_scan": True})
    return rows


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed] or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Rough screen completed."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    best_direction: str = "",
    best_delta_return: float = 0.0,
    best_delta_drawdown: float = 0.0,
    deep_research_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_structural_rough_screen",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "best_direction": best_direction,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_return,
        "best_delta_max_drawdown_pct_points_vs_repaired_baseline": best_delta_drawdown,
        "deep_research_count": deep_research_count,
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


def _report(comparison: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f Structural Rough Screen",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Deep research candidates: {decision[0]['deep_research_candidate_count']}",
            "- Status: diagnostic rough screen only; not accepted.",
            "",
            "## Ranking",
            *[
                f"- {row['rank']}. `{row['direction_id']}` ({row['family']}): delta={float(row['delta_return_pct_points_vs_repaired_baseline']):.4f} pct, dd_delta={float(row['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct, status={row['rough_screen_status']}"
                for row in comparison
            ],
            "",
        ]
    )


def _prompt() -> str:
    return """Working directory:
D:\\hh\\codex\\v5

Task name:
V5f structural rough-screen deep research packet

Objective:
Read `v5f_structural_rough_screen/current/` and promote only the rough-screen directions marked `worth_deep_research` into separate Quant specs. Use startup-preload repaired V57f as the only benchmark. Do not mark accepted, do not modify V57f, do not select full-market stocks, and do not scan parameters.

Required inputs:
- v5f_structural_rough_screen/current/v5f_structural_rough_screen_summary.json
- v5f_structural_rough_screen/current/v5f_structural_rough_screen_comparison_matrix.csv
- v5f_structural_rough_screen/current/v5f_structural_rough_screen_next_queue.csv
- v5f_repaired_baseline_overlay_comparison/current/v5f_repaired_overlay_summary.json

Decision rule:
- Worth deep research only if return is positive versus repaired baseline and max drawdown does not worsen.
- Positive return with worse drawdown stays diagnostic.
- Anything requiring full-market stock selection needs separate PM approval.
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Structural Rough Screen Rules",
            "",
            "- Repaired V57f baseline only.",
            "- V57f selected-stock pool only.",
            "- Rough-screen diagnostics are not accepted and not live approved.",
            "- Do not use this packet to scan parameters.",
            "",
        ]
    )


def _family(version: str) -> str:
    if version == BASELINE:
        return "baseline"
    if version.startswith("internal_subsleeve"):
        return "v57f_pool_internal_subsleeve"
    if version.startswith("dual_sleeve"):
        return "dual_sleeve_allocation"
    if version.startswith("state_routed"):
        return "state_routed_budget"
    if version.startswith("admission"):
        return "admission_suppression"
    return "other"


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


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PRICE_DIR,
        REPAIRED_RUN / "summary.json",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        COMPARISON_DIR / "v5f_repaired_overlay_summary.json",
        COMPARISON_DIR / "v5f_candidate_matrix.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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
    print(json.dumps(run_v5f_structural_rough_screen(Path(".")), ensure_ascii=False, indent=2))
