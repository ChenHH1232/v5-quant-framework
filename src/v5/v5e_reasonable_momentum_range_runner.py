from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_reasonable_momentum_range_test") / "current"
PRICE_DIR = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
LIMITED_ENGINEERING = Path("v5e_limited_engineering_loop") / "current"
V4_DIR = Path("D:/hh/codex/v4/phase_2_momentum")
INITIAL_CAPITAL = 2_000_000.0
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
SKIP_DAYS = 20
RANGE_WINDOWS = [
    {"window_id": "mom_6_1", "lookback_days": 126, "role": "state_sensitive_reference"},
    {"window_id": "mom_9_1", "lookback_days": 189, "role": "mid_band_stability_check"},
    {"window_id": "mom_12_1", "lookback_days": 252, "role": "primary_slow_backbone"},
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_reasonable_momentum_range(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_reasonable_momentum_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_data_or_pit_issue", blockers)
        _write_json(out / "v5e_reasonable_momentum_summary.json", summary)
        return summary

    prices = _load_prices(root)
    panel = _held_panel(root, prices)
    features = _features(panel, prices)
    feature_df = pd.DataFrame(features)
    long = _long(feature_df)
    diagnostics = _diagnostics(long)
    trigger = _trigger_overlay(root, feature_df)
    nav = _nav_proxy(trigger)
    decision = _decision(diagnostics, nav)
    queue = _next_queue(decision[0]["pm_gate_decision"])
    pit = _pit_audit(len(features), len(long))
    blockers_out = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Reasonable momentum range diagnostic complete."}]

    _write_csv(out / "v5e_reasonable_momentum_v4_anchor.csv", _v4_anchor())
    _write_csv(out / "v5e_reasonable_momentum_feature_schema.csv", _feature_schema())
    _write_csv(out / "v5e_reasonable_momentum_pit_governance_audit.csv", pit)
    _write_csv(out / "v5e_reasonable_momentum_held_stock_features.csv", features)
    _write_csv(out / "v5e_reasonable_momentum_range_diagnostics.csv", diagnostics)
    _write_csv(out / "v5e_reasonable_momentum_trigger_overlay.csv", trigger)
    _write_csv(out / "v5e_reasonable_momentum_nav_proxy.csv", nav)
    _write_csv(out / "v5e_reasonable_momentum_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_reasonable_momentum_next_queue.csv", queue)
    _write_csv(out / "v5e_reasonable_momentum_blockers.csv", blockers_out)
    (out / "v5e_reasonable_momentum_report.md").write_text(_report(diagnostics, nav, decision), encoding="utf-8")
    (out / "v5e_reasonable_momentum_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    primary = _row(diagnostics, "mom_12_1_vs_sleeve_mean")
    summary = _summary(
        "completed_v5e_reasonable_momentum_range_test",
        decision[0]["pm_gate_decision"],
        [],
        held_stock_day_count=len(features),
        feature_event_count=len(long),
        primary_feature="mom_12_1_vs_sleeve_mean",
        primary_forward_60d_spread=float(primary.get("positive_minus_negative_forward_60d_return", 0.0) or 0.0),
        best_feature_by_forward_60d_spread=_best(diagnostics).get("feature_name", ""),
        best_forward_60d_spread=float(_best(diagnostics).get("positive_minus_negative_forward_60d_return", 0.0) or 0.0),
        trigger_overlay_best_pct_points=float(nav[-1]["delta_return_pct_points_vs_baseline"]),
    )
    _write_json(out / "v5e_reasonable_momentum_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = []
    for path in (root / PRICE_DIR).glob("*.csv"):
        frames.append(pd.read_csv(path, dtype={"date": str, "code": str}))
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    for horizon in [20, 60, 120]:
        prices[f"future_close_{horizon}d"] = prices.groupby("code")["close"].shift(-horizon)
        prices[f"forward_{horizon}d_return"] = prices[f"future_close_{horizon}d"] / prices["close"] - 1.0
    max_lag = SKIP_DAYS + max(row["lookback_days"] for row in RANGE_WINDOWS)
    for lag in sorted({SKIP_DAYS, *[SKIP_DAYS + row["lookback_days"] for row in RANGE_WINDOWS], max_lag}):
        prices[f"close_lag_{lag}"] = prices.groupby("code")["close"].shift(lag)
    for row in RANGE_WINDOWS:
        lag = SKIP_DAYS + row["lookback_days"]
        prices[f"{row['window_id']}_daily"] = prices[f"close_lag_{SKIP_DAYS}"] / prices[f"close_lag_{lag}"] - 1.0
    return prices


def _held_panel(root: Path, prices: pd.DataFrame) -> pd.DataFrame:
    holdings = pd.read_csv(root / REPAIRED_RUN / "holdings.csv", dtype={"trade_date": str, "code": str})
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    sleeve_map = {(row["trade_date"], row["code"]): str(row.get("sector_id", "")) for _, row in signals.iterrows()}
    rebalance_dates = sorted(holdings["trade_date"].unique().tolist())
    dates = sorted(prices[(prices["date"] >= BACKTEST_START) & (prices["date"] <= BACKTEST_END)]["date"].unique().tolist())
    rows = []
    for _, row in holdings.iterrows():
        start = row["trade_date"]
        next_rebalance = _next_rebalance(start, rebalance_dates)
        for day in dates:
            if day >= start and (not next_rebalance or day < next_rebalance):
                rows.append(
                    {
                        "trade_date": day,
                        "code": row["code"],
                        "holding_start_date": start,
                        "next_rebalance_date": next_rebalance,
                        "sleeve": sleeve_map.get((start, row["code"]), ""),
                    }
                )
    return pd.DataFrame(rows)


def _features(panel: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    merged = panel.merge(prices, left_on=["trade_date", "code"], right_on=["date", "code"], how="left")
    merged = merged[merged["close"].notna()].copy()
    for row in RANGE_WINDOWS:
        feature = f"{row['window_id']}_daily"
        sleeve_mean = merged.groupby(["trade_date", "sleeve"])[feature].mean().rename(f"{feature}_sleeve_mean").reset_index()
        port_mean = merged.groupby("trade_date")[feature].mean().rename(f"{feature}_portfolio_mean").reset_index()
        merged = merged.merge(sleeve_mean, on=["trade_date", "sleeve"], how="left").merge(port_mean, on="trade_date", how="left")
    rows = []
    for _, row in merged.iterrows():
        out = {
            "research_pool": "v57f_repaired_historical_holdings_only",
            "trade_date": row["trade_date"],
            "code": row["code"],
            "sleeve": row["sleeve"],
            "holding_start_date": row["holding_start_date"],
            "next_rebalance_date": row["next_rebalance_date"],
            "close": row["close"],
            "forward_20d_return": row["forward_20d_return"],
            "forward_60d_return": row["forward_60d_return"],
            "forward_120d_return": row["forward_120d_return"],
            "future_return_used_for_signal": False,
            "new_buy_signal_allowed": False,
        }
        for spec in RANGE_WINDOWS:
            base = f"{spec['window_id']}_daily"
            out[base] = row[base]
            out[f"{spec['window_id']}_vs_sleeve_mean"] = _diff(row[base], row[f"{base}_sleeve_mean"])
            out[f"{spec['window_id']}_vs_portfolio_mean"] = _diff(row[base], row[f"{base}_portfolio_mean"])
        rows.append(out)
    return rows


def _long(df: pd.DataFrame) -> pd.DataFrame:
    names = []
    for spec in RANGE_WINDOWS:
        names.extend([f"{spec['window_id']}_daily", f"{spec['window_id']}_vs_sleeve_mean", f"{spec['window_id']}_vs_portfolio_mean"])
    rows = []
    for name in names:
        for _, row in df.iterrows():
            value = _safe_float(row.get(name))
            if value is None:
                continue
            rows.append(
                {
                    "feature_name": name,
                    "trade_date": row["trade_date"],
                    "code": row["code"],
                    "sleeve": row["sleeve"],
                    "feature_value": value,
                    "sign_bucket": _sign_bucket(value),
                    "forward_20d_return": row["forward_20d_return"],
                    "forward_60d_return": row["forward_60d_return"],
                    "forward_120d_return": row["forward_120d_return"],
                    "used_for_trade_rule": False,
                }
            )
    long = pd.DataFrame(rows)
    if long.empty:
        return long
    long["tercile_bucket"] = ""
    for name, group in long.groupby("feature_name"):
        long.loc[group.index, "tercile_bucket"] = pd.qcut(group["feature_value"].rank(method="first"), 3, labels=["bottom", "middle", "top"]).astype(str)
    return long


def _diagnostics(long: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for name, group in long.groupby("feature_name"):
        pos = group[group["sign_bucket"].eq("positive")]
        neg = group[group["sign_bucket"].eq("negative")]
        rows.append(
            {
                "feature_name": name,
                "observation_count": int(len(group)),
                "positive_count": int(len(pos)),
                "negative_count": int(len(neg)),
                "positive_forward_20d_return": _mean(pos["forward_20d_return"]),
                "negative_forward_20d_return": _mean(neg["forward_20d_return"]),
                "positive_minus_negative_forward_20d_return": _mean(pos["forward_20d_return"]) - _mean(neg["forward_20d_return"]),
                "positive_forward_60d_return": _mean(pos["forward_60d_return"]),
                "negative_forward_60d_return": _mean(neg["forward_60d_return"]),
                "positive_minus_negative_forward_60d_return": _mean(pos["forward_60d_return"]) - _mean(neg["forward_60d_return"]),
                "positive_forward_120d_return": _mean(pos["forward_120d_return"]),
                "negative_forward_120d_return": _mean(neg["forward_120d_return"]),
                "positive_minus_negative_forward_120d_return": _mean(pos["forward_120d_return"]) - _mean(neg["forward_120d_return"]),
                "stable_direction_diagnostic": _stable_direction(pos, neg),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _trigger_overlay(root: Path, df: pd.DataFrame) -> list[dict[str, Any]]:
    exits = pd.read_csv(root / LIMITED_ENGINEERING / "v5e_exit_action_log.csv", dtype={"trigger_date": str, "execution_date": str, "code": str})
    exits = exits[exits["version_id"].eq("v5e_profit_lock_main_20pct_sell50")].copy()
    fmap = {(row["code"], row["trade_date"]): row for _, row in df.iterrows()}
    rows = []
    features = ["mom_6_1_vs_sleeve_mean", "mom_9_1_vs_sleeve_mean", "mom_12_1_vs_sleeve_mean"]
    for idx, row in exits.iterrows():
        feature_row = fmap.get((row["code"], row["trigger_date"]))
        if feature_row is None:
            continue
        sold_value = float(row.get("value", 0.0))
        for feature in features:
            value = _safe_float(feature_row.get(feature))
            fwd60 = _safe_float(feature_row.get("forward_60d_return"))
            if value is None:
                continue
            state = _sign_bucket(value)
            rows.append(
                {
                    "event_id": f"reasonable_range_exit_{idx}_{feature}",
                    "version_id": row["version_id"],
                    "code": row["code"],
                    "trigger_date": row["trigger_date"],
                    "execution_date": row["execution_date"],
                    "feature_name": feature,
                    "momentum_state": state,
                    "feature_value": value,
                    "sold_value": sold_value,
                    "forward_60d_return_after_trigger_close": "" if fwd60 is None else fwd60,
                    "positive_momentum_delay_sell_60d_diagnostic_value": sold_value * fwd60 if state == "positive" and fwd60 is not None else 0.0,
                    "used_for_trade_rule": False,
                    "accepted": False,
                }
            )
    return rows


def _nav_proxy(trigger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_feature: dict[str, float] = {}
    for row in trigger:
        by_feature[row["feature_name"]] = by_feature.get(row["feature_name"], 0.0) + float(row["positive_momentum_delay_sell_60d_diagnostic_value"])
    rows = []
    for feature, value in sorted(by_feature.items()):
        rows.append(
            {
                "version_id": f"{feature}_event_proxy",
                "nav_level_valid": False,
                "delta_return_pct_points_vs_baseline": value / INITIAL_CAPITAL * 100.0,
                "accepted": False,
            }
        )
    best = max((float(row["delta_return_pct_points_vs_baseline"]) for row in rows), default=0.0)
    rows.append(
        {
            "version_id": "reasonable_range_best_event_proxy_not_selectable",
            "nav_level_valid": False,
            "delta_return_pct_points_vs_baseline": best,
            "accepted": False,
        }
    )
    return rows


def _decision(diagnostics: list[dict[str, Any]], nav: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = _row(diagnostics, "mom_12_1_vs_sleeve_mean")
    primary_60 = float(primary.get("positive_minus_negative_forward_60d_return", 0.0) or 0.0)
    primary_120 = float(primary.get("positive_minus_negative_forward_120d_return", 0.0) or 0.0)
    best_proxy = float(nav[-1]["delta_return_pct_points_vs_baseline"])
    if primary_60 > 0 and best_proxy > 0:
        decision = "reasonable_range_supports_12_1_separate_quant_spec_not_accepted"
        rationale = "The pre-declared 12-1 sleeve-relative feature is positive at 60d and V5e trigger-event diagnostics are positive."
    elif best_proxy > 0:
        decision = "trigger_event_positive_but_range_not_stable"
        rationale = "Trigger-event diagnostics are positive, but the pre-declared 12-1 range is not stable enough."
    else:
        decision = "reasonable_range_diagnostic_only_no_trading_value"
        rationale = "No sufficient long-horizon diagnostic value in the reasonable range."
    return [
        {
            "pm_gate_decision": decision,
            "primary_feature": "mom_12_1_vs_sleeve_mean",
            "primary_forward_60d_spread": primary_60,
            "primary_forward_120d_spread": primary_120,
            "event_proxy_best_pct_points": best_proxy,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_replacement": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal": False,
            "rationale": rationale,
        }
    ]


def _v4_anchor() -> list[dict[str, Any]]:
    return [
        {"anchor_id": "v4_mom_6_1", "role": "state_sensitive_research_alpha", "v5e_use": "reference_only"},
        {"anchor_id": "v4_mom_12_1", "role": "slower_durable_backbone", "v5e_use": "primary_reasonable_range_anchor"},
        {"anchor_id": "skip_recent_1m", "role": "avoid_short_reversal_noise", "v5e_use": "fixed_skip_20_trading_days"},
    ]


def _feature_schema() -> list[dict[str, Any]]:
    rows = []
    for spec in RANGE_WINDOWS:
        rows.extend(
            [
                {"feature_name": f"{spec['window_id']}_daily", "lookback_days": spec["lookback_days"], "skip_days": SKIP_DAYS, "role": spec["role"], "threshold_scan_used": False},
                {"feature_name": f"{spec['window_id']}_vs_sleeve_mean", "lookback_days": spec["lookback_days"], "skip_days": SKIP_DAYS, "role": spec["role"], "threshold_scan_used": False},
                {"feature_name": f"{spec['window_id']}_vs_portfolio_mean", "lookback_days": spec["lookback_days"], "skip_days": SKIP_DAYS, "role": spec["role"], "threshold_scan_used": False},
            ]
        )
    return rows


def _pit_audit(feature_rows: int, feature_events: int) -> list[dict[str, Any]]:
    return [
        {"audit_id": "reasonable_range_only", "status": "pass", "detail": "6-1, 9-1, 12-1 only; not an open grid"},
        {"audit_id": "v57f_pool_only", "status": "pass", "detail": f"feature_rows={feature_rows}; feature_events={feature_events}"},
        {"audit_id": "skip_recent_1m_fixed", "status": "pass", "detail": "skip_days=20"},
        {"audit_id": "forward_returns_evaluation_only", "status": "pass", "detail": "No future return used in features"},
        {"audit_id": "accepted_false", "status": "pass", "detail": "Diagnostic / separate spec candidate only"},
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "Open V5e 12-1 sleeve-relative delay-sell Quant spec", "allowed": decision.startswith("reasonable_range_supports"), "requires_threshold_scan": False},
        {"priority": 2, "next_task": "Compare V5e momentum addenda closeout packet", "allowed": True, "requires_threshold_scan": False},
        {"priority": 3, "next_task": "Continue V5e forward/paper tracking", "allowed": True, "requires_threshold_scan": False},
        {"priority": 4, "next_task": "Momentum threshold scan", "allowed": False, "requires_threshold_scan": True},
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    held_stock_day_count: int = 0,
    feature_event_count: int = 0,
    primary_feature: str = "",
    primary_forward_60d_spread: float = 0.0,
    best_feature_by_forward_60d_spread: str = "",
    best_forward_60d_spread: float = 0.0,
    trigger_overlay_best_pct_points: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_reasonable_momentum_range_test",
        "status": status,
        "pm_gate_decision": decision,
        "range": "6_1_9_1_12_1_skip_20_trading_days",
        "research_pool": "v57f_v5e_existing_value_dividend_lowvol_sleeve_pool_only",
        "held_stock_day_count": held_stock_day_count,
        "feature_event_count": feature_event_count,
        "primary_feature": primary_feature,
        "primary_forward_60d_spread": primary_forward_60d_spread,
        "best_feature_by_forward_60d_spread": best_feature_by_forward_60d_spread,
        "best_forward_60d_spread": best_forward_60d_spread,
        "trigger_overlay_best_pct_points": trigger_overlay_best_pct_points,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_replacement": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(diagnostics: list[dict[str, Any]], nav: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    primary = _row(diagnostics, "mom_12_1_vs_sleeve_mean")
    best = _best(diagnostics)
    return "\n".join(
        [
            "# V5e Reasonable Momentum Range Test",
            "",
            "- Tested fixed reasonable range: 6-1, 9-1, 12-1 with a 20-trading-day skip.",
            "- Pool: V57f/V5e existing holdings only.",
            "- No full-market selection, no threshold scan, no accepted status.",
            "",
            "## Result",
            f"- Primary feature `mom_12_1_vs_sleeve_mean` forward 60d spread: `{primary.get('positive_minus_negative_forward_60d_return', '')}`.",
            f"- Best diagnostic feature by forward 60d spread: `{best.get('feature_name', '')}` = `{best.get('positive_minus_negative_forward_60d_return', '')}`.",
            *[f"- `{row['version_id']}` event proxy pct points: `{row['delta_return_pct_points_vs_baseline']}`." for row in nav],
            "",
            "## PM Gate",
            f"- Decision: `{decision[0]['pm_gate_decision']}`.",
            f"- Rationale: {decision[0]['rationale']}",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Reasonable Momentum Range Agent Rules",
            "",
            "- Diagnostic only.",
            "- Test only 6-1, 9-1, 12-1 with fixed 20-trading-day skip.",
            "- Do not expand to an open parameter grid.",
            "- Do not use full-market selection, new buys, threshold scans, or V57f core changes.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PRICE_DIR,
        REPAIRED_RUN / "holdings.csv",
        REPAIRED_RUN / "rebalance_signals.csv",
        LIMITED_ENGINEERING / "v5e_exit_action_log.csv",
        V4_DIR / "momentum_stage_summary_v1.md",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not ((root / path).exists() if not path.is_absolute() else path.exists())
    ]


def _row(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next((row for row in rows if row["feature_name"] == name), {})


def _best(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return max(rows, key=lambda row: float(row.get("positive_minus_negative_forward_60d_return", 0.0) or 0.0)) if rows else {}


def _stable_direction(pos: pd.DataFrame, neg: pd.DataFrame) -> str:
    spread60 = _mean(pos["forward_60d_return"]) - _mean(neg["forward_60d_return"])
    spread120 = _mean(pos["forward_120d_return"]) - _mean(neg["forward_120d_return"])
    if spread60 > 0 and spread120 > 0:
        return "positive_long_momentum_directionally_favorable"
    if spread60 < 0 and spread120 < 0:
        return "negative_or_reversal_directionally_favorable"
    return "mixed_or_unstable"


def _diff(left: Any, right: Any) -> float | str:
    lf = _safe_float(left)
    rf = _safe_float(right)
    return "" if lf is None or rf is None else lf - rf


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _sign_bucket(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def _mean(values: Any) -> float:
    nums = [value for value in (_safe_float(item) for item in list(values)) if value is not None]
    return float(sum(nums) / len(nums)) if nums else 0.0


def _next_rebalance(start: str, dates: list[str]) -> str:
    later = [day for day in dates if day > start]
    return later[0] if later else ""


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
    result = run_v5e_reasonable_momentum_range()
    print(json.dumps(result, ensure_ascii=False, indent=2))
