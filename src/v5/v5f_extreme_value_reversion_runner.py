from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_quality_value_mean_reversion_runner import (
    BACKTEST_END,
    BACKTEST_START,
    BASELINE,
    CHAMPION,
    DEEP_DIR,
    REPAIRED_RUN,
    _daily_returns,
    _governance_audit,
    _load_prices,
    _metrics,
    _momentum_targets,
    _pit_audit,
    _safe_float,
    _target_turnover,
    _yearly,
)


OUT_DIR = Path("v5f_extreme_value_reversion") / "current"

EXTREME_60 = "extreme_60d_value_repair_70_30"
EXTREME_120 = "extreme_120d_value_repair_70_30"
COMBO_70_20_10 = "core70_mom20_extreme60_10"
COMBO_80_10_10 = "core80_mom10_extreme60_10"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_extreme_value_reversion(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_extreme_value_reversion_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_extreme_value_reversion_summary.json", summary)
        return summary

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    repaired_summary = _read_json(root / REPAIRED_RUN / "summary.json")
    deep_summary = _read_json(root / DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")

    signals = signals[(signals["trade_date"] >= BACKTEST_START) & (signals["trade_date"] <= BACKTEST_END)].copy()
    baseline_daily = baseline_daily[
        (baseline_daily["trade_date"] >= BACKTEST_START) & (baseline_daily["trade_date"] <= BACKTEST_END)
    ].copy()

    spec = _spec()
    data_gate = _data_gate(signals)
    weights, events, attribution = _build_weight_event_and_attribution(signals, prices, baseline_daily)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    comparison = _comparison(metrics, deep_summary)
    event_summary = _event_summary(events)
    sleeve_summary = _sleeve_summary(attribution)
    governance = _governance_audit(repaired_summary, weights)
    pit = _pit_audit() + [
        {
            "audit_id": "fundamental_proxy_visible_at_rebalance",
            "status": "pass",
            "detail": "Uses repaired V57f rebalance signal fields only.",
        }
    ]
    decision = _pm_decision(comparison, governance, data_gate)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_extreme_value_reversion_spec.csv", spec)
    _write_csv(out / "v5f_extreme_value_reversion_data_gate.csv", data_gate)
    _write_csv(out / "v5f_extreme_value_reversion_weight_log.csv", weights)
    _write_csv(out / "v5f_extreme_value_reversion_candidate_events.csv", events)
    _write_csv(out / "v5f_extreme_value_reversion_fundamental_attribution.csv", attribution)
    _write_csv(out / "v5f_extreme_value_reversion_event_summary.csv", event_summary)
    _write_csv(out / "v5f_extreme_value_reversion_sleeve_summary.csv", sleeve_summary)
    _write_csv(out / "v5f_extreme_value_reversion_daily_returns.csv", daily)
    _write_csv(out / "v5f_extreme_value_reversion_metrics.csv", metrics)
    _write_csv(out / "v5f_extreme_value_reversion_yearly.csv", yearly)
    _write_csv(out / "v5f_extreme_value_reversion_comparison.csv", comparison)
    _write_csv(out / "v5f_extreme_value_reversion_governance_audit.csv", governance)
    _write_csv(out / "v5f_extreme_value_reversion_pit_audit.csv", pit)
    _write_csv(out / "v5f_extreme_value_reversion_pm_decision.csv", decision)
    _write_csv(out / "v5f_extreme_value_reversion_next_queue.csv", next_queue)
    _write_csv(out / "v5f_extreme_value_reversion_blockers.csv", blockers_out)
    (out / "v5f_extreme_value_reversion_report.md").write_text(
        _report(metrics, comparison, event_summary, sleeve_summary, decision, data_gate),
        encoding="utf-8",
    )
    (out / "v5f_extreme_value_reversion_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_variant(comparison)
    champion = next(row for row in comparison if row["version_id"] == CHAMPION)
    summary = _summary(
        "completed_v5f_extreme_value_reversion",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=decision[0]["primary_candidate"],
        best_variant=best["version_id"],
        best_delta_return=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        champion_delta_return=float(champion["delta_return_pct_points_vs_repaired_baseline"]),
        best_incremental_vs_champion=float(best["incremental_delta_return_vs_champion"]),
        usable_space=decision[0]["usable_space"],
    )
    _write_json(out / "v5f_extreme_value_reversion_summary.json", summary)
    return summary


def _spec() -> list[dict[str, Any]]:
    return [
        {
            "version_id": CHAMPION,
            "rule": "Current V5f reference: V57f repaired selected pool, same-sleeve 12-1 momentum 70/30.",
            "accepted": False,
        },
        {
            "version_id": EXTREME_60,
            "rule": "70% base plus 30% same-sleeve allocation to names that are 60d oversold, fundamentally intact, valuation-proxy cheap, and short-term momentum stabilized.",
            "accepted": False,
        },
        {
            "version_id": EXTREME_120,
            "rule": "70% base plus 30% same-sleeve allocation to names that are 120d oversold, fundamentally intact, valuation-proxy cheap, and short-term momentum stabilized.",
            "accepted": False,
        },
        {
            "version_id": COMBO_70_20_10,
            "rule": "70% V57f core, 20% same-sleeve 12-1 momentum, 10% extreme 60d value-repair satellite.",
            "accepted": False,
        },
        {
            "version_id": COMBO_80_10_10,
            "rule": "80% V57f core, 10% same-sleeve 12-1 momentum, 10% extreme 60d value-repair satellite.",
            "accepted": False,
        },
    ]


def _data_gate(signals: pd.DataFrame) -> list[dict[str, Any]]:
    required = {
        "score": "fundamental_quality_proxy",
        "cash_generation_yield": "valuation_cashflow_proxy",
        "dividend_yield_decimal": "valuation_dividend_proxy",
        "sector_id": "industry_or_sleeve_proxy",
    }
    rows: list[dict[str, Any]] = []
    for field, role in required.items():
        coverage = 0.0 if field not in signals else signals[field].notna().mean()
        rows.append(
            {
                "field": field,
                "role": role,
                "coverage": coverage,
                "status": "pass" if coverage >= 0.95 else "review",
                "detail": "available in repaired V57f signal table",
            }
        )
    unavailable = [
        ("price_to_book", "direct_valuation_metric"),
        ("roe", "direct_profitability_metric"),
        ("revenue_growth", "single_name_fundamental_change"),
        ("net_profit_growth", "single_name_fundamental_change"),
        ("industry_financial_statement_growth", "industry_fundamental_change"),
    ]
    for field, role in unavailable:
        rows.append(
            {
                "field": field,
                "role": role,
                "coverage": 0.0,
                "status": "needs_data_for_formal_financial_statement_gate",
                "detail": "not present in repaired V57f signal table; current run uses PIT proxies only",
            }
        )
    return rows


def _build_weight_event_and_attribution(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    baseline_daily: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    feature = prices.set_index(["date", "code"])[
        ["mom_12_1", "ret_20d_lagged", "ret_60d_lagged", "ret_120d_lagged"]
    ].to_dict("index")
    dates = sorted(baseline_daily["trade_date"].tolist())
    pools = {date: group.copy() for date, group in signals.groupby("trade_date", sort=True)}
    history = _fundamental_history(signals)

    weights: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    attribution: list[dict[str, Any]] = []
    current_targets: dict[str, dict[str, float]] = {}
    current_meta: dict[str, dict[str, dict[str, Any]]] = {}
    active_rebalance = ""
    active_pool = pd.DataFrame()

    versions = [CHAMPION, EXTREME_60, EXTREME_120, COMBO_70_20_10, COMBO_80_10_10]
    for day in dates:
        if day in pools:
            active_rebalance = day
            active_pool = pools[day].copy()
            active_pool["base_target_weight"] = active_pool["target_weight"].astype(float)
            active_pool["quality_value_score"] = pd.to_numeric(active_pool["score"], errors="coerce")
            current_targets[CHAMPION] = _momentum_targets(active_pool, feature, day)
            current_meta[CHAMPION] = {}
            current_targets[EXTREME_60], current_meta[EXTREME_60] = _extreme_targets(
                active_pool, feature, history, day, "ret_60d_lagged", 0.70, 0.30, 0.0
            )
            current_targets[EXTREME_120], current_meta[EXTREME_120] = _extreme_targets(
                active_pool, feature, history, day, "ret_120d_lagged", 0.70, 0.30, 0.0
            )
            current_targets[COMBO_70_20_10], current_meta[COMBO_70_20_10] = _extreme_targets(
                active_pool, feature, history, day, "ret_60d_lagged", 0.70, 0.10, 0.20
            )
            current_targets[COMBO_80_10_10], current_meta[COMBO_80_10_10] = _extreme_targets(
                active_pool, feature, history, day, "ret_60d_lagged", 0.80, 0.10, 0.10
            )
            for version in versions:
                selected_codes = [code for code, meta in current_meta.get(version, {}).items() if meta["selected"]]
                events.append(
                    {
                        "trade_date": day,
                        "version_id": version,
                        "event_type": "official_v57f_rebalance",
                        "selected_extreme_repair_count": len(selected_codes),
                        "selected_codes": ";".join(selected_codes),
                        "target_turnover": 0.0,
                        "accepted": False,
                    }
                )
                for code in selected_codes:
                    row = current_meta[version][code]
                    attribution.append({"trade_date": day, "version_id": version, "code": code, **row})

        if active_pool.empty:
            continue

        base = {row["code"]: float(row["base_target_weight"]) for _, row in active_pool.iterrows()}
        for version in versions:
            target = current_targets[version]
            for _, row in active_pool.iterrows():
                code = row["code"]
                feature_row = feature.get((day, code), {})
                meta = current_meta.get(version, {}).get(code, {})
                weights.append(
                    {
                        "trade_date": day,
                        "active_rebalance_date": active_rebalance,
                        "version_id": version,
                        "code": code,
                        "sleeve": row["sector_id"],
                        "quality_value_score": row["quality_value_score"],
                        "selected_rank": row["selected_rank"],
                        "base_target_weight": base[code],
                        "target_weight": target.get(code, base[code]),
                        "weight_delta": target.get(code, base[code]) - base[code],
                        "mom_12_1": _safe_float(feature_row.get("mom_12_1")),
                        "ret_20d_lagged": _safe_float(feature_row.get("ret_20d_lagged")),
                        "ret_60d_lagged": _safe_float(feature_row.get("ret_60d_lagged")),
                        "ret_120d_lagged": _safe_float(feature_row.get("ret_120d_lagged")),
                        "extreme_repair_selected": bool(meta.get("selected", False)),
                        "fundamental_status": meta.get("fundamental_status", ""),
                        "valuation_status": meta.get("valuation_status", ""),
                        "momentum_stabilized": meta.get("momentum_stabilized", ""),
                        "locked_pool_only": True,
                        "new_stock_selected": False,
                        "accepted": False,
                    }
                )
    return weights, events, attribution


def _fundamental_history(signals: pd.DataFrame) -> dict[str, Any]:
    df = signals.copy()
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    code_prev: dict[tuple[str, str], float | None] = {}
    for code, group in df.sort_values("trade_date").groupby("code"):
        prev: float | None = None
        for _, row in group.iterrows():
            code_prev[(row["trade_date"], code)] = prev
            prev = _safe_float(row["score"])
    sleeve_median = df.groupby(["trade_date", "sector_id"])["score"].median().to_dict()
    sleeve_prev: dict[tuple[str, str], float | None] = {}
    for sleeve in df["sector_id"].dropna().unique():
        prev = None
        dates = sorted(df.loc[df["sector_id"] == sleeve, "trade_date"].unique().tolist())
        for date in dates:
            sleeve_prev[(date, sleeve)] = prev
            prev = _safe_float(sleeve_median.get((date, sleeve)))
    return {"code_prev_score": code_prev, "sleeve_median": sleeve_median, "sleeve_prev_score": sleeve_prev}


def _extreme_targets(
    pool: pd.DataFrame,
    feature: dict[tuple[str, str], dict[str, Any]],
    history: dict[str, Any],
    day: str,
    return_feature: str,
    core_budget: float,
    extreme_budget: float,
    momentum_budget: float,
) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    targets: dict[str, float] = {}
    meta: dict[str, dict[str, Any]] = {}
    for sleeve, group in pool.groupby("sector_id"):
        sleeve_total = group["base_target_weight"].astype(float).sum()
        tmp = group.copy()
        tmp["_ret"] = tmp["code"].map(lambda code: _safe_float(feature.get((day, code), {}).get(return_feature)))
        tmp["_ret20"] = tmp["code"].map(lambda code: _safe_float(feature.get((day, code), {}).get("ret_20d_lagged")))
        tmp["_mom"] = tmp["code"].map(lambda code: _safe_float(feature.get((day, code), {}).get("mom_12_1")))
        tmp["_cash_yield"] = pd.to_numeric(tmp["cash_generation_yield"], errors="coerce")
        tmp["_dividend_yield"] = pd.to_numeric(tmp["dividend_yield_decimal"], errors="coerce")
        tmp["_score"] = pd.to_numeric(tmp["quality_value_score"], errors="coerce")
        ret_floor = -0.05 if return_feature == "ret_60d_lagged" else -0.08
        ret_cut = min(_nan_quantile(tmp["_ret"], 1 / 3), ret_floor)
        score_med = tmp["_score"].median()
        cash_med = tmp["_cash_yield"].median()
        dividend_med = tmp["_dividend_yield"].median()
        mom_ranks = tmp["_mom"].rank(method="first", ascending=False)
        mom_selected = tmp.loc[mom_ranks <= max(1, math.ceil(len(tmp) / 3)), "code"].tolist()
        selected: list[str] = []
        for _, row in tmp.iterrows():
            code = row["code"]
            ret_value = _safe_float(row["_ret"])
            ret20 = _safe_float(row["_ret20"])
            score = _safe_float(row["_score"])
            cash_yield = _safe_float(row["_cash_yield"])
            dividend_yield = _safe_float(row["_dividend_yield"])
            prior_score = history["code_prev_score"].get((day, code))
            sleeve_score = _safe_float(history["sleeve_median"].get((day, sleeve)))
            prior_sleeve_score = history["sleeve_prev_score"].get((day, sleeve))
            score_change = None if prior_score is None or score is None else score - prior_score
            sleeve_score_change = None if prior_sleeve_score is None or sleeve_score is None else sleeve_score - prior_sleeve_score
            idio_bad = (
                score_change is not None
                and sleeve_score_change is not None
                and score_change < -0.25
                and score_change < sleeve_score_change - 0.10
            )
            industry_bad = sleeve_score_change is not None and sleeve_score_change < -0.20
            fundamental_intact = bool(
                score is not None
                and score >= score_med
                and not idio_bad
                and (score_change is None or score_change >= -0.25 or industry_bad)
            )
            cheap = bool(
                (cash_yield is not None and cash_yield >= cash_med)
                or (dividend_yield is not None and dividend_yield >= dividend_med)
            )
            oversold = bool(ret_value is not None and ret_value <= ret_cut)
            divisor = 3 if return_feature == "ret_60d_lagged" else 6
            stabilized = bool(
                ret_value is not None
                and ret20 is not None
                and (ret20 >= ret_value / divisor or ret20 >= 0)
            )
            is_selected = oversold and fundamental_intact and cheap and stabilized
            if is_selected:
                selected.append(code)
            if idio_bad:
                fundamental_status = "single_name_fundamental_proxy_deteriorated"
            elif industry_bad:
                fundamental_status = "industry_or_sleeve_proxy_deteriorated"
            elif fundamental_intact:
                fundamental_status = "fundamental_proxy_intact"
            else:
                fundamental_status = "not_fundamental_intact"
            if cheap:
                valuation_status = "valuation_proxy_cheap"
            else:
                valuation_status = "not_cheap_by_cash_or_dividend_yield"
            meta[code] = {
                "sleeve": sleeve,
                "selected": is_selected,
                "return_feature": return_feature,
                "recent_return": ret_value,
                "ret20_lagged": ret20,
                "ret_cut": ret_cut,
                "oversold": oversold,
                "quality_value_score": score,
                "prior_quality_value_score": prior_score,
                "quality_value_score_change": score_change,
                "sleeve_score": sleeve_score,
                "prior_sleeve_score": prior_sleeve_score,
                "sleeve_score_change": sleeve_score_change,
                "fundamental_status": fundamental_status,
                "valuation_status": valuation_status,
                "momentum_stabilized": stabilized,
                "classification": _classification(is_selected, idio_bad, industry_bad, cheap, oversold, stabilized),
            }
        if not selected:
            extreme_core_budget = core_budget + extreme_budget
        else:
            extreme_core_budget = core_budget
        for _, row in tmp.iterrows():
            code = row["code"]
            target = extreme_core_budget * float(row["base_target_weight"])
            if selected and code in selected:
                target += extreme_budget * sleeve_total / len(selected)
            if momentum_budget > 0:
                if mom_selected and code in mom_selected:
                    target += momentum_budget * sleeve_total / len(mom_selected)
                elif not mom_selected:
                    target += momentum_budget * float(row["base_target_weight"])
            targets[code] = target
    return targets, meta


def _classification(
    selected: bool,
    idio_bad: bool,
    industry_bad: bool,
    cheap: bool,
    oversold: bool,
    stabilized: bool,
) -> str:
    if selected:
        return "candidate_true_undervaluation_proxy"
    if idio_bad:
        return "exclude_single_name_fundamental_deterioration_proxy"
    if industry_bad:
        return "exclude_or_review_industry_deterioration_proxy"
    if oversold and cheap and not stabilized:
        return "exclude_falling_knife_momentum_not_stabilized"
    if oversold and not cheap:
        return "exclude_oversold_not_cheap"
    return "not_extreme_repair_candidate"


def _comparison(metrics: list[dict[str, Any]], deep_summary: dict[str, Any]) -> list[dict[str, Any]]:
    champion = next(row for row in metrics if row["version_id"] == CHAMPION)
    official_champion_delta = float(deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"])
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        rows.append(
            {
                "version_id": row["version_id"],
                "delta_return_pct_points_vs_repaired_baseline": row[
                    "delta_return_pct_points_vs_repaired_baseline"
                ],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row[
                    "delta_max_drawdown_pct_points_vs_repaired_baseline"
                ],
                "incremental_delta_return_vs_champion": float(
                    row["delta_return_pct_points_vs_repaired_baseline"]
                )
                - float(champion["delta_return_pct_points_vs_repaired_baseline"]),
                "incremental_delta_drawdown_vs_champion": float(
                    row["delta_max_drawdown_pct_points_vs_repaired_baseline"]
                )
                - float(champion["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
                "official_registered_champion_delta_return": official_champion_delta,
                "incremental_delta_return_vs_official_registered_champion": float(
                    row["delta_return_pct_points_vs_repaired_baseline"]
                )
                - official_champion_delta,
                "accepted": False,
            }
        )
    return rows


def _event_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(events)
    rows = []
    for version, group in df.groupby("version_id", sort=True):
        rows.append(
            {
                "version_id": version,
                "rebalance_events": len(group),
                "total_selected_extreme_repair_events": int(
                    pd.to_numeric(group["selected_extreme_repair_count"], errors="coerce").sum()
                ),
                "avg_selected_per_rebalance": pd.to_numeric(
                    group["selected_extreme_repair_count"], errors="coerce"
                ).mean(),
            }
        )
    return rows


def _sleeve_summary(attribution: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not attribution:
        return [
            {
                "version_id": "none",
                "sleeve": "none",
                "selected_events": 0,
                "dominant_classification": "no_extreme_repair_candidate",
            }
        ]
    df = pd.DataFrame(attribution)
    rows = []
    for (version, sleeve), group in df.groupby(["version_id", "sleeve"], sort=True):
        rows.append(
            {
                "version_id": version,
                "sleeve": sleeve,
                "selected_events": len(group),
                "unique_codes": group["code"].nunique(),
                "avg_recent_return": pd.to_numeric(group["recent_return"], errors="coerce").mean(),
                "avg_score_change": pd.to_numeric(group["quality_value_score_change"], errors="coerce").mean(),
                "avg_sleeve_score_change": pd.to_numeric(group["sleeve_score_change"], errors="coerce").mean(),
                "dominant_classification": group["classification"].mode().iloc[0],
            }
        )
    return rows


def _pm_decision(
    comparison: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    formal_financial_data_ready = all(row["status"] == "pass" for row in data_gate)
    best = _best_variant(comparison)
    champion = next(row for row in comparison if row["version_id"] == CHAMPION)
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        primary = ""
        usable = "no"
        rationale = "Governance audit failed."
    elif (
        best["version_id"] != CHAMPION
        and float(best["incremental_delta_return_vs_champion"]) > 0.5
        and float(best["incremental_delta_drawdown_vs_champion"]) <= 0.1
    ):
        decision = "extreme_value_reversion_positive_ready_for_pm_quant_review_not_accepted"
        primary = best["version_id"]
        usable = "yes_candidate"
        rationale = "Extreme value-repair signal improves over current momentum reference."
    elif best["version_id"] != CHAMPION and float(best["incremental_delta_return_vs_champion"]) > 0:
        decision = "extreme_value_reversion_positive_but_insufficient_keep_momentum_primary"
        primary = CHAMPION
        usable = "limited_diagnostic"
        rationale = "Extreme value-repair signal adds a small positive edge but not enough to replace momentum."
    else:
        decision = "extreme_value_reversion_diagnostic_only_keep_momentum_primary"
        primary = CHAMPION
        usable = "diagnostic_only"
        rationale = "Extreme value-repair signal does not improve over current momentum reference."
    if not formal_financial_data_ready and decision != "blocked_by_governance_issue":
        rationale += " Direct financial-statement fields are not fully available; current attribution uses V57f PIT proxies."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": primary,
            "best_variant": best["version_id"],
            "champion_reference": CHAMPION,
            "best_delta_return_pct_points_vs_repaired_baseline": best[
                "delta_return_pct_points_vs_repaired_baseline"
            ],
            "champion_delta_return_pct_points_vs_repaired_baseline": champion[
                "delta_return_pct_points_vs_repaired_baseline"
            ],
            "best_incremental_delta_return_vs_champion": best["incremental_delta_return_vs_champion"],
            "best_incremental_delta_drawdown_vs_champion": best[
                "incremental_delta_drawdown_vs_champion"
            ],
            "usable_space": usable,
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "Keep internal_subsleeve_mom12_70_30 as primary unless extreme repair formally promotes.",
            "allowed": True,
        },
        {
            "priority": 2,
            "task": "Open formal financial statement data gate for PB, ROE, revenue growth, profit growth, and sector aggregates.",
            "allowed": True,
        },
        {
            "priority": 3,
            "task": "Open PM/Quant review for extreme value repair if positive.",
            "allowed": decision.startswith("extreme_value_reversion_positive_ready"),
        },
        {
            "priority": 4,
            "task": "Use full-market oversold stock selection or scan oversold thresholds.",
            "allowed": False,
        },
    ]


def _best_variant(comparison: list[dict[str, Any]]) -> dict[str, Any]:
    return max(comparison, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [
            {
                "blocker_id": row["audit_id"],
                "severity": "fatal",
                "status": "blocking",
                "description": row["detail"],
            }
            for row in failed
        ]
    return [
        {
            "blocker_id": "none",
            "severity": "none",
            "status": "not_blocking",
            "description": "Extreme value-reversion research completed.",
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    best_variant: str = "",
    best_delta_return: float = 0.0,
    champion_delta_return: float = 0.0,
    best_incremental_vs_champion: float = 0.0,
    usable_space: str = "",
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_extreme_value_reversion",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_candidate": primary_candidate,
        "best_variant": best_variant,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_return,
        "champion_delta_return_pct_points_vs_repaired_baseline": champion_delta_return,
        "best_incremental_delta_return_vs_champion": best_incremental_vs_champion,
        "usable_space": usable_space,
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


def _report(
    metrics: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    event_summary: list[dict[str, Any]],
    sleeve_summary: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Extreme Value-Reversion Diagnostic",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary: `{decision[0]['primary_candidate']}`",
            f"- Best variant: `{decision[0]['best_variant']}`",
            "- Scope: V57f repaired selected pool only; no full-market selection.",
            "- Interpretation: tests extreme oversold plus intact fundamental proxy plus cheap valuation proxy plus stabilizing momentum.",
            "- Status: not accepted; not live approved.",
            "",
            "## Metrics",
            *[
                f"- `{row['version_id']}`: return={float(row['strategy_return']) * 100:.2f}%, "
                f"delta={float(row['delta_return_pct_points_vs_repaired_baseline']):.4f} pct, "
                f"dd_delta={float(row['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct"
                for row in metrics
            ],
            "",
            "## Versus Momentum Champion",
            *[
                f"- `{row['version_id']}`: incremental={float(row['incremental_delta_return_vs_champion']):.4f} pct, "
                f"dd_incremental={float(row['incremental_delta_drawdown_vs_champion']):.4f} pct"
                for row in comparison
            ],
            "",
            "## Event Counts",
            *[
                f"- `{row['version_id']}`: selected_events={row['total_selected_extreme_repair_events']}, "
                f"avg_per_rebalance={float(row['avg_selected_per_rebalance']):.2f}"
                for row in event_summary
            ],
            "",
            "## Sleeve Attribution",
            *[
                f"- `{row['version_id']}` / `{row['sleeve']}`: events={row['selected_events']}, codes={row['unique_codes']}"
                for row in sleeve_summary
            ],
            "",
            "## Data Gate",
            *[f"- `{row['field']}`: {row['status']}" for row in data_gate],
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Extreme Value-Reversion Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- Use V57f repaired selected pool only.",
            "- Extreme value reversion requires oversold, valuation-proxy cheap, fundamental-proxy intact, and momentum stabilization.",
            "- Direct financial statement fields are data-gated separately.",
            "- No V57f core modification, no full-market selection, no accepted/live approval.",
            "",
        ]
    )


def _nan_quantile(series: pd.Series, q: float) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return float(clean.quantile(q)) if len(clean) else 0.0


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        REPAIRED_RUN / "summary.json",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json",
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
    print(json.dumps(run_v5f_extreme_value_reversion(Path(".")), ensure_ascii=False, indent=2))
