from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_structural_rough_screen_runner import (
    BASELINE,
    REPAIRED_RUN,
    _daily_returns,
    _drawdown,
    _load_prices,
    _metrics,
    _safe_float,
    _sleeve_contribution,
    _yearly,
)


OUT_DIR = Path("v5c_key_metric_confidence_tilt_overlay") / "current"

PRIMARY = "internal_subsleeve_mom12_70_30"
V5F_WEIGHTS = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_weights.csv"
V5F_METRICS = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_metrics.csv"
KEY_METRIC_SUMMARY = Path("v5c_key_weight_metric_prediction") / "current" / "v5c_key_weight_metric_prediction_summary.json"
KEY_METRIC_PANEL = Path("v5c_key_weight_metric_prediction") / "current" / "v5c_key_weight_metric_formal_prediction_panel.csv"

VARIANTS: tuple[dict[str, Any], ...] = (
    {
        "version_id": "v5c_keymetric_risk_cap_only",
        "test_order": 1,
        "reward_multiplier": 1.0,
        "penalty_multiplier": 0.95,
        "scope": "all_sleeves",
        "rule": "Only cap quality-watch names by 5%; no reward for support.",
    },
    {
        "version_id": "v5c_keymetric_support_tilt_5pct",
        "test_order": 2,
        "reward_multiplier": 1.05,
        "penalty_multiplier": 0.95,
        "scope": "all_sleeves",
        "rule": "Strong support x1.05, quality watch x0.95, sleeve-normalized.",
    },
    {
        "version_id": "v5c_keymetric_support_tilt_10pct",
        "test_order": 3,
        "reward_multiplier": 1.10,
        "penalty_multiplier": 0.90,
        "scope": "all_sleeves",
        "rule": "Strong support x1.10, quality watch x0.90, sleeve-normalized.",
    },
    {
        "version_id": "v5c_keymetric_bank_only_confidence_tilt",
        "test_order": 4,
        "reward_multiplier": 1.05,
        "penalty_multiplier": 0.95,
        "scope": "bank",
        "rule": "Bank sleeve only: strong support x1.05, quality watch x0.95.",
    },
    {
        "version_id": "v5c_keymetric_power_plus_bank_confidence_tilt",
        "test_order": 5,
        "reward_multiplier": 1.05,
        "penalty_multiplier": 0.95,
        "scope": "bank;utilities_electricity",
        "rule": "Bank and electricity only: strong support x1.05, quality watch x0.95.",
    },
)

FIXED_METRICS_BY_SLEEVE: dict[str, tuple[str, ...]] = {
    "bank": ("low_pb", "bank_npl", "bank_provision", "bank_cet1"),
    "utilities_electricity": ("low_pb", "dividend_yield", "asset_liability", "capex_burden"),
    "highway_infrastructure": ("low_pb", "dividend_yield", "asset_liability"),
    "port_rail_infrastructure": ("low_pb", "dividend_yield", "asset_liability"),
}


def run_v5c_key_metric_confidence_tilt_overlay(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_key_metric_confidence_tilt_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_missing_required_input", blockers)
        _write_json(out / "v5c_key_metric_confidence_tilt_summary.json", summary)
        return summary

    prices = _load_prices(root)
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    weights_df = pd.read_csv(root / V5F_WEIGHTS, dtype=str)
    v5f_metrics = pd.read_csv(root / V5F_METRICS, dtype=str)
    key_panel = pd.read_csv(root / KEY_METRIC_PANEL, dtype=str)

    spec = _rule_spec()
    support_scores = _support_score_panel(key_panel)
    weights = _build_weights(weights_df, support_scores)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    drawdown = _drawdown(daily)
    sleeve = _sleeve_contribution(weights, prices)
    comparison = _comparison(metrics, v5f_metrics)
    governance = _governance(weights, support_scores)
    decision = _pm_gate_decision(comparison, governance)
    next_queue = _next_queue(decision[0], comparison)
    blockers_out = _blockers(governance)

    _write_csv(out / "v5c_key_metric_confidence_tilt_rule_spec.csv", spec)
    _write_csv(out / "v5c_key_metric_confidence_support_score_panel.csv", support_scores)
    _write_csv(out / "v5c_key_metric_confidence_tilt_weights.csv", weights)
    _write_csv(out / "v5c_key_metric_confidence_tilt_daily_returns.csv", daily)
    _write_csv(out / "v5c_key_metric_confidence_tilt_metrics.csv", metrics)
    _write_csv(out / "v5c_key_metric_confidence_tilt_yearly.csv", yearly)
    _write_csv(out / "v5c_key_metric_confidence_tilt_drawdown.csv", drawdown)
    _write_csv(out / "v5c_key_metric_confidence_tilt_sleeve_contribution.csv", sleeve)
    _write_csv(out / "v5c_key_metric_confidence_tilt_comparison.csv", comparison)
    _write_csv(out / "v5c_key_metric_confidence_tilt_governance_audit.csv", governance)
    _write_csv(out / "v5c_key_metric_confidence_tilt_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_key_metric_confidence_tilt_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_key_metric_confidence_tilt_blockers.csv", blockers_out)
    (out / "v5c_key_metric_confidence_tilt_report.md").write_text(
        _report(comparison, decision),
        encoding="utf-8",
    )
    (out / "v5c_key_metric_confidence_tilt_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = next((row for row in comparison if row["rank"] == 1), {})
    summary = _summary(
        "completed_key_metric_confidence_tilt_overlay",
        decision[0]["pm_gate_decision"],
        blockers_out,
        best_version=best.get("version_id", ""),
        best_delta_return_vs_v5f_primary=float(best.get("delta_return_pct_points_vs_v5f_primary", 0.0) or 0.0),
        best_delta_drawdown_vs_v5f_primary=float(best.get("delta_max_drawdown_pct_points_vs_v5f_primary", 0.0) or 0.0),
        tested_variant_count=len(VARIANTS),
        support_score_rows=len(support_scores),
    )
    _write_json(out / "v5c_key_metric_confidence_tilt_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _support_score_panel(key_panel: pd.DataFrame) -> list[dict[str, Any]]:
    panel = key_panel[key_panel["sample_scope"] == "formal_backtest_observation"].copy()
    panel = panel[panel.apply(lambda row: row["metric_id"] in FIXED_METRICS_BY_SLEEVE.get(row["sleeve_id"], ()), axis=1)].copy()
    rows = []
    for (date, code, sleeve), group in panel.groupby(["trade_date", "code", "sleeve_id"], sort=True):
        favorable = int((group["predicted_next_bucket"] == "favorable").sum())
        unfavorable = int((group["predicted_next_bucket"] == "unfavorable").sum())
        middle = int((group["predicted_next_bucket"] == "middle").sum())
        count = len(group)
        raw_score = favorable - unfavorable
        avg_score = raw_score / count if count else 0.0
        if count == 0:
            state = "missing"
        elif avg_score >= 0.5:
            state = "strong_support"
        elif avg_score <= -0.5:
            state = "quality_watch"
        else:
            state = "neutral"
        rows.append(
            {
                "rebalance_date": date,
                "code": code,
                "sleeve": sleeve,
                "metric_count": count,
                "favorable_count": favorable,
                "middle_count": middle,
                "unfavorable_count": unfavorable,
                "support_score": avg_score,
                "confidence_state": state,
                "metrics_used": ";".join(group["metric_id"].tolist()),
                "buckets": ";".join(f"{row['metric_id']}={row['predicted_next_bucket']}" for _, row in group.iterrows()),
                "trade_impact": "none",
                "accepted": False,
            }
        )
    return rows


def _build_weights(weights_df: pd.DataFrame, support_scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = weights_df[weights_df["version_id"] == BASELINE].copy()
    primary = weights_df[weights_df["version_id"] == PRIMARY].copy()
    rows = [_row_from_existing(row) for _, row in baseline.iterrows()]
    rows.extend(_row_from_existing(row) for _, row in primary.iterrows())
    score_map = {(row["rebalance_date"], row["code"]): row for row in support_scores}
    for variant in VARIANTS:
        tmp = primary.copy()
        tmp["version_id"] = variant["version_id"]
        tmp["family"] = "v5c_key_metric_confidence_tilt"
        tmp["base_target_weight"] = pd.to_numeric(tmp["base_target_weight"], errors="coerce")
        tmp["target_weight"] = pd.to_numeric(tmp["target_weight"], errors="coerce")
        tmp["confidence_state"] = "missing"
        tmp["support_score"] = 0.0
        tmp["tilt_multiplier"] = 1.0
        for idx, row in tmp.iterrows():
            score = score_map.get((row["rebalance_date"], row["code"]), {})
            state = score.get("confidence_state", "missing")
            tmp.at[idx, "confidence_state"] = state
            tmp.at[idx, "support_score"] = score.get("support_score", 0.0)
            if not _scope_applies(str(variant["scope"]), str(row["sleeve"])):
                multiplier = 1.0
            elif state == "strong_support":
                multiplier = float(variant["reward_multiplier"])
            elif state == "quality_watch":
                multiplier = float(variant["penalty_multiplier"])
            else:
                multiplier = 1.0
            tmp.at[idx, "tilt_multiplier"] = multiplier
        tmp["primary_target_weight"] = pd.to_numeric(tmp["target_weight"], errors="coerce")
        tmp["tilted_raw_weight"] = tmp["primary_target_weight"] * pd.to_numeric(tmp["tilt_multiplier"], errors="coerce")
        for (date, sleeve), group in tmp.groupby(["rebalance_date", "sleeve"], sort=True):
            idx = group.index
            primary_total = pd.to_numeric(group["primary_target_weight"], errors="coerce").sum()
            raw_total = pd.to_numeric(group["tilted_raw_weight"], errors="coerce").sum()
            if raw_total:
                tmp.loc[idx, "target_weight"] = pd.to_numeric(group["tilted_raw_weight"], errors="coerce") * primary_total / raw_total
            else:
                tmp.loc[idx, "target_weight"] = pd.to_numeric(group["primary_target_weight"], errors="coerce")
        tmp["weight_delta"] = pd.to_numeric(tmp["target_weight"], errors="coerce") - pd.to_numeric(tmp["base_target_weight"], errors="coerce")
        rows.extend(_variant_row(row, variant) for _, row in tmp.iterrows())
    return rows


def _row_from_existing(row: pd.Series) -> dict[str, Any]:
    return {
        "version_id": row["version_id"],
        "family": row.get("family", ""),
        "rebalance_date": row["rebalance_date"],
        "code": row["code"],
        "sleeve": row["sleeve"],
        "base_target_weight": row["base_target_weight"],
        "target_weight": row["target_weight"],
        "weight_delta": row["weight_delta"],
        "confidence_state": "reference",
        "support_score": "",
        "tilt_multiplier": 1.0,
        "bucket": row.get("bucket", ""),
        "sleeve_weight_preserved": row.get("sleeve_weight_preserved", "True"),
        "new_stock_selected": False,
        "accepted": False,
    }


def _variant_row(row: pd.Series, variant: dict[str, Any]) -> dict[str, Any]:
    return {
        "version_id": row["version_id"],
        "family": row.get("family", "v5c_key_metric_confidence_tilt"),
        "rebalance_date": row["rebalance_date"],
        "code": row["code"],
        "sleeve": row["sleeve"],
        "base_target_weight": row["base_target_weight"],
        "primary_target_weight": row["primary_target_weight"],
        "target_weight": row["target_weight"],
        "weight_delta": row["weight_delta"],
        "confidence_state": row["confidence_state"],
        "support_score": row["support_score"],
        "tilt_multiplier": row["tilt_multiplier"],
        "variant_scope": variant["scope"],
        "bucket": f"confidence_{row['confidence_state']}",
        "sleeve_weight_preserved": True,
        "new_stock_selected": False,
        "accepted": False,
    }


def _scope_applies(scope: str, sleeve: str) -> bool:
    if scope == "all_sleeves":
        return True
    return sleeve in set(scope.split(";"))


def _rule_spec() -> list[dict[str, Any]]:
    metric_rows = [
        {
            "spec_type": "metric_set",
            "sleeve": sleeve,
            "metric_ids": ";".join(metrics),
            "selection_basis": "pre_registered_key_weight_metrics_not_formal_return_tuned",
            "accepted": False,
        }
        for sleeve, metrics in FIXED_METRICS_BY_SLEEVE.items()
    ]
    variant_rows = [
        {
            "spec_type": "variant",
            "test_order": row["test_order"],
            "version_id": row["version_id"],
            "scope": row["scope"],
            "reward_multiplier": row["reward_multiplier"],
            "penalty_multiplier": row["penalty_multiplier"],
            "rule": row["rule"],
            "sleeve_normalized": True,
            "new_stock_selected": False,
            "accepted": False,
        }
        for row in VARIANTS
    ]
    return metric_rows + variant_rows


def _comparison(metrics: list[dict[str, Any]], v5f_metrics: pd.DataFrame) -> list[dict[str, Any]]:
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    baseline = next(row for row in metrics if row["version_id"] == BASELINE)
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        delta_vs_primary = (float(row["strategy_return"]) - float(primary["strategy_return"])) * 100
        dd_vs_primary = (float(row["max_drawdown"]) - float(primary["max_drawdown"])) * 100
        status = "reference_primary" if row["version_id"] == PRIMARY else _status(delta_vs_primary, dd_vs_primary)
        rows.append(
            {
                "version_id": row["version_id"],
                "family": "v5f_primary_reference" if row["version_id"] == PRIMARY else "v5c_key_metric_confidence_tilt",
                "strategy_return": row["strategy_return"],
                "annualized_return": row["annualized_return"],
                "max_drawdown": row["max_drawdown"],
                "volatility": row["volatility"],
                "sharpe_proxy": row["sharpe_proxy"],
                "turnover_proxy": row["turnover_proxy"],
                "incremental_commission_total": row["incremental_commission_total"],
                "delta_return_pct_points_vs_repaired_baseline": (float(row["strategy_return"]) - float(baseline["strategy_return"])) * 100,
                "delta_return_pct_points_vs_v5f_primary": delta_vs_primary,
                "delta_max_drawdown_pct_points_vs_v5f_primary": dd_vs_primary,
                "status": status,
                "accepted": False,
            }
        )
    ranked = sorted([row for row in rows if row["version_id"] != PRIMARY], key=lambda item: float(item["delta_return_pct_points_vs_v5f_primary"]), reverse=True)
    for idx, row in enumerate(ranked, start=1):
        row["rank"] = idx
    primary_row = next(row for row in rows if row["version_id"] == PRIMARY)
    primary_row["rank"] = len(ranked) + 1
    return ranked + [primary_row]


def _status(delta_return: float, delta_dd: float) -> str:
    if delta_return > 0 and delta_dd <= 0:
        return "positive_increment_forward_observation_not_accepted"
    if delta_return > 0:
        return "positive_return_but_drawdown_worse_diagnostic"
    return "no_increment_vs_v5f_primary_diagnostic"


def _governance(weights: list[dict[str, Any]], support_scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    sleeve_check = _sleeve_weight_check(df)
    return [
        {"audit_id": "v5f_primary_unchanged", "status": "pass", "detail": PRIMARY},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
        {"audit_id": "selected_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": "no new stocks"},
        {"audit_id": "same_sleeve_normalized", "status": "pass" if sleeve_check else "fail", "detail": "target sleeve totals match primary sleeve totals"},
        {"audit_id": "fixed_variant_order_no_scan", "status": "pass", "detail": ";".join(row["version_id"] for row in VARIANTS)},
        {"audit_id": "accepted_false", "status": "pass" if not df["accepted"].astype(str).eq("True").any() else "fail", "detail": False},
        {"audit_id": "support_scores_available", "status": "pass" if support_scores else "fail", "detail": len(support_scores)},
    ]


def _sleeve_weight_check(df: pd.DataFrame) -> bool:
    primary = df[df["version_id"] == PRIMARY].copy()
    target = df[df["version_id"].isin([row["version_id"] for row in VARIANTS])].copy()
    primary_totals = primary.groupby(["rebalance_date", "sleeve"])["target_weight"].apply(lambda s: pd.to_numeric(s, errors="coerce").sum()).to_dict()
    for (version, date, sleeve), group in target.groupby(["version_id", "rebalance_date", "sleeve"], sort=True):
        total = pd.to_numeric(group["target_weight"], errors="coerce").sum()
        if abs(total - primary_totals.get((date, sleeve), 0.0)) > 1e-8:
            return False
    return True


def _pm_gate_decision(comparison: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    positive = [row for row in comparison if row["version_id"] != PRIMARY and row["status"] == "positive_increment_forward_observation_not_accepted"]
    if not gov_ok:
        gate = "key_metric_confidence_tilt_blocked_by_governance"
        next_step = "repair_governance"
    elif positive:
        gate = "key_metric_confidence_tilt_positive_forward_observation_not_accepted"
        next_step = positive[0]["version_id"]
    else:
        gate = "key_metric_confidence_tilt_no_incremental_value_diagnostic"
        next_step = "keep_v5f_primary_unchanged"
    return [
        {
            "pm_gate_decision": gate,
            "positive_candidate_count": len(positive),
            "next_step": next_step,
            "accepted": False,
            "live_approved": False,
            "v57f_core_modified": False,
            "v5f_primary_modified": False,
        }
    ]


def _next_queue(decision: dict[str, Any], comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "priority": 1,
            "next_task": "Keep internal_subsleeve_mom12_70_30 as V5f primary.",
            "allowed": True,
            "requires_acceptance": False,
        }
    ]
    positives = [row for row in comparison if row["status"] == "positive_increment_forward_observation_not_accepted"]
    if positives:
        rows.append(
            {
                "priority": 2,
                "next_task": f"Open forward observation for {positives[0]['version_id']} only.",
                "allowed": True,
                "requires_acceptance": False,
            }
        )
    rows.append(
        {
            "priority": 3,
            "next_task": "Do not open accepted/live approval or threshold scan.",
            "allowed": False,
            "requires_acceptance": True,
        }
    )
    return rows


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    return [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]}
        for row in failed
    ] or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "completed"}]


def _report(comparison: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    lines = [
        "# V5c Key Metric Confidence Tilt Overlay",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        "- Accepted: false",
        "- V5f primary modified: false",
        "",
        "## Comparison Vs V5f Primary",
    ]
    for row in comparison:
        lines.append(
            f"- `{row['version_id']}`: return {float(row['strategy_return']) * 100:.2f}%, delta vs V5f {float(row['delta_return_pct_points_vs_v5f_primary']):.4f} pct, drawdown delta {float(row['delta_max_drawdown_pct_points_vs_v5f_primary']):.4f} pct, status={row['status']}"
        )
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return """# Agent Execution Rules

- V5f primary remains `internal_subsleeve_mom12_70_30`.
- Use only fixed key metric confidence states.
- Do not add stocks, remove stocks, or cross sleeves.
- Normalize within each sleeve to preserve V5f sleeve totals.
- Do not scan thresholds or mark accepted.
"""


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [V5F_WEIGHTS, V5F_METRICS, KEY_METRIC_SUMMARY, KEY_METRIC_PANEL, REPAIRED_RUN / "daily_returns.csv"]
    return [
        {
            "blocker_id": str(path).replace("\\", "/"),
            "severity": "fatal",
            "status": "missing_required_input",
            "description": "Required local input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _summary(status: str, gate: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": status,
        "pm_gate_decision": gate,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accepted": False,
        "live_approved": False,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "threshold_scan_used": False,
        "new_stock_selected": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "blocker_count": len(blockers),
    }
    summary.update(extra)
    return summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run_v5c_key_metric_confidence_tilt_overlay()
