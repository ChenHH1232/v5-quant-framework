from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_momentum_weight_tilt_backtest_scope") / "current"
ENG_DIR = Path("v5f_momentum_weight_tilt_limited_engineering") / "current"
PM_DIR = Path("v5f_momentum_weight_tilt_pm_quant_review") / "current"
HISTORICAL_CLOSEOUT = Path("v5e_historical_closeout_governance_packet") / "current" / "v5e_historical_closeout_summary.json"

BACKTEST_SCOPE_START = "2021-05-01"
BACKTEST_SCOPE_END = "2026-05-31"
PRIMARY = "mom_12_1_sleeve_tilt_10pct"
STRESS = "mom_9_1_sleeve_tilt_10pct"
BASELINE = "v57f_repaired_baseline_proxy"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_momentum_weight_tilt_backtest_scope(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_momentum_weight_tilt_backtest_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_momentum_weight_tilt_backtest_summary.json", summary)
        return summary

    historical = _read_json(root / HISTORICAL_CLOSEOUT)
    pm_summary = _read_json(root / PM_DIR / "v5f_momentum_weight_tilt_pm_quant_summary.json")
    daily = pd.read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_daily_returns.csv", dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})
    weights = pd.read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_weights.csv", dtype={"rebalance_date": str, "version_id": str, "code": str})
    metrics = _read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_metrics.csv")
    governance = _read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_governance_audit.csv")

    daily = daily[(daily["trade_date"] >= BACKTEST_SCOPE_START) & (daily["trade_date"] <= BACKTEST_SCOPE_END)].copy()
    scope_audit = _scope_audit(daily, weights, historical, pm_summary, governance)
    yearly = _yearly_performance(daily)
    rebalance_period = _rebalance_period_performance(daily)
    drawdown = _drawdown_review(daily)
    contribution = _contribution_summary(daily)
    decision = _pm_decision(scope_audit, metrics)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(scope_audit)

    _write_csv(out / "v5f_momentum_weight_tilt_backtest_scope_audit.csv", scope_audit)
    _write_csv(out / "v5f_momentum_weight_tilt_backtest_metrics.csv", metrics)
    _write_csv(out / "v5f_momentum_weight_tilt_backtest_yearly_performance.csv", yearly)
    _write_csv(out / "v5f_momentum_weight_tilt_backtest_rebalance_period_performance.csv", rebalance_period)
    _write_csv(out / "v5f_momentum_weight_tilt_backtest_drawdown_review.csv", drawdown)
    _write_csv(out / "v5f_momentum_weight_tilt_backtest_contribution_summary.csv", contribution)
    _write_csv(out / "v5f_momentum_weight_tilt_backtest_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_momentum_weight_tilt_backtest_next_queue.csv", next_queue)
    _write_csv(out / "v5f_momentum_weight_tilt_backtest_blockers.csv", blockers_out)
    (out / "v5f_momentum_weight_tilt_backtest_report.md").write_text(
        _report(metrics, yearly, rebalance_period, drawdown, decision),
        encoding="utf-8",
    )
    (out / "v5f_momentum_weight_tilt_backtest_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    stress = next(row for row in metrics if row["version_id"] == STRESS)
    summary = _summary(
        "completed_v5f_momentum_weight_tilt_backtest_scope",
        decision[0]["pm_gate_decision"],
        [],
        actual_first_trade_date=str(daily["trade_date"].min()),
        actual_last_trade_date=str(daily["trade_date"].max()),
        primary_delta_return_pct_points=float(primary["delta_return_pct_points_vs_baseline_proxy"]),
        primary_delta_max_drawdown_pct_points=float(primary["delta_max_drawdown_pct_points_vs_baseline_proxy"]),
        stress_delta_return_pct_points=float(stress["delta_return_pct_points_vs_baseline_proxy"]),
    )
    _write_json(out / "v5f_momentum_weight_tilt_backtest_summary.json", summary)
    return summary


def _scope_audit(
    daily: pd.DataFrame,
    weights: pd.DataFrame,
    historical: dict[str, Any],
    pm_summary: dict[str, Any],
    governance: list[dict[str, str]],
) -> list[dict[str, Any]]:
    first_trade = str(daily["trade_date"].min())
    last_trade = str(daily["trade_date"].max())
    checks = [
        ("declared_backtest_start", historical.get("backtest_scope_start") == BACKTEST_SCOPE_START, historical.get("backtest_scope_start")),
        ("declared_backtest_end", historical.get("backtest_scope_end") == BACKTEST_SCOPE_END, historical.get("backtest_scope_end")),
        ("actual_first_trade_inside_scope", first_trade >= BACKTEST_SCOPE_START, first_trade),
        ("actual_last_trade_inside_scope", last_trade <= BACKTEST_SCOPE_END, last_trade),
        ("primary_present", PRIMARY in set(daily["version_id"]), PRIMARY),
        ("baseline_present", BASELINE in set(daily["version_id"]), BASELINE),
        ("rebalance_dates_inside_scope", weights["rebalance_date"].between(BACKTEST_SCOPE_START, BACKTEST_SCOPE_END).all(), f"{weights['rebalance_date'].min()} to {weights['rebalance_date'].max()}"),
        ("pm_review_not_accepted", not pm_summary.get("accepted") and not pm_summary.get("live_trading_approved"), pm_summary.get("pm_gate_decision")),
        ("governance_clean", all(row["status"] == "pass" for row in governance), "limited engineering governance audit"),
        ("threshold_scan_false", not pm_summary.get("threshold_scan_used"), pm_summary.get("threshold_scan_used")),
        ("new_buy_signal_false", not pm_summary.get("new_buy_signal_used"), pm_summary.get("new_buy_signal_used")),
        ("v57f_core_modified_false", not pm_summary.get("v57f_core_modified"), pm_summary.get("v57f_core_modified")),
    ]
    return [{"check_id": check_id, "status": "pass" if ok else "fail", "detail": detail} for check_id, ok, detail in checks]


def _yearly_performance(daily: pd.DataFrame) -> list[dict[str, Any]]:
    df = daily.copy()
    df["year"] = df["trade_date"].str.slice(0, 4)
    rows: list[dict[str, Any]] = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        nav_factor = (1.0 + pd.to_numeric(group["strategy_return"])).prod()
        rows.append({"version_id": version, "year": year, "period_return": nav_factor - 1.0, "trade_days": len(group)})
    baseline_by_year = {row["year"]: float(row["period_return"]) for row in rows if row["version_id"] == BASELINE}
    for row in rows:
        row["delta_return_pct_points_vs_baseline"] = (float(row["period_return"]) - baseline_by_year.get(row["year"], 0.0)) * 100
    return rows


def _rebalance_period_performance(daily: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (version, period), group in daily.groupby(["version_id", "active_rebalance_date"], sort=True):
        nav_factor = (1.0 + pd.to_numeric(group["strategy_return"])).prod()
        rows.append({"version_id": version, "active_rebalance_date": period, "period_return": nav_factor - 1.0, "trade_days": len(group)})
    baseline_by_period = {row["active_rebalance_date"]: float(row["period_return"]) for row in rows if row["version_id"] == BASELINE}
    for row in rows:
        row["delta_return_pct_points_vs_baseline"] = (float(row["period_return"]) - baseline_by_period.get(row["active_rebalance_date"], 0.0)) * 100
    return rows


def _drawdown_review(daily: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for version, group in daily.groupby("version_id", sort=True):
        ordered = group.sort_values("trade_date")
        nav = pd.to_numeric(ordered["strategy_nav"]).reset_index(drop=True)
        dates = ordered["trade_date"].reset_index(drop=True)
        running_peak = nav.cummax()
        dd = nav / running_peak - 1.0
        trough_idx = int(dd.idxmin())
        peak_idx = int(nav.iloc[: trough_idx + 1].idxmax())
        rows.append(
            {
                "version_id": version,
                "max_drawdown": abs(float(dd.iloc[trough_idx])),
                "peak_date": dates.iloc[peak_idx],
                "trough_date": dates.iloc[trough_idx],
                "accepted": False,
            }
        )
    baseline_dd = next(float(row["max_drawdown"]) for row in rows if row["version_id"] == BASELINE)
    for row in rows:
        row["delta_max_drawdown_pct_points_vs_baseline"] = (float(row["max_drawdown"]) - baseline_dd) * 100
    return rows


def _contribution_summary(daily: pd.DataFrame) -> list[dict[str, Any]]:
    pivot = daily.pivot(index="trade_date", columns="version_id", values="strategy_return").fillna(0.0)
    rows = []
    for version in [PRIMARY, STRESS]:
        diff = pivot[version] - pivot[BASELINE]
        rows.append(
            {
                "version_id": version,
                "positive_relative_days": int((diff > 0).sum()),
                "negative_relative_days": int((diff < 0).sum()),
                "mean_daily_delta_return": float(diff.mean()),
                "median_daily_delta_return": float(diff.median()),
                "top_positive_day": str(diff.idxmax()),
                "top_positive_day_delta_return": float(diff.max()),
                "top_negative_day": str(diff.idxmin()),
                "top_negative_day_delta_return": float(diff.min()),
            }
        )
    return rows


def _pm_decision(scope_audit: list[dict[str, Any]], metrics: list[dict[str, str]]) -> list[dict[str, Any]]:
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    passed = all(row["status"] == "pass" for row in scope_audit)
    positive = float(primary["delta_return_pct_points_vs_baseline_proxy"]) > 0
    drawdown_ok = float(primary["delta_max_drawdown_pct_points_vs_baseline_proxy"]) <= 0
    if passed and positive and drawdown_ok:
        decision = "backtest_scope_positive_keep_forward_paper_candidate_not_accepted"
        rationale = "Fixed 12-1 within-sleeve weight tilt is positive over the declared backtest scope and passes governance, but remains forward/paper only."
    elif passed and positive:
        decision = "backtest_scope_positive_but_drawdown_note_not_accepted"
        rationale = "Return is positive but drawdown is not clean enough for promotion beyond diagnostic/forward review."
    else:
        decision = "backtest_scope_diagnostic_only_not_accepted"
        rationale = "Backtest-scope evidence is not sufficient."
    return [
        {
            "pm_gate_decision": decision,
            "candidate_id": PRIMARY,
            "delta_return_pct_points_vs_baseline_proxy": primary["delta_return_pct_points_vs_baseline_proxy"],
            "delta_max_drawdown_pct_points_vs_baseline_proxy": primary["delta_max_drawdown_pct_points_vs_baseline_proxy"],
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Keep V5f momentum weight tilt in forward/paper tracking", "allowed": decision.startswith("backtest_scope_positive"), "requires_threshold_scan": False},
        {"priority": 2, "task": "Use next official V57f rebalance to populate paper signal template", "allowed": True, "requires_threshold_scan": False},
        {"priority": 3, "task": "Deployment governance review before any simulated/live use", "allowed": True, "requires_threshold_scan": False},
        {"priority": 4, "task": "Scan windows or tilt multipliers", "allowed": False, "requires_threshold_scan": True},
    ]


def _blockers(scope_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in scope_audit if row["status"] != "pass"]
    if not failed:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Backtest scope validation passed."}]
    return [{"blocker_id": row["check_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    actual_first_trade_date: str = "",
    actual_last_trade_date: str = "",
    primary_delta_return_pct_points: float = 0.0,
    primary_delta_max_drawdown_pct_points: float = 0.0,
    stress_delta_return_pct_points: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_momentum_weight_tilt_backtest_scope",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_SCOPE_START,
        "backtest_scope_end": BACKTEST_SCOPE_END,
        "actual_first_trade_date": actual_first_trade_date,
        "actual_last_trade_date": actual_last_trade_date,
        "primary_candidate": PRIMARY,
        "primary_delta_return_pct_points_vs_baseline_proxy": primary_delta_return_pct_points,
        "primary_delta_max_drawdown_pct_points_vs_baseline_proxy": primary_delta_max_drawdown_pct_points,
        "stress_reference_delta_return_pct_points_vs_baseline_proxy": stress_delta_return_pct_points,
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


def _report(
    metrics: list[dict[str, str]],
    yearly: list[dict[str, Any]],
    rebalance_period: list[dict[str, Any]],
    drawdown: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    stress = next(row for row in metrics if row["version_id"] == STRESS)
    baseline = next(row for row in metrics if row["version_id"] == BASELINE)
    primary_years = [row for row in yearly if row["version_id"] == PRIMARY]
    positive_years = sum(1 for row in primary_years if float(row["delta_return_pct_points_vs_baseline"]) > 0)
    primary_periods = [row for row in rebalance_period if row["version_id"] == PRIMARY]
    positive_periods = sum(1 for row in primary_periods if float(row["delta_return_pct_points_vs_baseline"]) > 0)
    return "\n".join(
        [
            "# V5f Momentum Weight Tilt Backtest Scope Validation",
            "",
            f"- Backtest scope: `{BACKTEST_SCOPE_START}` to `{BACKTEST_SCOPE_END}`.",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`.",
            "- Status: candidate for forward/paper tracking only; not accepted.",
            f"- Baseline return: {float(baseline['strategy_return']) * 100:.4f}%.",
            f"- Primary 12-1 return: {float(primary['strategy_return']) * 100:.4f}%, delta {float(primary['delta_return_pct_points_vs_baseline_proxy']):.4f} pct points.",
            f"- Primary max drawdown: {float(primary['max_drawdown']) * 100:.4f}%, delta {float(primary['delta_max_drawdown_pct_points_vs_baseline_proxy']):.4f} pct points.",
            f"- Stress 9-1 return delta: {float(stress['delta_return_pct_points_vs_baseline_proxy']):.4f} pct points.",
            f"- Positive relative years: {positive_years}/{len(primary_years)}.",
            f"- Positive relative rebalance periods: {positive_periods}/{len(primary_periods)}.",
            "",
            "## Drawdown Windows",
            *[
                f"- `{row['version_id']}`: max drawdown {float(row['max_drawdown']) * 100:.4f}% from {row['peak_date']} to {row['trough_date']}."
                for row in drawdown
            ],
            "",
            "## Governance",
            "- No V57f core modification.",
            "- No full-market momentum stock selection.",
            "- No new buy signal.",
            "- No threshold scan.",
            "- Not accepted and not live approved.",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Momentum Weight Tilt Backtest Scope Rules",
            "",
            "- Historical window is fixed at 2021-05-01 to 2026-05-31.",
            "- Use only existing V57f selected stocks.",
            "- Apply fixed 12-1 same-sleeve tilt only as reviewed.",
            "- Do not scan windows or tilt strength.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        ENG_DIR / "v5f_momentum_weight_tilt_daily_returns.csv",
        ENG_DIR / "v5f_momentum_weight_tilt_weights.csv",
        ENG_DIR / "v5f_momentum_weight_tilt_metrics.csv",
        ENG_DIR / "v5f_momentum_weight_tilt_governance_audit.csv",
        PM_DIR / "v5f_momentum_weight_tilt_pm_quant_summary.json",
        HISTORICAL_CLOSEOUT,
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
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5f_momentum_weight_tilt_backtest_scope(Path(".")), ensure_ascii=False, indent=2))
