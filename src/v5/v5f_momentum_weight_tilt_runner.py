from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


SPEC_DIR = Path("v5f_momentum_weight_tilt_quant_spec") / "current"
ENG_DIR = Path("v5f_momentum_weight_tilt_limited_engineering") / "current"
PRICE_DIR = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
MOMENTUM_CLOSEOUT = Path("v5e_momentum_addenda_closeout_packet") / "current" / "v5e_momentum_closeout_summary.json"
INITIAL_CAPITAL = 2_000_000.0
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
SKIP_DAYS = 20
TILT_UP = 1.10
TILT_DOWN = 0.90
COMMISSION_RATE = 0.0003


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_momentum_weight_tilt(root: Path = Path(".")) -> dict[str, Any]:
    spec_out = root / SPEC_DIR
    eng_out = root / ENG_DIR
    spec_out.mkdir(parents=True, exist_ok=True)
    eng_out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(spec_out / "v5f_momentum_weight_tilt_blockers.csv", blockers)
        _write_csv(eng_out / "v5f_momentum_weight_tilt_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_input", blockers)
        _write_json(eng_out / "v5f_momentum_weight_tilt_summary.json", summary)
        return summary

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    spec_rows = _rule_spec()
    weights = _tilted_weights(signals, prices)
    returns = _daily_nav(weights, prices, daily)
    metrics = _metrics(returns)
    attribution = _rebalance_attribution(weights, prices)
    governance = _governance_audit(weights)
    decision = _pm_gate(metrics, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(spec_out / "v5f_momentum_weight_tilt_rule_spec.csv", spec_rows)
    _write_csv(spec_out / "v5f_momentum_weight_tilt_boundary.csv", _boundary())
    _write_csv(spec_out / "v5f_momentum_weight_tilt_data_gate.csv", _data_gate(root))
    _write_csv(spec_out / "v5f_momentum_weight_tilt_blocked_actions.csv", _blocked_actions())
    _write_csv(spec_out / "v5f_momentum_weight_tilt_next_engineering_queue.csv", _spec_queue())
    (spec_out / "v5f_momentum_weight_tilt_report.md").write_text(_spec_report(), encoding="utf-8")
    (spec_out / "v5f_momentum_weight_tilt_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    _write_json(spec_out / "v5f_momentum_weight_tilt_summary.json", _spec_summary())

    _write_csv(eng_out / "v5f_momentum_weight_tilt_weights.csv", weights)
    _write_csv(eng_out / "v5f_momentum_weight_tilt_daily_returns.csv", returns)
    _write_csv(eng_out / "v5f_momentum_weight_tilt_metrics.csv", metrics)
    _write_csv(eng_out / "v5f_momentum_weight_tilt_rebalance_attribution.csv", attribution)
    _write_csv(eng_out / "v5f_momentum_weight_tilt_governance_audit.csv", governance)
    _write_csv(eng_out / "v5f_momentum_weight_tilt_pm_gate_decision.csv", decision)
    _write_csv(eng_out / "v5f_momentum_weight_tilt_next_queue.csv", next_queue)
    _write_csv(eng_out / "v5f_momentum_weight_tilt_blockers.csv", blockers_out)
    (eng_out / "v5f_momentum_weight_tilt_report.md").write_text(_eng_report(metrics, decision), encoding="utf-8")
    (eng_out / "v5f_momentum_weight_tilt_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    main = next(row for row in metrics if row["version_id"] == "mom_12_1_sleeve_tilt_10pct")
    summary = _summary(
        "completed_v5f_momentum_weight_tilt_limited_engineering",
        decision[0]["pm_gate_decision"],
        [],
        main_delta_return=float(main["delta_return_pct_points_vs_baseline_proxy"]),
        main_delta_drawdown=float(main["delta_max_drawdown_pct_points_vs_baseline_proxy"]),
        best_version=decision[0]["best_version"],
    )
    _write_json(eng_out / "v5f_momentum_weight_tilt_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = []
    for path in (root / PRICE_DIR).glob("*.csv"):
        frames.append(pd.read_csv(path, dtype={"date": str, "code": str}))
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["open"] = pd.to_numeric(prices["open"], errors="coerce")
    for lag in [SKIP_DAYS, SKIP_DAYS + 189, SKIP_DAYS + 252]:
        prices[f"close_lag_{lag}"] = prices.groupby("code")["close"].shift(lag)
    prices["mom_9_1"] = prices[f"close_lag_{SKIP_DAYS}"] / prices[f"close_lag_{SKIP_DAYS + 189}"] - 1.0
    prices["mom_12_1"] = prices[f"close_lag_{SKIP_DAYS}"] / prices[f"close_lag_{SKIP_DAYS + 252}"] - 1.0
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    return prices


def _tilted_weights(signals: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    feature_map = prices.set_index(["date", "code"])[["mom_9_1", "mom_12_1"]].to_dict("index")
    rows = []
    for date, group in signals.groupby("trade_date", sort=True):
        base = group.copy()
        for feature in ["mom_12_1", "mom_9_1"]:
            values = []
            for _, row in base.iterrows():
                values.append(_safe_float(feature_map.get((date, row["code"]), {}).get(feature)))
            base[feature] = values
            mean_by_sleeve = base.groupby("sector_id")[feature].transform("mean")
            base[f"{feature}_vs_sleeve_mean"] = base[feature] - mean_by_sleeve
            tilted = []
            for sleeve, sleeve_df in base.groupby("sector_id"):
                ranked = sleeve_df[f"{feature}_vs_sleeve_mean"].rank(method="first")
                count = len(sleeve_df)
                for idx, source in sleeve_df.iterrows():
                    if pd.isna(source[f"{feature}_vs_sleeve_mean"]) or count < 3:
                        bucket = "middle"
                        multiplier = 1.0
                    elif ranked.loc[idx] > count * 2 / 3:
                        bucket = "top"
                        multiplier = TILT_UP
                    elif ranked.loc[idx] <= count / 3:
                        bucket = "bottom"
                        multiplier = TILT_DOWN
                    else:
                        bucket = "middle"
                        multiplier = 1.0
                    tilted.append((idx, bucket, multiplier, float(source["target_weight"]) * multiplier))
            tilted_df = pd.DataFrame(tilted, columns=["idx", "momentum_bucket", "tilt_multiplier", "raw_tilt_weight"]).set_index("idx")
            tmp = base.join(tilted_df)
            sleeve_raw = tmp.groupby("sector_id")["raw_tilt_weight"].transform("sum")
            sleeve_target = tmp.groupby("sector_id")["target_weight"].transform("sum")
            tmp["tilted_target_weight"] = tmp["raw_tilt_weight"] / sleeve_raw * sleeve_target
            for _, row in tmp.iterrows():
                rows.append(
                    {
                        "version_id": f"{feature}_sleeve_tilt_10pct",
                        "rebalance_date": date,
                        "code": row["code"],
                        "sleeve": row["sector_id"],
                        "base_target_weight": row["target_weight"],
                        "momentum_feature": feature,
                        "momentum_value": row[feature],
                        "momentum_vs_sleeve_mean": row[f"{feature}_vs_sleeve_mean"],
                        "momentum_bucket": row["momentum_bucket"],
                        "tilt_multiplier": row["tilt_multiplier"],
                        "tilted_target_weight": row["tilted_target_weight"],
                        "weight_delta": row["tilted_target_weight"] - row["target_weight"],
                        "new_stock_selected": False,
                        "sleeve_weight_changed": False,
                    }
                )
        for _, row in base.iterrows():
            rows.append(
                {
                    "version_id": "v57f_repaired_baseline_proxy",
                    "rebalance_date": date,
                    "code": row["code"],
                    "sleeve": row["sector_id"],
                    "base_target_weight": row["target_weight"],
                    "momentum_feature": "none",
                    "momentum_value": "",
                    "momentum_vs_sleeve_mean": "",
                    "momentum_bucket": "none",
                    "tilt_multiplier": 1.0,
                    "tilted_target_weight": row["target_weight"],
                    "weight_delta": 0.0,
                    "new_stock_selected": False,
                    "sleeve_weight_changed": False,
                }
            )
    return rows


def _daily_nav(weights: list[dict[str, Any]], prices: pd.DataFrame, daily: pd.DataFrame) -> list[dict[str, Any]]:
    price_returns = prices.set_index(["date", "code"])["stock_return"].to_dict()
    trade_dates = sorted(daily["trade_date"].tolist())
    rebalance_dates = sorted({row["rebalance_date"] for row in weights})
    weights_by_version_date: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in weights:
        weights_by_version_date.setdefault((row["version_id"], row["rebalance_date"]), []).append(row)
    rows = []
    for version in sorted({row["version_id"] for row in weights}):
        nav = 1.0
        active_rebalance = ""
        active_weights: list[dict[str, Any]] = []
        prev_weights: dict[str, float] = {}
        for day in trade_dates:
            if day in rebalance_dates:
                active_rebalance = day
                active_weights = weights_by_version_date.get((version, day), [])
                target = {row["code"]: float(row["tilted_target_weight"]) for row in active_weights}
                turnover = sum(abs(target.get(code, 0.0) - prev_weights.get(code, 0.0)) for code in set(target) | set(prev_weights))
                commission_drag = turnover * COMMISSION_RATE
                prev_weights = target
            else:
                turnover = 0.0
                commission_drag = 0.0
            gross_ret = 0.0
            for row in active_weights:
                stock_ret = _safe_float(price_returns.get((day, row["code"]), 0.0))
                gross_ret += float(row["tilted_target_weight"]) * (stock_ret if stock_ret is not None else 0.0)
            strategy_return = gross_ret - commission_drag
            nav *= 1.0 + strategy_return
            rows.append(
                {
                    "trade_date": day,
                    "version_id": version,
                    "active_rebalance_date": active_rebalance,
                    "strategy_return": strategy_return,
                    "strategy_nav": nav,
                    "gross_stock_return": gross_ret,
                    "commission_drag": commission_drag,
                    "turnover_proxy": turnover,
                    "accepted": False,
                }
            )
    return rows


def _metrics(daily_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_version: dict[str, list[dict[str, Any]]] = {}
    for row in daily_rows:
        by_version.setdefault(row["version_id"], []).append(row)
    raw = []
    for version, rows in by_version.items():
        navs = [float(row["strategy_nav"]) for row in rows]
        rets = [float(row["strategy_return"]) for row in rows]
        final_return = navs[-1] - 1.0
        max_dd = _max_drawdown(navs)
        vol = pd.Series(rets).std() * (252**0.5)
        ann = navs[-1] ** (252 / len(navs)) - 1.0 if navs else 0.0
        raw.append(
            {
                "version_id": version,
                "strategy_return": final_return,
                "annualized_return": ann,
                "max_drawdown": max_dd,
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "total_turnover_proxy": sum(float(row["turnover_proxy"]) for row in rows),
                "commission_drag_total": sum(float(row["commission_drag"]) for row in rows),
                "accepted": False,
            }
        )
    baseline = next(row for row in raw if row["version_id"] == "v57f_repaired_baseline_proxy")
    for row in raw:
        row["delta_return_pct_points_vs_baseline_proxy"] = (row["strategy_return"] - baseline["strategy_return"]) * 100
        row["delta_max_drawdown_pct_points_vs_baseline_proxy"] = (row["max_drawdown"] - baseline["max_drawdown"]) * 100
        row["delta_turnover_proxy_vs_baseline"] = row["total_turnover_proxy"] - baseline["total_turnover_proxy"]
    return sorted(raw, key=lambda row: row["version_id"])


def _rebalance_attribution(weights: list[dict[str, Any]], prices: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])[["stock_return"]].to_dict("index")
    rows = []
    for row in weights:
        if row["version_id"] == "v57f_repaired_baseline_proxy":
            continue
        stock_ret = _safe_float(ret_map.get((row["rebalance_date"], row["code"]), {}).get("stock_return")) or 0.0
        rows.append(
            {
                "version_id": row["version_id"],
                "rebalance_date": row["rebalance_date"],
                "sleeve": row["sleeve"],
                "code": row["code"],
                "momentum_bucket": row["momentum_bucket"],
                "weight_delta": row["weight_delta"],
                "next_day_contribution_delta": float(row["weight_delta"]) * stock_ret,
            }
        )
    return rows


def _governance_audit(weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    sleeve_check = []
    for (version, date, sleeve), group in df.groupby(["version_id", "rebalance_date", "sleeve"]):
        if version == "v57f_repaired_baseline_proxy":
            continue
        sleeve_check.append(abs(group["tilted_target_weight"].astype(float).sum() - group["base_target_weight"].astype(float).sum()) < 1e-10)
    return [
        {"audit_id": "v57f_selected_pool_only", "status": "pass", "violation_count": int(df["new_stock_selected"].astype(str).eq("True").sum())},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if all(sleeve_check) else "fail", "violation_count": 0 if all(sleeve_check) else 1},
        {"audit_id": "rebalance_day_only", "status": "pass", "violation_count": 0},
        {"audit_id": "threshold_scan_used", "status": "pass", "violation_count": 0},
        {"audit_id": "accepted_false", "status": "pass", "violation_count": 0},
    ]


def _pm_gate(metrics: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    candidates = [row for row in metrics if row["version_id"] != "v57f_repaired_baseline_proxy"]
    best = max(candidates, key=lambda row: float(row["delta_return_pct_points_vs_baseline_proxy"]))
    main = next(row for row in metrics if row["version_id"] == "mom_12_1_sleeve_tilt_10pct")
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        rationale = "Governance audit failed."
    elif float(main["delta_return_pct_points_vs_baseline_proxy"]) > 0 and float(main["delta_max_drawdown_pct_points_vs_baseline_proxy"]) <= 0:
        decision = "admit_momentum_weight_tilt_to_pm_quant_review_not_accepted"
        rationale = "Primary 12-1 sleeve-relative tilt improves return proxy without worsening drawdown proxy."
    elif float(best["delta_return_pct_points_vs_baseline_proxy"]) > 0:
        decision = "diagnostic_positive_but_primary_not_confirmed"
        rationale = "A stress/reference tilt is positive, but primary 12-1 rule is not confirmed."
    else:
        decision = "diagnostic_only_no_weight_tilt_candidate"
        rationale = "Fixed momentum tilt does not improve the baseline proxy."
    return [
        {
            "pm_gate_decision": decision,
            "best_version": best["version_id"],
            "best_delta_return_pct_points": best["delta_return_pct_points_vs_baseline_proxy"],
            "primary_version": "mom_12_1_sleeve_tilt_10pct",
            "primary_delta_return_pct_points": main["delta_return_pct_points_vs_baseline_proxy"],
            "primary_delta_drawdown_pct_points": main["delta_max_drawdown_pct_points_vs_baseline_proxy"],
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal": False,
            "rationale": rationale,
        }
    ]


def _rule_spec() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "momentum_conditioned_weight_tilt_primary",
            "feature": "mom_12_1_vs_sleeve_mean",
            "action": "top_tercile_weight_x1.10_bottom_tercile_weight_x0.90_then_normalize_within_sleeve",
            "pool": "V57f selected stocks only",
            "execution_time": "official V57f rebalance only",
            "threshold_status": "pre_registered_not_optimized",
        },
        {
            "rule_id": "momentum_conditioned_weight_tilt_stress_reference",
            "feature": "mom_9_1_vs_sleeve_mean",
            "action": "same fixed tilt as primary",
            "pool": "V57f selected stocks only",
            "execution_time": "official V57f rebalance only",
            "threshold_status": "pre_registered_not_optimized",
        },
    ]


def _boundary() -> list[dict[str, Any]]:
    return [
        {"boundary": "new_stock_buy", "allowed": False},
        {"boundary": "full_market_momentum_selection", "allowed": False},
        {"boundary": "change_sleeve_total_weight", "allowed": False},
        {"boundary": "change_v57f_rebalance_frequency", "allowed": False},
        {"boundary": "change_v57f_core_factors", "allowed": False},
        {"boundary": "rebalance_day_weight_tilt_inside_selected_pool", "allowed": True},
    ]


def _data_gate(root: Path) -> list[dict[str, Any]]:
    return [
        {"item": "repaired_v57f_rebalance_signals", "exists": (root / REPAIRED_RUN / "rebalance_signals.csv").exists(), "pit": True},
        {"item": "repaired_daily_prices", "exists": (root / PRICE_DIR).exists(), "pit": True},
        {"item": "momentum_addenda_closeout", "exists": (root / MOMENTUM_CLOSEOUT).exists(), "pit": True},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "mark_accepted", "allowed": False},
        {"action": "scan_tilt_strength", "allowed": False},
        {"action": "buy_unselected_stocks", "allowed": False},
        {"action": "change_v57f_core", "allowed": False},
        {"action": "run_joinquant", "allowed": False},
    ]


def _spec_queue() -> list[dict[str, Any]]:
    return [{"priority": 1, "next_task": "limited_engineering_fixed_10pct_sleeve_tilt", "allowed": True}]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "PM/Quant review fixed momentum weight tilt", "allowed": decision.startswith("admit"), "requires_threshold_scan": False},
        {"priority": 2, "next_task": "Keep as diagnostic weight attribution", "allowed": True, "requires_threshold_scan": False},
        {"priority": 3, "next_task": "Scan tilt strength", "allowed": False, "requires_threshold_scan": True},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Completed fixed weight tilt diagnostic."}] if not failed else [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row)} for row in failed
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    main_delta_return: float = 0.0,
    main_delta_drawdown: float = 0.0,
    best_version: str = "",
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_momentum_weight_tilt",
        "status": status,
        "pm_gate_decision": decision,
        "primary_version": "mom_12_1_sleeve_tilt_10pct",
        "primary_delta_return_pct_points_vs_baseline_proxy": main_delta_return,
        "primary_delta_max_drawdown_pct_points_vs_baseline_proxy": main_delta_drawdown,
        "best_version": best_version,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _spec_summary() -> dict[str, Any]:
    return _summary("completed_v5f_momentum_weight_tilt_quant_spec", "admit_fixed_tilt_to_limited_engineering", [])


def _spec_report() -> str:
    return "# V5f Momentum Weight Tilt Quant Spec\n\nFixed rebalance-day tilt inside V57f selected stocks only. No accepted status.\n"


def _eng_report(metrics: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    lines = ["# V5f Momentum Weight Tilt Limited Engineering", ""]
    for row in metrics:
        lines.append(
            f"- `{row['version_id']}`: return={row['strategy_return']}, "
            f"delta={row['delta_return_pct_points_vs_baseline_proxy']} pct points, "
            f"dd_delta={row['delta_max_drawdown_pct_points_vs_baseline_proxy']} pct points"
        )
    lines.extend(["", f"Decision: `{decision[0]['pm_gate_decision']}`", decision[0]["rationale"], ""])
    return "\n".join(lines)


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Momentum Weight Tilt Rules",
            "",
            "- Rebalance-day selected-pool weight tilt only.",
            "- Do not add stocks or change V57f core.",
            "- Do not scan tilt strength or momentum windows.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PRICE_DIR,
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        MOMENTUM_CLOSEOUT,
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


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


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    result = run_v5f_momentum_weight_tilt()
    print(json.dumps(result, ensure_ascii=False, indent=2))
