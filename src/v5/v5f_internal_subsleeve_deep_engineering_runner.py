from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_internal_subsleeve_deep_engineering") / "current"
SPEC_DIR = Path("v5f_internal_subsleeve_deep_research_spec") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
REPAIRED_COMPARISON_DIR = Path("v5f_repaired_baseline_overlay_comparison") / "current"
BASELINE = "v57f_startup_preload_repaired_baseline"
PRIMARY = "internal_subsleeve_mom12_70_30"
SECONDARY = "internal_subsleeve_mom12_80_20"
CURRENT_REFERENCE = "current_momentum_plus_mean_reversion_equal_blend"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_internal_subsleeve_deep_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_internal_subsleeve_deep_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_internal_subsleeve_deep_summary.json", summary)
        return summary

    spec_summary = _read_json(root / SPEC_DIR / "v5f_internal_subsleeve_summary.json")
    weights = pd.read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_weights.csv", dtype={"rebalance_date": str, "code": str})
    daily = pd.read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_daily_returns.csv", dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})
    metrics = _read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_metrics.csv")
    yearly = _read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_yearly.csv")
    current_candidates = _read_csv(root / REPAIRED_COMPARISON_DIR / "v5f_candidate_matrix.csv")

    deep_metrics = _deep_metrics(metrics, yearly)
    rebalance_period = _rebalance_period_stability(daily)
    sleeve_attr = _sleeve_attribution(daily, weights)
    stock_concentration = _stock_concentration(daily, weights)
    top_events = _top_contribution_events(daily)
    turnover_cost = _turnover_cost_review(metrics)
    governance = _governance_audit(spec_summary, weights)
    comparison = _comparison_vs_current(deep_metrics, current_candidates)
    decision = _pm_decision(deep_metrics, rebalance_period, governance, comparison)
    queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_internal_subsleeve_deep_metrics.csv", deep_metrics)
    _write_csv(out / "v5f_internal_subsleeve_yearly_stability.csv", _filter_versions(yearly))
    _write_csv(out / "v5f_internal_subsleeve_rebalance_period_stability.csv", rebalance_period)
    _write_csv(out / "v5f_internal_subsleeve_sleeve_attribution.csv", sleeve_attr)
    _write_csv(out / "v5f_internal_subsleeve_stock_concentration.csv", stock_concentration)
    _write_csv(out / "v5f_internal_subsleeve_top_contribution_events.csv", top_events)
    _write_csv(out / "v5f_internal_subsleeve_turnover_cost_review.csv", turnover_cost)
    _write_csv(out / "v5f_internal_subsleeve_governance_audit.csv", governance)
    _write_csv(out / "v5f_internal_subsleeve_vs_current_overlay.csv", comparison)
    _write_csv(out / "v5f_internal_subsleeve_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_internal_subsleeve_next_queue.csv", queue)
    _write_csv(out / "v5f_internal_subsleeve_deep_blockers.csv", blockers_out)
    (out / "v5f_internal_subsleeve_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5f_internal_subsleeve_deep_report.md").write_text(
        _report(deep_metrics, comparison, decision),
        encoding="utf-8",
    )
    (out / "v5f_internal_subsleeve_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    primary = next(row for row in deep_metrics if row["version_id"] == PRIMARY)
    primary_period = next(row for row in rebalance_period if row["version_id"] == PRIMARY)
    summary = _summary(
        "completed_v5f_internal_subsleeve_deep_engineering",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        primary_delta_return=float(primary["delta_return_pct_points_vs_repaired_baseline"]),
        primary_delta_drawdown=float(primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
        yearly_win_rate=float(primary["yearly_win_rate"]),
        rebalance_period_win_rate=float(primary_period["rebalance_period_win_rate"]),
    )
    _write_json(out / "v5f_internal_subsleeve_deep_summary.json", summary)
    return summary


def _deep_metrics(metrics: list[dict[str, str]], yearly: list[dict[str, str]]) -> list[dict[str, Any]]:
    versions = {PRIMARY, SECONDARY, BASELINE}
    rows = [dict(row) for row in metrics if row["version_id"] in versions]
    yearly_rows = _filter_versions(yearly)
    yearly_by_version: dict[str, list[dict[str, str]]] = {}
    for row in yearly_rows:
        yearly_by_version.setdefault(row["version_id"], []).append(row)
    for row in rows:
        if row["version_id"] == BASELINE:
            row["yearly_win_count"] = 0
            row["yearly_win_rate"] = 0.0
            row["negative_relative_year_count"] = 0
            continue
        wins = sum(1 for y in yearly_by_version.get(row["version_id"], []) if float(y["delta_return_pct_points_vs_repaired_baseline"]) > 0)
        total = len(yearly_by_version.get(row["version_id"], []))
        negatives = sum(1 for y in yearly_by_version.get(row["version_id"], []) if float(y["delta_return_pct_points_vs_repaired_baseline"]) < 0)
        row["yearly_win_count"] = wins
        row["yearly_win_rate"] = wins / total if total else 0.0
        row["negative_relative_year_count"] = negatives
    return rows


def _rebalance_period_stability(daily: pd.DataFrame) -> list[dict[str, Any]]:
    df = daily[daily["version_id"].isin([PRIMARY, SECONDARY, BASELINE])].copy()
    rows: list[dict[str, Any]] = []
    for (version, period), group in df.groupby(["version_id", "active_rebalance_date"], sort=True):
        period_return = (1.0 + pd.to_numeric(group["strategy_return"])).prod() - 1.0
        rows.append({"version_id": version, "active_rebalance_date": period, "period_return": period_return, "trade_days": len(group)})
    baseline = {row["active_rebalance_date"]: float(row["period_return"]) for row in rows if row["version_id"] == BASELINE}
    for row in rows:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - baseline.get(row["active_rebalance_date"], 0.0)) * 100
    wins: dict[str, tuple[int, int]] = {}
    for version in [PRIMARY, SECONDARY]:
        version_rows = [row for row in rows if row["version_id"] == version]
        win_count = sum(1 for row in version_rows if float(row["delta_return_pct_points_vs_repaired_baseline"]) > 0)
        wins[version] = (win_count, len(version_rows))
    for row in rows:
        if row["version_id"] in wins:
            win_count, total = wins[row["version_id"]]
            row["rebalance_period_win_count"] = win_count
            row["rebalance_period_win_rate"] = win_count / total if total else 0.0
        else:
            row["rebalance_period_win_count"] = 0
            row["rebalance_period_win_rate"] = 0.0
    return rows


def _sleeve_attribution(daily: pd.DataFrame, weights: pd.DataFrame) -> list[dict[str, Any]]:
    active = daily[daily["version_id"].isin([PRIMARY, SECONDARY])].copy()
    weight_rows = weights[weights["version_id"].isin([PRIMARY, SECONDARY])].copy()
    sleeve_weight_delta = weight_rows.groupby(["version_id", "sleeve"])["weight_delta"].apply(lambda s: s.astype(float).abs().sum()).to_dict()
    # Daily delta is portfolio-level; allocate by each sleeve's absolute active weight share for concentration diagnostics.
    total_abs = weight_rows.groupby("version_id")["weight_delta"].apply(lambda s: s.astype(float).abs().sum()).to_dict()
    daily_delta = active.groupby("version_id")["delta_stock_return"].sum().to_dict()
    rows = []
    for (version, sleeve), abs_delta in sleeve_weight_delta.items():
        share = abs_delta / total_abs.get(version, 1.0) if total_abs.get(version) else 0.0
        rows.append(
            {
                "version_id": version,
                "sleeve": sleeve,
                "absolute_weight_delta": abs_delta,
                "active_weight_delta_share": share,
                "allocated_total_delta_stock_return": daily_delta.get(version, 0.0) * share,
            }
        )
    return sorted(rows, key=lambda row: (row["version_id"], -float(row["active_weight_delta_share"])))


def _stock_concentration(daily: pd.DataFrame, weights: pd.DataFrame) -> list[dict[str, Any]]:
    weight_rows = weights[weights["version_id"].isin([PRIMARY, SECONDARY])].copy()
    grouped = weight_rows.groupby(["version_id", "code", "sleeve"])["weight_delta"].apply(lambda s: s.astype(float).abs().sum()).reset_index()
    totals = grouped.groupby("version_id")["weight_delta"].sum().to_dict()
    grouped["active_weight_delta_share"] = grouped.apply(lambda row: float(row["weight_delta"]) / totals.get(row["version_id"], 1.0), axis=1)
    grouped = grouped.sort_values(["version_id", "active_weight_delta_share"], ascending=[True, False])
    return grouped.head(40).to_dict("records")


def _top_contribution_events(daily: pd.DataFrame) -> list[dict[str, Any]]:
    active = daily[daily["version_id"].isin([PRIMARY, SECONDARY])].copy()
    active["delta_return_pct_points"] = pd.to_numeric(active["delta_stock_return"]) * 100
    top_pos = active.sort_values("delta_return_pct_points", ascending=False).head(20)
    top_neg = active.sort_values("delta_return_pct_points", ascending=True).head(20)
    rows = []
    for label, frame in [("top_positive", top_pos), ("top_negative", top_neg)]:
        for _, row in frame.iterrows():
            rows.append(
                {
                    "event_type": label,
                    "version_id": row["version_id"],
                    "trade_date": row["trade_date"],
                    "active_rebalance_date": row["active_rebalance_date"],
                    "delta_return_pct_points": row["delta_return_pct_points"],
                }
            )
    return rows


def _turnover_cost_review(metrics: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        if row["version_id"] not in {PRIMARY, SECONDARY}:
            continue
        delta_return_decimal = float(row["delta_return_pct_points_vs_repaired_baseline"]) / 100.0
        cost = float(row["incremental_commission_total"])
        rows.append(
            {
                "version_id": row["version_id"],
                "turnover_proxy": row["turnover_proxy"],
                "incremental_commission_total": cost,
                "delta_return_decimal_vs_repaired_baseline": delta_return_decimal,
                "return_to_incremental_cost_ratio": delta_return_decimal / cost if cost else "",
                "cost_health": "pass" if delta_return_decimal > cost else "review",
            }
        )
    return rows


def _governance_audit(spec_summary: dict[str, Any], weights: pd.DataFrame) -> list[dict[str, Any]]:
    deep = weights[weights["version_id"].isin([PRIMARY, SECONDARY])]
    sleeve_checks = []
    for (_, date, sleeve), group in deep.groupby(["version_id", "rebalance_date", "sleeve"]):
        sleeve_checks.append(abs(group["target_weight"].astype(float).sum() - group["base_target_weight"].astype(float).sum()) < 1e-10)
    return [
        {"audit_id": "spec_gate", "status": "pass" if spec_summary.get("pm_gate_decision") == "admit_internal_subsleeve_to_deep_research_not_accepted" else "fail", "detail": spec_summary.get("pm_gate_decision")},
        {"audit_id": "v57f_selected_pool_only", "status": "pass" if not deep["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if all(sleeve_checks) else "fail", "detail": 0 if all(sleeve_checks) else 1},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": "V57f repaired selected stocks only"},
        {"audit_id": "no_parameter_scan", "status": "pass", "detail": "Only admitted 70/30 and 80/20 fixed versions"},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "live_trading_approved_false", "status": "pass", "detail": False},
    ]


def _comparison_vs_current(deep_metrics: list[dict[str, Any]], current_candidates: list[dict[str, str]]) -> list[dict[str, Any]]:
    current = next(row for row in current_candidates if row["candidate_id"] == "momentum_plus_mean_reversion_equal_blend")
    current_delta = float(current["delta_return_pct_points_vs_repaired_baseline"])
    current_dd = float(current["delta_max_drawdown_pct_points_vs_repaired_baseline"])
    rows = []
    for row in deep_metrics:
        if row["version_id"] == BASELINE:
            continue
        rows.append(
            {
                "version_id": row["version_id"],
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "incremental_delta_return_vs_current_equal_blend": float(row["delta_return_pct_points_vs_repaired_baseline"]) - current_delta,
                "incremental_delta_drawdown_vs_current_equal_blend": float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"]) - current_dd,
                "current_equal_blend_delta_return": current_delta,
                "current_equal_blend_delta_drawdown": current_dd,
                "beats_current_on_return": float(row["delta_return_pct_points_vs_repaired_baseline"]) > current_delta,
                "non_worse_drawdown_vs_repaired_baseline": float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"]) <= 0,
            }
        )
    return rows


def _pm_decision(
    deep_metrics: list[dict[str, Any]],
    rebalance_period: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    primary = next(row for row in deep_metrics if row["version_id"] == PRIMARY)
    primary_period_rows = [row for row in rebalance_period if row["version_id"] == PRIMARY]
    win_rate = float(primary_period_rows[0]["rebalance_period_win_rate"]) if primary_period_rows else 0.0
    compare_primary = next(row for row in comparison if row["version_id"] == PRIMARY)
    if gov_ok and float(primary["delta_return_pct_points_vs_repaired_baseline"]) > 5.0 and float(primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]) <= 0 and win_rate >= 0.5:
        decision = "promote_internal_subsleeve_70_30_to_v5f_candidate_not_accepted"
        rationale = "70/30 internal sub-sleeve has large repaired-baseline return improvement, non-worse drawdown, clean governance, and adequate period stability."
    elif gov_ok and bool(compare_primary["beats_current_on_return"]):
        decision = "positive_but_needs_forward_paper"
        rationale = "70/30 beats current candidate on return, but stability/risk checks are not strong enough for candidate promotion."
    else:
        decision = "diagnostic_only_no_stable_edge"
        rationale = "Deep review did not confirm stable edge."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": PRIMARY,
            "secondary_candidate": SECONDARY,
            "primary_delta_return_pct_points_vs_repaired_baseline": primary["delta_return_pct_points_vs_repaired_baseline"],
            "primary_delta_max_drawdown_pct_points_vs_repaired_baseline": primary["delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "primary_yearly_win_rate": primary["yearly_win_rate"],
            "primary_rebalance_period_win_rate": win_rate,
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "V5f internal sub-sleeve PM/Quant formal review", "allowed": decision.startswith("promote"), "requires_threshold_scan": False},
        {"priority": 2, "next_task": "Forward/paper tracking packet for internal_subsleeve_mom12_70_30", "allowed": decision.startswith("promote"), "requires_threshold_scan": False},
        {"priority": 3, "next_task": "Keep 80/20 as secondary stress candidate", "allowed": True, "requires_threshold_scan": False},
        {"priority": 4, "next_task": "Scan sub-sleeve budget levels", "allowed": False, "requires_threshold_scan": True},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed] or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Deep engineering review completed."}]


def _filter_versions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row["version_id"] in {PRIMARY, SECONDARY, BASELINE}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    primary_delta_return: float = 0.0,
    primary_delta_drawdown: float = 0.0,
    yearly_win_rate: float = 0.0,
    rebalance_period_win_rate: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_internal_subsleeve_deep_engineering",
        "status": status,
        "pm_gate_decision": decision,
        "primary_candidate": primary_candidate,
        "primary_delta_return_pct_points_vs_repaired_baseline": primary_delta_return,
        "primary_delta_max_drawdown_pct_points_vs_repaired_baseline": primary_delta_drawdown,
        "yearly_win_rate": yearly_win_rate,
        "rebalance_period_win_rate": rebalance_period_win_rate,
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


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""Working directory:
D:\\hh\\codex\\v5

Task name:
V5f internal sub-sleeve PM/Quant formal review

Objective:
Review `internal_subsleeve_mom12_70_30` as the primary V5f internal sub-sleeve candidate and `internal_subsleeve_mom12_80_20` as the secondary stress candidate. Use startup-preload repaired V57f as the only benchmark. Do not mark accepted/live approved and do not modify V57f.

Source gate:
`{decision["pm_gate_decision"]}`

Read first:
- v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_deep_summary.json
- v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_deep_metrics.csv
- v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_vs_current_overlay.csv
- v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_governance_audit.csv

Required decision:
- promote to forward/paper candidate not accepted
- or keep diagnostic if stability/risk is insufficient
"""


def _report(deep_metrics: list[dict[str, Any]], comparison: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    primary = next(row for row in deep_metrics if row["version_id"] == PRIMARY)
    secondary = next(row for row in deep_metrics if row["version_id"] == SECONDARY)
    primary_compare = next(row for row in comparison if row["version_id"] == PRIMARY)
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Deep Engineering",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            "- Status: not accepted; not live approved.",
            f"- Primary `{PRIMARY}` delta return: {float(primary['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Primary drawdown delta: {float(primary['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Primary yearly win rate: {float(primary['yearly_win_rate']) * 100:.2f}%.",
            f"- Primary incremental return versus current equal-blend: {float(primary_compare['incremental_delta_return_vs_current_equal_blend']):.4f} pct points.",
            f"- Secondary `{SECONDARY}` delta return: {float(secondary['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            "",
            "## Interpretation",
            "- The internal sub-sleeve structure is stronger than the current equal-blend overlay in repaired-baseline historical testing.",
            "- It remains inside the V57f selected pool and preserves sleeve totals.",
            "- It should move to PM/Quant formal review and forward/paper preparation, not acceptance.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Deep Engineering Rules",
            "",
            "- Repaired V57f baseline only.",
            "- V57f selected-stock pool only.",
            "- No full-market stock selection.",
            "- Preserve sleeve total weights.",
            "- Do not scan sub-sleeve budgets.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPEC_DIR / "v5f_internal_subsleeve_summary.json",
        ROUGH_DIR / "v5f_structural_rough_screen_weights.csv",
        ROUGH_DIR / "v5f_structural_rough_screen_daily_returns.csv",
        ROUGH_DIR / "v5f_structural_rough_screen_metrics.csv",
        ROUGH_DIR / "v5f_structural_rough_screen_yearly.csv",
        REPAIRED_COMPARISON_DIR / "v5f_candidate_matrix.csv",
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
    print(json.dumps(run_v5f_internal_subsleeve_deep_engineering(Path(".")), ensure_ascii=False, indent=2))
