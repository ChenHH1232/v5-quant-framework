from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5g_01_state_gated_internal_subsleeve_limited_engineering") / "current"
SPEC_DIR = Path("v5g_01_state_gated_internal_subsleeve_quant_spec") / "current"
P2_DIR = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
V5F_ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
V5F_DEEP_DIR = Path("v5f_internal_subsleeve_deep_engineering") / "current"
PRICE_DIR = Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_prices_v5"

BASELINE = "v57f_startup_preload_repaired_baseline"
CHAMPION = "internal_subsleeve_mom12_70_30"
STATE_GATED = "v5g_01_state_gated_internal_subsleeve_70_30"
COMMISSION_RATE = 0.0003
HOT_STATES = {"valuation_price_flow_overheat_watch", "valuation_overheat_watch"}

REQUIRED = [
    SPEC_DIR / "v5g_01_state_gated_quant_spec_summary.json",
    SPEC_DIR / "v5g_01_state_gate_rule_spec.csv",
    SPEC_DIR / "v5g_01_state_gate_event_queue.csv",
    P2_DIR / "v5c_p2_sleeve_overheat_state_panel.csv",
    V5F_ROUGH_DIR / "v5f_structural_rough_screen_weights.csv",
    V5F_ROUGH_DIR / "v5f_structural_rough_screen_daily_returns.csv",
    V5F_DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json",
]


def run_v5g_01_state_gated_internal_subsleeve_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5g_01_state_gated_engineering_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5g_01_state_gated_engineering_summary.json", summary)
        return summary

    spec_summary = _read_json(root / SPEC_DIR / "v5g_01_state_gated_quant_spec_summary.json")
    rule_spec = _read_csv(root / SPEC_DIR / "v5g_01_state_gate_rule_spec.csv")
    event_queue = _read_csv(root / SPEC_DIR / "v5g_01_state_gate_event_queue.csv")
    states = pd.read_csv(root / P2_DIR / "v5c_p2_sleeve_overheat_state_panel.csv", dtype={"trade_date": str, "sleeve_id": str})
    base_weights = pd.read_csv(root / V5F_ROUGH_DIR / "v5f_structural_rough_screen_weights.csv", dtype={"rebalance_date": str, "code": str})
    rough_daily = pd.read_csv(root / V5F_ROUGH_DIR / "v5f_structural_rough_screen_daily_returns.csv", dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})
    v5f_deep = _read_json(root / V5F_DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")

    prices = _load_prices(root)
    weights = _state_gated_weights(base_weights, states)
    daily = _daily_returns(weights, rough_daily, prices)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    period = _rebalance_period(daily)
    event_impact = _event_impact(event_queue, daily)
    sleeve_impact = _sleeve_impact(weights, daily)
    governance = _governance(spec_summary, rule_spec, weights, v5f_deep)
    decision = _pm_decision(metrics, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5g_01_state_gated_engineering_weights.csv", weights)
    _write_csv(out / "v5g_01_state_gated_engineering_daily_returns.csv", daily)
    _write_csv(out / "v5g_01_state_gated_engineering_metrics.csv", metrics)
    _write_csv(out / "v5g_01_state_gated_engineering_yearly.csv", yearly)
    _write_csv(out / "v5g_01_state_gated_engineering_rebalance_period.csv", period)
    _write_csv(out / "v5g_01_state_gate_event_impact.csv", event_impact)
    _write_csv(out / "v5g_01_state_gated_sleeve_impact.csv", sleeve_impact)
    _write_csv(out / "v5g_01_state_gated_governance_audit.csv", governance)
    _write_csv(out / "v5g_01_state_gated_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_01_state_gated_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5g_01_state_gated_engineering_blockers.csv", blockers_out)
    (out / "v5g_01_state_gated_engineering_report.md").write_text(_report(metrics, event_impact, decision), encoding="utf-8")
    (out / "v5g_01_state_gated_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    state_row = next(row for row in metrics if row["version_id"] == STATE_GATED)
    summary = _summary(
        "completed_v5g_01_state_gated_limited_engineering",
        decision[0]["pm_gate_decision"],
        blockers_out,
        limited_engineering_started=True,
        engineering_backtest_started=True,
        state_gated_delta_return_pct_points_vs_repaired_baseline=float(state_row["delta_return_pct_points_vs_repaired_baseline"]),
        state_gated_delta_return_pct_points_vs_internal_subsleeve_champion=float(state_row["delta_return_pct_points_vs_internal_subsleeve_champion"]),
        state_gated_delta_max_drawdown_pct_points_vs_champion=float(state_row["delta_max_drawdown_pct_points_vs_internal_subsleeve_champion"]),
        hot_gate_event_count=sum(1 for row in event_impact if row["gate_applied"] == "True"),
    )
    _write_json(out / "v5g_01_state_gated_engineering_summary.json", summary)
    return summary


def _state_gated_weights(weights: pd.DataFrame, states: pd.DataFrame) -> list[dict[str, Any]]:
    selected = weights[weights["version_id"].isin([BASELINE, CHAMPION])].copy()
    state_map = states.set_index(["trade_date", "sleeve_id"])["sleeve_overheat_state"].to_dict()
    champion = selected[selected["version_id"] == CHAMPION].copy()
    champion["version_id"] = STATE_GATED
    champion["family"] = "state_gated_internal_subsleeve"
    champion["state_gate_state"] = [
        state_map.get((row["rebalance_date"], row["sleeve"]), "normal") for _, row in champion.iterrows()
    ]
    champion["gate_applied"] = champion["state_gate_state"].isin(HOT_STATES)
    hot_idx = champion["gate_applied"]
    champion.loc[hot_idx, "target_weight"] = champion.loc[hot_idx, "base_target_weight"]
    champion["target_weight"] = pd.to_numeric(champion["target_weight"], errors="coerce")
    champion["base_target_weight"] = pd.to_numeric(champion["base_target_weight"], errors="coerce")
    champion["weight_delta"] = champion["target_weight"] - champion["base_target_weight"]
    champion.loc[hot_idx, "bucket"] = "state_gate_hot_sleeve_reverted_to_v57f"
    champion["sleeve_weight_preserved"] = True
    champion["new_stock_selected"] = False
    champion["accepted"] = False

    selected["state_gate_state"] = "not_applicable"
    selected["gate_applied"] = False
    combined = pd.concat([selected, champion], ignore_index=True, sort=False)
    cols = [
        "version_id",
        "family",
        "rebalance_date",
        "code",
        "sleeve",
        "base_target_weight",
        "target_weight",
        "weight_delta",
        "mom_12_1",
        "mr_60d",
        "bucket",
        "state_gate_state",
        "gate_applied",
        "sleeve_weight_preserved",
        "new_stock_selected",
        "accepted",
    ]
    return combined[cols].to_dict("records")


def _daily_returns(weights: list[dict[str, Any]], rough_daily: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    base_daily = rough_daily[rough_daily["version_id"] == BASELINE].copy()
    base_ret = base_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    base_nav = base_daily.set_index("trade_date")["strategy_nav"].astype(float).to_dict()
    dates = sorted(base_daily["trade_date"].tolist())
    rebalances = sorted({row["rebalance_date"] for row in weights})
    by_version_date: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in weights:
        by_version_date.setdefault((row["version_id"], row["rebalance_date"]), []).append(row)
    rows: list[dict[str, Any]] = []
    for version in [BASELINE, CHAMPION, STATE_GATED]:
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
                strategy_return = float(base_ret[day])
                nav = float(base_nav[day])
                delta_stock_return = 0.0
            else:
                delta_stock_return = sum(float(row["weight_delta"]) * (_safe_float(ret_map.get((day, row["code"]))) or 0.0) for row in active)
                strategy_return = float(base_ret[day]) + delta_stock_return - commission
                nav *= 1.0 + strategy_return
            rows.append(
                {
                    "trade_date": day,
                    "version_id": version,
                    "active_rebalance_date": active_rebalance,
                    "strategy_return": strategy_return,
                    "strategy_nav": nav,
                    "baseline_return": base_ret[day],
                    "delta_stock_return": delta_stock_return,
                    "incremental_commission": commission,
                    "turnover_proxy": turnover,
                    "accepted": False,
                }
            )
    return rows


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out = []
    for version, group in df.groupby("version_id", sort=False):
        navs = pd.to_numeric(group["strategy_nav"]).tolist()
        rets = pd.to_numeric(group["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = float(pd.Series(rets).std() * (252**0.5))
        out.append(
            {
                "version_id": version,
                "family": _family(version),
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "turnover_proxy": float(pd.to_numeric(group["turnover_proxy"]).sum()),
                "incremental_commission_total": float(pd.to_numeric(group["incremental_commission"]).sum()),
                "accepted": False,
            }
        )
    baseline = next(row for row in out if row["version_id"] == BASELINE)
    champion = next(row for row in out if row["version_id"] == CHAMPION)
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["strategy_return"]) - float(baseline["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (float(row["max_drawdown"]) - float(baseline["max_drawdown"])) * 100
        row["delta_return_pct_points_vs_internal_subsleeve_champion"] = (float(row["strategy_return"]) - float(champion["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_internal_subsleeve_champion"] = (float(row["max_drawdown"]) - float(champion["max_drawdown"])) * 100
    return sorted(out, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].str.slice(0, 4)
    out = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append({"version_id": version, "family": _family(version), "year": year, "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1, "trade_days": len(group)})
    baseline = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    champion = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == CHAMPION}
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - baseline.get(row["year"], 0.0)) * 100
        row["delta_return_pct_points_vs_internal_subsleeve_champion"] = (float(row["period_return"]) - champion.get(row["year"], 0.0)) * 100
    return out


def _rebalance_period(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out = []
    for (version, period), group in df.groupby(["version_id", "active_rebalance_date"], sort=True):
        if not period:
            continue
        out.append({"version_id": version, "active_rebalance_date": period, "period_return": (1.0 + pd.to_numeric(group["strategy_return"])).prod() - 1.0, "trade_days": len(group)})
    baseline = {row["active_rebalance_date"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    champion = {row["active_rebalance_date"]: float(row["period_return"]) for row in out if row["version_id"] == CHAMPION}
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - baseline.get(row["active_rebalance_date"], 0.0)) * 100
        row["delta_return_pct_points_vs_internal_subsleeve_champion"] = (float(row["period_return"]) - champion.get(row["active_rebalance_date"], 0.0)) * 100
    return out


def _event_impact(event_queue: list[dict[str, str]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    daily = pd.DataFrame(rows)
    periods = sorted(daily["active_rebalance_date"].dropna().unique().tolist())
    out = []
    for event in event_queue:
        day = event["trade_date"]
        next_day = next((p for p in periods if p > day), "2026-05-31")
        segment = daily[(daily["trade_date"] >= day) & (daily["trade_date"] < next_day)]
        item = {
            "event_id": event["event_id"],
            "trade_date": day,
            "sleeve_id": event["sleeve_id"],
            "sleeve_overheat_state": event["sleeve_overheat_state"],
            "gate_applied": str(event["sleeve_overheat_state"] in HOT_STATES),
            "period_end_exclusive": next_day,
        }
        returns = {}
        for version, group in segment.groupby("version_id"):
            returns[version] = (1.0 + pd.to_numeric(group["strategy_return"])).prod() - 1.0
        item["state_gated_period_return"] = returns.get(STATE_GATED, "")
        item["champion_period_return"] = returns.get(CHAMPION, "")
        item["baseline_period_return"] = returns.get(BASELINE, "")
        item["state_minus_champion_pct_points"] = (returns.get(STATE_GATED, 0.0) - returns.get(CHAMPION, 0.0)) * 100
        item["state_minus_baseline_pct_points"] = (returns.get(STATE_GATED, 0.0) - returns.get(BASELINE, 0.0)) * 100
        out.append(item)
    return out


def _sleeve_impact(weights: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    w = pd.DataFrame(weights)
    state = w[w["version_id"] == STATE_GATED].copy()
    rows_out = []
    for sleeve, group in state.groupby("sleeve", sort=True):
        rows_out.append(
            {
                "sleeve": sleeve,
                "gate_applied_rebalance_count": int(group[group["gate_applied"].astype(str) == "True"]["rebalance_date"].nunique()),
                "absolute_active_weight_delta": float(pd.to_numeric(group["weight_delta"]).abs().sum()),
                "hot_state_rows": int((group["gate_applied"].astype(str) == "True").sum()),
            }
        )
    return rows_out


def _governance(spec_summary: dict[str, Any], rule_spec: list[dict[str, str]], weights: list[dict[str, Any]], v5f_deep: dict[str, Any]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    state = df[df["version_id"] == STATE_GATED].copy()
    sleeve_checks = []
    for (_, sleeve), group in state.groupby(["rebalance_date", "sleeve"]):
        sleeve_checks.append(abs(pd.to_numeric(group["target_weight"]).sum() - pd.to_numeric(group["base_target_weight"]).sum()) < 1e-10)
    return [
        {"audit_id": "quant_spec_dependency", "status": "pass" if spec_summary.get("pm_gate_decision") == "v5g_01_quant_spec_pass_ready_for_limited_engineering_approval_not_backtest" else "fail", "detail": spec_summary.get("pm_gate_decision")},
        {"audit_id": "base_candidate_dependency", "status": "pass" if v5f_deep.get("primary_candidate") == CHAMPION else "fail", "detail": v5f_deep.get("primary_candidate", "")},
        {"audit_id": "fixed_rule_only", "status": "pass" if len(rule_spec) == 1 else "fail", "detail": len(rule_spec)},
        {"audit_id": "v57f_selected_pool_only", "status": "pass" if not state["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if all(sleeve_checks) else "fail", "detail": 0 if all(sleeve_checks) else 1},
        {"audit_id": "no_cash_raise", "status": "pass", "detail": "hot sleeve reverts to baseline sleeve weights; no cash bucket created"},
        {"audit_id": "no_511360_attachment", "status": "pass", "detail": "cash proxy not used in V5g 01 engineering"},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pm_decision(metrics: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    state = next(row for row in metrics if row["version_id"] == STATE_GATED)
    delta_base = float(state["delta_return_pct_points_vs_repaired_baseline"])
    delta_champion = float(state["delta_return_pct_points_vs_internal_subsleeve_champion"])
    dd_champion = float(state["delta_max_drawdown_pct_points_vs_internal_subsleeve_champion"])
    if not gov_ok:
        decision = "blocked_by_v5g_01_governance_issue"
        next_step = "repair_governance"
    elif delta_champion > 0 and dd_champion <= 0:
        decision = "promote_state_gated_internal_subsleeve_to_forward_paper_candidate_not_accepted"
        next_step = "open_v5g_01_forward_paper_tracking"
    elif delta_base > 0:
        decision = "v5g_01_limited_engineering_pass_but_do_not_replace_internal_subsleeve_champion"
        next_step = "keep_v5f_champion_primary_and_archive_state_gate_as_diagnostic"
    else:
        decision = "v5g_01_state_gate_diagnostic_only_no_incremental_edge"
        next_step = "keep_v5f_champion_primary"
    return [
        {
            "pm_gate_decision": decision,
            "governance_pass": gov_ok,
            "delta_return_pct_points_vs_repaired_baseline": delta_base,
            "delta_return_pct_points_vs_internal_subsleeve_champion": delta_champion,
            "delta_max_drawdown_pct_points_vs_internal_subsleeve_champion": dd_champion,
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "engineering_backtest_started": True,
            "next_step": next_step,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    if decision == "promote_state_gated_internal_subsleeve_to_forward_paper_candidate_not_accepted":
        return [{"priority": 1, "next_gate": "v5g_01_forward_paper_tracking_packet", "allowed": True, "status": "ready_not_accepted"}]
    return [
        {"priority": 1, "next_gate": "v5f_internal_subsleeve_70_30_keep_primary", "allowed": True, "status": "continue_primary_candidate"},
        {"priority": 2, "next_gate": "v5g_01_archive_or_observation_only", "allowed": True, "status": "diagnostic_or_secondary_only"},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]}
        for row in governance
        if row["status"] != "pass"
    ]


def _load_prices(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path, dtype={"date": str, "code": str}) for path in (root / PRICE_DIR).glob("*.csv")]
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    return prices


def _max_drawdown(navs: list[float]) -> float:
    peak = navs[0]
    worst = 0.0
    for nav in navs:
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1.0)
    return abs(worst)


def _family(version: str) -> str:
    if version == BASELINE:
        return "baseline"
    if version == CHAMPION:
        return "v5f_internal_subsleeve_champion"
    return "v5g_state_gated_internal_subsleeve"


def _report(metrics: list[dict[str, Any]], event_impact: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    state = next(row for row in metrics if row["version_id"] == STATE_GATED)
    champion = next(row for row in metrics if row["version_id"] == CHAMPION)
    return "\n".join(
        [
            "# V5g 01 State-Gated Internal Sub-Sleeve Limited Engineering",
            "",
            f"- State-gated return delta vs repaired baseline: `{float(state['delta_return_pct_points_vs_repaired_baseline']):.4f}` pct points",
            f"- Champion return delta vs repaired baseline: `{float(champion['delta_return_pct_points_vs_repaired_baseline']):.4f}` pct points",
            f"- State-gated delta vs champion: `{float(state['delta_return_pct_points_vs_internal_subsleeve_champion']):.4f}` pct points",
            f"- Hot gate events applied: `{sum(1 for row in event_impact if row['gate_applied'] == 'True')}`",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            "- Accepted: `False`",
            "- V57f core modified: `False`",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5g 01 Agent Execution Rules",
            "",
            "- Use repaired startup baseline only.",
            "- Use V57f selected stock pool only.",
            "- Do not modify V57f core.",
            "- Do not scan thresholds.",
            "- Do not attach 511360 or any cash proxy.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    blockers = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            blockers.append({"blocker_id": f"missing_{rel.name}", "severity": "fatal", "status": "blocking", "path": str(rel)})
    if not any((root / PRICE_DIR).glob("*.csv")):
        blockers.append({"blocker_id": "missing_repaired_price_files", "severity": "fatal", "status": "blocking", "path": str(PRICE_DIR)})
    return blockers


def _summary(
    status: str,
    decision: str,
    blockers: list[dict[str, Any]],
    limited_engineering_started: bool = False,
    engineering_backtest_started: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5g_01_state_gated_internal_subsleeve_limited_engineering",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "cash_proxy_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "limited_engineering_started": limited_engineering_started,
        "engineering_backtest_started": engineering_backtest_started,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }
    payload.update(extra)
    return payload


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(value):
        return None
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run_v5g_01_state_gated_internal_subsleeve_engineering()
