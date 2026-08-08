from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_trigger_day_5min_execution_proxy_test") / "current"
DATA_GATE_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "current"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
INITIAL_CAPITAL = 2_000_000.0
MAIN_CANDIDATE = "v5e_combined_main_profit_lock_plus_trailing"
SECONDARY_CANDIDATE = "v5e_profit_lock_main_20pct_sell50"
TARGET_VERSIONS = [MAIN_CANDIDATE, SECONDARY_CANDIDATE]
PROXIES = ["bar_0935", "bar_0940", "bar_1000", "bar_1455", "day_5min_vwap", "day_5min_twap"]
BAR_TIMES = {
    "bar_0935": "09:35:00",
    "bar_0940": "09:40:00",
    "bar_1000": "10:00:00",
    "bar_1455": "14:55:00",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_trigger_day_5min_execution_proxy(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_5min_execution_proxy_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_5min_execution_proxy_summary.json", summary)
        return summary

    data_gate = _read_json(root / DATA_GATE_DIR / "v5e_trigger_day_5min_data_gate_summary.json")
    if data_gate.get("pm_decision") != "coverage_pass_ready_for_execution_proxy_test":
        blockers = [
            {
                "blocker_id": "v5e_5min_data_gate_not_passed",
                "severity": "fatal",
                "status": "blocking",
                "description": "Trigger-day 5min execution windows are not fully covered.",
            }
        ]
        _write_csv(out / "v5e_5min_execution_proxy_blockers.csv", blockers)
        summary = _summary("blocked_data_gate_not_passed", "blocked_until_5min_data_gate_pass", blockers)
        _write_json(out / "v5e_5min_execution_proxy_summary.json", summary)
        return summary

    exits = _read_df(root / LOOP_DIR / "v5e_exit_action_log.csv")
    requirements = _read_df(root / DATA_GATE_DIR / "v5e_exit_execution_window_requirement.csv")
    coverage = _read_df(root / DATA_GATE_DIR / "v5e_exit_5min_coverage_audit.csv")
    comparison = _read_df(root / LOOP_DIR / "v5e_engineering_comparison.csv")
    action_rows = _action_proxy_rows(exits, requirements, coverage)
    proxy_summary = _proxy_summary_rows(action_rows)
    candidate_rows = _candidate_rows(proxy_summary, comparison)
    gate_rows = _gate_decision(candidate_rows)
    blockers = _nonfatal_blockers(candidate_rows)

    _write_csv(out / "v5e_5min_execution_proxy_action_prices.csv", action_rows)
    _write_csv(out / "v5e_5min_execution_proxy_comparison.csv", proxy_summary)
    _write_csv(out / "v5e_5min_execution_proxy_candidate_impact.csv", candidate_rows)
    _write_csv(out / "v5e_5min_execution_proxy_gate_decision.csv", gate_rows)
    _write_csv(out / "v5e_5min_execution_proxy_blockers.csv", blockers)
    _write_csv(out / "v5e_5min_execution_proxy_next_queue.csv", _next_queue(gate_rows[0]["pm_decision"]))
    (out / "v5e_5min_execution_proxy_report.md").write_text(_report(gate_rows, candidate_rows), encoding="utf-8")
    (out / "v5e_5min_execution_proxy_agent_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_5min_execution_proxy_test",
        gate_rows[0]["pm_decision"],
        [],
        action_count=len(exits[exits["version_id"].isin(TARGET_VERSIONS)]),
        proxy_count=len(PROXIES),
        candidate_rows=candidate_rows,
    )
    _write_json(out / "v5e_5min_execution_proxy_summary.json", summary)
    return summary


def _action_proxy_rows(exits: pd.DataFrame, requirements: pd.DataFrame, coverage: pd.DataFrame) -> list[dict[str, Any]]:
    exits = exits[exits["version_id"].isin(TARGET_VERSIONS)].reset_index(drop=True).copy()
    req = requirements[requirements["version_id"].isin(TARGET_VERSIONS)].reset_index(drop=True).copy()
    if len(exits) != len(req):
        raise ValueError("V5e exit action log and execution requirements are misaligned.")
    exec_cov = coverage[coverage["window_label"].eq("execution_date")].set_index("action_id")
    rows: list[dict[str, Any]] = []
    for idx, exit_row in exits.iterrows():
        req_row = req.iloc[idx]
        action_id = str(req_row["action_id"])
        cov = exec_cov.loc[action_id]
        minute = _minute_prices(Path(str(cov["path"])))
        amount = _float(exit_row["amount"])
        reference_price = _float(exit_row["price"])
        reference_value = amount * reference_price
        for proxy in PROXIES:
            proxy_price = _proxy_price(proxy, minute)
            value_delta = (proxy_price - reference_price) * amount
            bps_delta = (value_delta / reference_value * 10000.0) if reference_value else 0.0
            rows.append(
                {
                    "action_id": action_id,
                    "version_id": exit_row["version_id"],
                    "trigger_date": exit_row["trigger_date"],
                    "execution_date": exit_row["execution_date"],
                    "code": exit_row["code"],
                    "sleeve": req_row.get("sleeve", "unknown"),
                    "trigger_reason": exit_row["trigger_reason"],
                    "side": "sell",
                    "amount": amount,
                    "daily_open_reference_price": reference_price,
                    "proxy_id": proxy,
                    "proxy_price": proxy_price,
                    "execution_value_delta_vs_daily_open": value_delta,
                    "execution_bps_delta_vs_daily_open": bps_delta,
                    "sell_execution_quality": "better_than_daily_open" if value_delta > 0 else "worse_than_daily_open" if value_delta < 0 else "same_as_daily_open",
                    "minute_data_used_for_trigger": False,
                    "full_rebacktest": False,
                }
            )
    return rows


def _proxy_summary_rows(action_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(action_rows)
    rows: list[dict[str, Any]] = []
    for (version, proxy), group in df.groupby(["version_id", "proxy_id"]):
        rows.append(
            {
                "version_id": version,
                "proxy_id": proxy,
                "action_count": int(len(group)),
                "total_execution_value_delta_vs_daily_open": float(group["execution_value_delta_vs_daily_open"].sum()),
                "impact_pct_of_initial_capital": float(group["execution_value_delta_vs_daily_open"].sum() / INITIAL_CAPITAL),
                "avg_bps_delta_vs_daily_open": float(group["execution_bps_delta_vs_daily_open"].mean()),
                "median_bps_delta_vs_daily_open": float(group["execution_bps_delta_vs_daily_open"].median()),
                "better_than_daily_open_count": int((group["execution_value_delta_vs_daily_open"] > 0).sum()),
                "worse_than_daily_open_count": int((group["execution_value_delta_vs_daily_open"] < 0).sum()),
                "same_as_daily_open_count": int((group["execution_value_delta_vs_daily_open"] == 0).sum()),
                "minute_data_used_for_trigger": False,
                "full_rebacktest": False,
            }
        )
    return rows


def _candidate_rows(proxy_summary: list[dict[str, Any]], comparison: pd.DataFrame) -> list[dict[str, Any]]:
    comp = comparison.set_index("version_id")
    baseline_return = _float(comp.loc["v57f_repaired_baseline", "strategy_return"])
    rows: list[dict[str, Any]] = []
    for row in proxy_summary:
        daily_return = _float(comp.loc[row["version_id"], "strategy_return"])
        proxy_adjusted_return = daily_return + _float(row["impact_pct_of_initial_capital"])
        rows.append(
            {
                **row,
                "v57f_baseline_strategy_return": baseline_return,
                "daily_proxy_strategy_return": daily_return,
                "execution_proxy_adjusted_return_estimate": proxy_adjusted_return,
                "daily_proxy_delta_vs_v57f_baseline": daily_return - baseline_return,
                "delta_return_estimate_vs_daily_proxy": proxy_adjusted_return - daily_return,
                "execution_proxy_adjusted_delta_vs_v57f_baseline": proxy_adjusted_return - baseline_return,
                "daily_proxy_max_drawdown": _float(comp.loc[row["version_id"], "max_drawdown"]),
                "daily_proxy_delta_max_drawdown_vs_baseline": _float(comp.loc[row["version_id"], "delta_max_drawdown_vs_baseline"]),
                "daily_proxy_cash_drag_delta_vs_baseline": _float(comp.loc[row["version_id"], "cash_drag_delta_vs_baseline"]),
                "estimate_scope": "execution_price_delta_only_not_full_rebacktest",
                "threshold_status": "pre_registered_not_optimized",
                "accepted": False,
            }
        )
    return rows


def _gate_decision(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    main = [r for r in candidate_rows if r["version_id"] == MAIN_CANDIDATE and r["proxy_id"] == "day_5min_vwap"]
    secondary = [r for r in candidate_rows if r["version_id"] == SECONDARY_CANDIDATE and r["proxy_id"] == "day_5min_vwap"]
    main_delta = _float(main[0]["execution_proxy_adjusted_delta_vs_v57f_baseline"]) if main else 0.0
    secondary_delta = _float(secondary[0]["execution_proxy_adjusted_delta_vs_v57f_baseline"]) if secondary else 0.0
    if secondary and secondary_delta > 0 and secondary[0]["daily_proxy_delta_max_drawdown_vs_baseline"] < 0:
        return [
            {
                "pm_decision": "switch_primary_to_profit_lock_main_execution_robust_review_candidate",
                "primary_candidate": SECONDARY_CANDIDATE,
                "previous_primary_candidate": MAIN_CANDIDATE,
                "preferred_execution_proxy_for_review": "day_5min_vwap",
                "main_candidate_vwap_delta_vs_v57f_baseline": main_delta,
                "secondary_candidate_vwap_delta_vs_v57f_baseline": secondary_delta,
                "accepted": False,
                "reason": "Profit-lock main remains positive versus V57f baseline under VWAP execution impact, has fewer exits and lower cash drag; switch is for review-candidate priority, not historical-return acceptance.",
                "next_gate": "v5e_profit_lock_main_execution_robust_formal_review_not_acceptance",
            }
        ]
    return [
        {
            "pm_decision": "ready_for_v5e_execution_governance_review",
            "primary_candidate": MAIN_CANDIDATE,
            "preferred_execution_proxy_for_review": "day_5min_vwap",
            "main_candidate_vwap_delta_vs_v57f_baseline": main_delta,
            "secondary_candidate_vwap_delta_vs_v57f_baseline": secondary_delta,
            "accepted": False,
            "reason": "5min trigger-day execution coverage is complete; proxy test is execution-sensitive but does not change V5e daily trigger logic.",
            "next_gate": "v5e_execution_governance_review_not_model_acceptance",
        }
    ]


def _nonfatal_blockers(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "full_nav_rebacktest_not_run",
            "severity": "review_note",
            "status": "non_blocking",
            "description": "This packet estimates execution price impact only; full V5e NAV rebacktest with minute execution governance remains a later step.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "v5e_execution_governance_review",
            "decision": decision,
            "description": "Review whether V5e exits should use daily open, 09:35/09:40 bars, VWAP/TWAP, or V5d L2/L3/L4 execution governance for execution-only handling.",
            "allowed": True,
            "requires_new_threshold": False,
            "requires_v57f_change": False,
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    action_count: int = 0,
    proxy_count: int = 0,
    candidate_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    candidate_rows = candidate_rows or []
    main_vwap = [r for r in candidate_rows if r.get("version_id") == MAIN_CANDIDATE and r.get("proxy_id") == "day_5min_vwap"]
    secondary_vwap = [r for r in candidate_rows if r.get("version_id") == SECONDARY_CANDIDATE and r.get("proxy_id") == "day_5min_vwap"]
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_trigger_day_5min_execution_proxy_test",
        "status": status,
        "pm_decision": decision,
        "action_count": action_count,
        "proxy_count": proxy_count,
        "minute_data_used_for_trigger": False,
        "full_holding_period_checked": False,
        "full_rebacktest": False,
        "accepted": False,
        "v57f_core_modified": False,
        "erc_modified": False,
        "v5d_modified": False,
        "main_candidate_vwap_delta_return_estimate": main_vwap[0]["delta_return_estimate_vs_daily_proxy"] if main_vwap else 0.0,
        "secondary_candidate_vwap_delta_return_estimate": secondary_vwap[0]["delta_return_estimate_vs_daily_proxy"] if secondary_vwap else 0.0,
        "main_candidate_vwap_delta_vs_v57f_baseline": main_vwap[0]["execution_proxy_adjusted_delta_vs_v57f_baseline"] if main_vwap else 0.0,
        "secondary_candidate_vwap_delta_vs_v57f_baseline": secondary_vwap[0]["execution_proxy_adjusted_delta_vs_v57f_baseline"] if secondary_vwap else 0.0,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(gate_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> str:
    df = pd.DataFrame(candidate_rows)
    lines = [
        "# V5e Trigger-Day 5min Execution Proxy Test",
        "",
        "## Scope",
        "- Daily V5e triggers are unchanged.",
        "- 5min data is used only for T+1 sell execution price proxy comparison.",
        "- This is execution price impact attribution, not a full NAV rebacktest and not model acceptance.",
        "",
        "## Gate",
        f"- PM decision: `{gate_rows[0]['pm_decision']}`",
        f"- Next gate: `{gate_rows[0]['next_gate']}`",
        "",
        "## VWAP Impact",
    ]
    for version in TARGET_VERSIONS:
        row = df[(df["version_id"] == version) & (df["proxy_id"] == "day_5min_vwap")].iloc[0]
        lines.append(
            f"- {version}: execution delta vs daily proxy {row['delta_return_estimate_vs_daily_proxy']:.6f}, adjusted delta vs V57f baseline {row['execution_proxy_adjusted_delta_vs_v57f_baseline']:.6f}, avg bps {row['avg_bps_delta_vs_daily_open']:.2f}"
        )
    return "\n".join(lines) + "\n"


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e 5min Execution Proxy Agent Rules",
            "",
            "- Use 5min bars only for execution price attribution after daily close triggers.",
            "- Do not add thresholds or change V5e trigger logic.",
            "- Do not modify V57f, ERC, or V5d.",
            "- Do not mark accepted.",
            "- Treat outputs as execution governance evidence, not model selection by historical return.",
            "",
        ]
    )


def _minute_prices(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path)
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    by_time = {str(row["time"]): float(row["close"]) for _, row in df.iterrows() if pd.notna(row["close"])}
    closes = [float(x) for x in df["close"].dropna().tolist()]
    volume = float(df["volume"].sum())
    amount = float(df["amount"].sum())
    return {
        "by_time": by_time,
        "vwap": amount / volume if volume > 0 else closes[-1],
        "twap": sum(closes) / len(closes) if closes else 0.0,
    }


def _proxy_price(proxy: str, minute: dict[str, Any]) -> float:
    if proxy in BAR_TIMES:
        return float(minute["by_time"][BAR_TIMES[proxy]])
    if proxy == "day_5min_vwap":
        return float(minute["vwap"])
    if proxy == "day_5min_twap":
        return float(minute["twap"])
    raise ValueError(proxy)


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        DATA_GATE_DIR / "v5e_trigger_day_5min_data_gate_summary.json",
        DATA_GATE_DIR / "v5e_exit_execution_window_requirement.csv",
        DATA_GATE_DIR / "v5e_exit_5min_coverage_audit.csv",
        LOOP_DIR / "v5e_exit_action_log.csv",
        LOOP_DIR / "v5e_engineering_comparison.csv",
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e 5min data gate or engineering file is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


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
    result = run_v5e_trigger_day_5min_execution_proxy()
    print(json.dumps(result, ensure_ascii=False, indent=2))
