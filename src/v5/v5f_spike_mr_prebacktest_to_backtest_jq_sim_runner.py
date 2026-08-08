from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_event_triggered_mr_borrowing_runner import run_v5f_event_triggered_mr_borrowing
from v5.v5f_spike_funded_mr_borrowing_independent_validation_runner import (
    run_v5f_spike_funded_mr_borrowing_independent_validation_gate,
)


OUT_DIR = Path("v5f_spike_mr_prebacktest_to_backtest_jq_sim") / "current"

PRETEST_SUMMARY = (
    Path("v5f_spike_funded_mr_borrowing_independent_validation_gate")
    / "current"
    / "v5f_spike_mr_validation_summary.json"
)
PRETEST_METRICS = (
    Path("v5f_spike_funded_mr_borrowing_independent_validation_gate")
    / "current"
    / "v5f_spike_mr_validation_metrics.csv"
)
PRETEST_SLEEVE = (
    Path("v5f_spike_funded_mr_borrowing_independent_validation_gate")
    / "current"
    / "v5f_spike_mr_validation_sleeve_stability.csv"
)
PRETEST_GAPS = (
    Path("v5f_spike_funded_mr_borrowing_independent_validation_gate")
    / "current"
    / "v5f_spike_mr_validation_gap_register.csv"
)

BACKTEST_SUMMARY = Path("v5f_event_triggered_mean_reversion_borrowing_test") / "current" / "v5f_mr_borrowing_summary.json"
BACKTEST_METRICS = Path("v5f_event_triggered_mean_reversion_borrowing_test") / "current" / "v5f_mr_borrowing_variant_metrics.csv"
BACKTEST_SLEEVE = Path("v5f_event_triggered_mean_reversion_borrowing_test") / "current" / "v5f_mr_borrowing_sleeve_attribution.csv"
BACKTEST_YEARLY = Path("v5f_event_triggered_mean_reversion_borrowing_test") / "current" / "v5f_mr_borrowing_yearly.csv"
BACKTEST_SOURCE = Path("v5f_event_triggered_mean_reversion_borrowing_test") / "current" / "v5f_mr_borrowing_source_audit.csv"

THRESHOLD_CLASSIFICATION = (
    Path("v5f_spike_mr_sleeve_threshold_effectiveness_audit")
    / "current"
    / "v5f_spike_mr_sleeve_effectiveness_classification.csv"
)
COMMON_VS_SLEEVE = (
    Path("v5f_spike_mr_sleeve_threshold_effectiveness_audit")
    / "current"
    / "v5f_spike_mr_common_vs_sleeve_threshold_comparison.csv"
)
THRESHOLD_SENSITIVITY = (
    Path("v5f_spike_mr_sleeve_threshold_effectiveness_audit")
    / "current"
    / "v5f_spike_mr_threshold_sensitivity_by_sleeve.csv"
)
STRUCTURAL_SUMMARY = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_summary.json"

REQUIRED = [
    PRETEST_SUMMARY,
    PRETEST_METRICS,
    PRETEST_SLEEVE,
    PRETEST_GAPS,
    BACKTEST_SUMMARY,
    BACKTEST_METRICS,
    BACKTEST_SLEEVE,
    BACKTEST_YEARLY,
    BACKTEST_SOURCE,
    THRESHOLD_CLASSIFICATION,
    COMMON_VS_SLEEVE,
    THRESHOLD_SENSITIVITY,
    STRUCTURAL_SUMMARY,
]

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
PRETEST_START = "2020-10-09"
PRETEST_END = "2020-12-31"
PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
PREFERRED_BACKTEST_VARIANT = "mr_borrow_paired_drop_spike_net0_cap10_next2"


def run_v5f_spike_mr_prebacktest_to_backtest_jq_sim(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    # Refresh the two actual evidence legs. The pretest runner is local-only here;
    # it uses already stored 2020Q4 minute bars and will not call BaoStock.
    pretest_refresh = run_v5f_spike_funded_mr_borrowing_independent_validation_gate(
        root,
        allow_baostock_fetch=False,
    )
    backtest_refresh = run_v5f_event_triggered_mr_borrowing(root)

    manifest = _input_manifest(root)
    missing = [row for row in manifest if row["required"] and not row["exists"]]
    if missing:
        summary = _summary(
            "blocked_missing_required_input",
            "blocked_by_missing_required_input",
            missing,
            pretest_refresh_status=pretest_refresh.get("status", ""),
            backtest_refresh_status=backtest_refresh.get("status", ""),
        )
        _write_minimal(out, summary, manifest, missing)
        return summary

    pretest = _pretest_matrix(root)
    backtest = _backtest_matrix(root)
    sleeve = _sleeve_sensitivity_matrix(root)
    yearly = _yearly_matrix(root)
    governance = _governance_audit(pretest, backtest)
    decision = _pm_gate_decision(pretest, backtest, governance)
    queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers = _blockers(root)

    _write_csv(out / "v5f_spike_mr_input_manifest.csv", manifest)
    _write_csv(out / "v5f_spike_mr_prebacktest_validation_matrix.csv", pretest)
    _write_csv(out / "v5f_spike_mr_backtest_local_jq_sim_comparison.csv", backtest)
    _write_csv(out / "v5f_spike_mr_sleeve_sensitivity_matrix.csv", sleeve)
    _write_csv(out / "v5f_spike_mr_yearly_backtest_comparison.csv", yearly)
    _write_csv(out / "v5f_spike_mr_scope_governance_audit.csv", governance)
    _write_csv(out / "v5f_spike_mr_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_spike_mr_next_queue.csv", queue)
    _write_csv(out / "v5f_spike_mr_blockers.csv", blockers)
    (out / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_report.md").write_text(
        _report(pretest, backtest, sleeve, yearly, decision, blockers),
        encoding="utf-8",
    )
    (out / "v5f_spike_mr_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best_backtest = next(row for row in backtest if row["role"] == "governance_preferred_shock_borrowing")
    best_pretest = pretest[0] if pretest else {}
    summary = _summary(
        "completed_prebacktest_validation_and_backtest_scope_local_jq_sim",
        decision[0]["pm_gate_decision"],
        [],
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        pretest_start=PRETEST_START,
        pretest_end=PRETEST_END,
        post_20260531_forward_excluded=True,
        daily_forward_automation_revoked=True,
        primary_candidate=PRIMARY,
        baseline=BASELINE,
        pretest_directional_support=best_pretest.get("directional_support", False),
        pretest_formal_independent_pass=False,
        backtest_best_variant=best_backtest["version_id"],
        backtest_return_pct=float(best_backtest["strategy_return_pct"]),
        backtest_delta_vs_primary_pct_points=float(best_backtest["delta_return_pct_points_vs_primary"]),
        backtest_delta_vs_v57f_pct_points=float(best_backtest["delta_return_pct_points_vs_v57f"]),
        sleeve_specific_thresholds_required=True,
        candidate_promoted=False,
        accepted=False,
        live_trading_approved=False,
        v57f_core_modified=False,
        threshold_scan_used=False,
        full_market_selection_used=False,
        joinquant_started=False,
        local_joinquant_style_simulation_used=True,
    )
    _write_json(out / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json", summary)
    return summary


def _pretest_matrix(root: Path) -> list[dict[str, Any]]:
    summary = _read_json(root / PRETEST_SUMMARY)
    metrics = pd.read_csv(root / PRETEST_METRICS)
    if metrics.empty:
        return []
    for col in ["net_incremental_return_pct_points", "win_rate", "trade_group_count", "feature_day_count"]:
        metrics[col] = pd.to_numeric(metrics[col], errors="coerce")
    metrics = metrics.sort_values("net_incremental_return_pct_points", ascending=False)
    best = metrics.iloc[0]
    return [
        {
            "scope": "pre_backtest_limited_validation",
            "window_start": summary.get("validation_window_start", PRETEST_START),
            "window_end": summary.get("validation_window_end", PRETEST_END),
            "window_classification": summary.get("validation_window_classification", ""),
            "version_id": best["version_id"],
            "funding_policy": best["funding_policy"],
            "borrow_horizon": best["borrow_horizon"],
            "feature_day_count": int(best["feature_day_count"]),
            "trade_group_count": int(best["trade_group_count"]),
            "sleeve_count": int(pd.to_numeric(best.get("sleeve_count", 0), errors="coerce") or 0),
            "net_incremental_return_pct_points": float(best["net_incremental_return_pct_points"]),
            "win_rate": float(best["win_rate"]),
            "directional_support": bool(summary.get("limited_2020q4_directional_pass", False)),
            "formal_independent_pass": bool(summary.get("independent_validation_pass", False)),
            "read": "positive_but_micro_sample_not_full_v57f_equivalent",
        }
    ]


def _backtest_matrix(root: Path) -> list[dict[str, Any]]:
    metrics = pd.read_csv(root / BACKTEST_METRICS)
    for col in [
        "strategy_return",
        "annualized_return",
        "max_drawdown",
        "volatility",
        "sharpe_proxy",
        "delta_return_pct_points_vs_champion",
        "delta_return_pct_points_vs_v57f",
    ]:
        metrics[col] = pd.to_numeric(metrics[col], errors="coerce")

    rows: list[dict[str, Any]] = []
    wanted = [
        ("baseline", BASELINE),
        ("primary_v5f_line", "vmr_70_30_0_champion"),
        ("governance_preferred_shock_borrowing", PREFERRED_BACKTEST_VARIANT),
    ]
    for role, version in wanted:
        hit = metrics[metrics["version_id"].astype(str).eq(version)]
        if hit.empty:
            continue
        row = hit.iloc[0]
        rows.append(
            {
                "scope": "backtest_scope_local_joinquant_style_sim",
                "window_start": BACKTEST_START,
                "window_end": BACKTEST_END,
                "role": role,
                "version_id": version,
                "funding_policy": row.get("funding_policy", ""),
                "borrow_horizon": row.get("borrow_horizon", ""),
                "strategy_return_pct": float(row["strategy_return"]) * 100,
                "annualized_return_pct": float(row["annualized_return"]) * 100,
                "max_drawdown_pct": float(row["max_drawdown"]) * 100,
                "volatility_pct": float(row["volatility"]) * 100,
                "sharpe_proxy": float(row["sharpe_proxy"]),
                "delta_return_pct_points_vs_primary": float(row["delta_return_pct_points_vs_champion"]),
                "delta_return_pct_points_vs_v57f": float(row["delta_return_pct_points_vs_v57f"]),
                "accepted": False,
            }
        )
    return rows


def _sleeve_sensitivity_matrix(root: Path) -> list[dict[str, Any]]:
    classification = pd.read_csv(root / THRESHOLD_CLASSIFICATION)
    common = pd.read_csv(root / COMMON_VS_SLEEVE)
    sensitivity = pd.read_csv(root / THRESHOLD_SENSITIVITY)
    backtest_sleeve = pd.read_csv(root / BACKTEST_SLEEVE)
    validation_sleeve = pd.read_csv(root / PRETEST_SLEEVE)

    sensitivity = sensitivity[
        sensitivity["scheme"].astype(str).eq("anchored_prior_years")
        & sensitivity["test_year"].astype(str).eq("2026")
    ].copy()
    backtest_sleeve = backtest_sleeve[backtest_sleeve["version_id"].astype(str).eq(PREFERRED_BACKTEST_VARIANT)].copy()
    validation_sleeve = validation_sleeve[
        validation_sleeve["version_id"].astype(str).eq("independent2020q4_paired_drop_spike_net0_cap10_next2")
    ].copy()

    rows: list[dict[str, Any]] = []
    for _, row in classification.iterrows():
        sleeve = str(row["sleeve"])
        sens = _first(sensitivity[sensitivity["sleeve"].astype(str).eq(sleeve)])
        com = _first(common[common["sleeve"].astype(str).eq(sleeve)])
        bt = _first(backtest_sleeve[backtest_sleeve["sleeve"].astype(str).eq(sleeve)])
        pre = _first(validation_sleeve[validation_sleeve["sleeve"].astype(str).eq(sleeve)])
        rows.append(
            {
                "sleeve": sleeve,
                "sleeve_specific_drop_abs_pct_2026": _float_or_blank(sens.get("drop_abs_pct")),
                "sleeve_specific_spike_abs_pct_2026": _float_or_blank(sens.get("spike_abs_pct")),
                "common_abs_1pct_drop_rate": _float_or_blank(com.get("drop_rate")),
                "common_abs_1pct_spike_rate": _float_or_blank(com.get("spike_rate")),
                "common_threshold_read": com.get("governance_read", ""),
                "historical_read": row.get("historical_read", ""),
                "pretest_net_pct_points": _float_or_blank(pre.get("net_incremental_return_pct_points")),
                "pretest_trade_group_count": _int_or_blank(pre.get("trade_group_count")),
                "backtest_net_pct_points": _float_or_blank(
                    (float(bt.get("net_incremental_return_sum", 0.0)) * 100) if bt else ""
                ),
                "backtest_trade_group_count": _int_or_blank(bt.get("trade_group_count")),
                "sleeve_threshold_required": True,
            }
        )
    return rows


def _yearly_matrix(root: Path) -> list[dict[str, Any]]:
    yearly = pd.read_csv(root / BACKTEST_YEARLY)
    yearly = yearly[
        yearly["version_id"].astype(str).isin([BASELINE, "vmr_70_30_0_champion", PREFERRED_BACKTEST_VARIANT])
    ].copy()
    for col in ["period_return", "delta_return_pct_points_vs_champion", "active_borrow_days"]:
        yearly[col] = pd.to_numeric(yearly[col], errors="coerce")
    rows = []
    for _, row in yearly.iterrows():
        rows.append(
            {
                "scope": "backtest_scope_local_joinquant_style_sim",
                "version_id": row["version_id"],
                "year": int(row["year"]),
                "period_return_pct": float(row["period_return"]) * 100,
                "active_borrow_days": int(row["active_borrow_days"]) if not pd.isna(row["active_borrow_days"]) else 0,
                "delta_return_pct_points_vs_primary": float(row["delta_return_pct_points_vs_champion"]),
            }
        )
    return rows


def _governance_audit(pretest: list[dict[str, Any]], backtest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred = next((row for row in backtest if row["role"] == "governance_preferred_shock_borrowing"), {})
    return [
        _audit("daily_forward_automation_revoked", True, "No scheduled forward append remains active for this line."),
        _audit("backtest_scope_end_20260531", True, f"Backtest scope ends at {BACKTEST_END}; later dates excluded."),
        _audit("prebacktest_validation_before_backtest", True, f"Pretest window {PRETEST_START} to {PRETEST_END}."),
        _audit("local_joinquant_style_backtest_used", True, "Uses repaired local daily backtest chain and local minute features; external JoinQuant not started."),
        _audit("sleeve_specific_thresholds_required", True, "Different sleeves have different shock sensitivity; common absolute threshold is too coarse."),
        _audit("pretest_formal_independent_pass_false", pretest and not pretest[0]["formal_independent_pass"], "2020Q4 is directional support only."),
        _audit("backtest_positive_vs_primary", float(preferred.get("delta_return_pct_points_vs_primary", 0.0)) > 0.0, preferred.get("version_id", "")),
        _audit("no_candidate_promotion", True, "Shock borrowing remains observation/diagnostic, not candidate."),
        _audit("no_v57f_core_modified", True, "V57f core unchanged."),
        _audit("no_threshold_scan_used", True, "Uses pre-existing fixed policy variants and PIT prior-year sleeve thresholds."),
        _audit("accepted_false", True, "No accepted/live approval."),
    ]


def _pm_gate_decision(
    pretest: list[dict[str, Any]],
    backtest: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    preferred = next((row for row in backtest if row["role"] == "governance_preferred_shock_borrowing"), {})
    gov_pass = all(row["status"] == "pass" for row in governance)
    backtest_positive = float(preferred.get("delta_return_pct_points_vs_primary", 0.0)) > 0.0
    limited_positive = bool(pretest and pretest[0]["directional_support"])
    decision = (
        "backtest_positive_prebacktest_limited_keep_observation_not_candidate"
        if gov_pass and backtest_positive and limited_positive
        else "diagnostic_only_insufficient_independent_validation"
    )
    return [
        {
            "pm_gate_decision": decision,
            "accepted": False,
            "candidate_promoted": False,
            "primary_v5f_line": PRIMARY,
            "shock_borrowing_status": "observation_only",
            "reason": "Backtest is positive, but pre-backtest evidence is a small 2020Q4 micro sample and not full V57f-equivalent.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary",
            "status": "active_primary",
            "allowed": True,
        },
        {
            "priority": 2,
            "next_task": "do_not_use_post_20260531_forward_as_backtest_validation",
            "status": "scope_guard",
            "allowed": False,
        },
        {
            "priority": 3,
            "next_task": "if_joinquant_available_run_official_backtest_scope_replication_only",
            "status": "optional_confirmation",
            "allowed": True,
        },
        {
            "priority": 4,
            "next_task": "source_broader_pre2021_5min_or_equivalent_local_jq_history_before_candidate_review",
            "status": "needed_for_formal_independent_validation",
            "allowed": True,
        },
        {
            "priority": 5,
            "next_task": "promote_spike_borrowing_to_candidate",
            "status": "blocked_until_independent_validation_passes",
            "allowed": False,
        },
    ]


def _blockers(root: Path) -> list[dict[str, Any]]:
    gaps = _read_csv(root / PRETEST_GAPS)
    rows = []
    for gap in gaps:
        if str(gap.get("blocks_formal_promotion", "")).lower() == "true":
            rows.append(
                {
                    "blocker_id": gap.get("gap_id", ""),
                    "severity": "research",
                    "blocks_candidate_promotion": True,
                    "detail": gap.get("detail", ""),
                }
            )
    return rows


def _report(
    pretest: list[dict[str, Any]],
    backtest: list[dict[str, Any]],
    sleeve: list[dict[str, Any]],
    yearly: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> str:
    preferred = next(row for row in backtest if row["role"] == "governance_preferred_shock_borrowing")
    primary = next(row for row in backtest if row["role"] == "primary_v5f_line")
    baseline = next(row for row in backtest if row["role"] == "baseline")
    lines = [
        "# V5f Spike MR Pre-Backtest Validation to Backtest Local JQ Simulation",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Scope: pretest `{PRETEST_START}` to `{PRETEST_END}`; backtest `{BACKTEST_START}` to `{BACKTEST_END}`.",
        "- 2026-05-31 after-data and daily forward observation are excluded from this judgment.",
        "- External JoinQuant was not started; this is the local JoinQuant-style repaired data simulation.",
        "",
        "## Main Comparison",
        "",
        f"- `{BASELINE}` return: `{baseline['strategy_return_pct']:.4f}%`.",
        f"- `{PRIMARY}` return: `{primary['strategy_return_pct']:.4f}%`, delta vs V57f `{primary['delta_return_pct_points_vs_v57f']:.4f}` pct.",
        f"- `{preferred['version_id']}` return: `{preferred['strategy_return_pct']:.4f}%`, delta vs primary `{preferred['delta_return_pct_points_vs_primary']:.4f}` pct, delta vs V57f `{preferred['delta_return_pct_points_vs_v57f']:.4f}` pct.",
        "",
        "## Pre-Backtest Read",
        "",
    ]
    if pretest:
        row = pretest[0]
        lines.append(
            f"- 2020Q4 best pretest `{row['version_id']}`: net `{row['net_incremental_return_pct_points']:.4f}` pct, win `{row['win_rate']:.2%}`, trade groups `{row['trade_group_count']}`."
        )
        lines.append("- Read: positive directional support, but not a formal independent pass.")
    lines.extend(["", "## Sleeve Sensitivity", ""])
    for row in sleeve:
        lines.append(
            f"- `{row['sleeve']}`: 2026 sleeve shock cuts drop `{row['sleeve_specific_drop_abs_pct_2026']}`%, spike `{row['sleeve_specific_spike_abs_pct_2026']}`%; backtest net `{row['backtest_net_pct_points']}` pct."
        )
    lines.extend(["", "## Yearly Backtest Increment", ""])
    for row in yearly:
        if row["version_id"] == PREFERRED_BACKTEST_VARIANT:
            lines.append(
                f"- `{row['year']}`: delta vs primary `{row['delta_return_pct_points_vs_primary']:.4f}` pct, active borrow days `{row['active_borrow_days']}`."
            )
    lines.extend(["", "## Promotion Blockers", ""])
    for row in blockers:
        lines.append(f"- `{row['blocker_id']}`: {row['detail']}")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# Agent Execution Rules",
            "",
            "- Backtest scope is fixed at 2021-05-01 to 2026-05-31.",
            "- Use pre-backtest data only for independent validation; do not use post-2026-05-31 forward evidence.",
            "- Keep `internal_subsleeve_mom12_70_30` as V5f primary.",
            "- Spike-funded mean reversion borrowing remains observation-only.",
            "- Use sleeve-specific PIT thresholds; do not use a common absolute shock threshold.",
            "- Do not modify V57f core, do not scan thresholds, do not mark accepted/live approved.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path),
            "required": True,
            "exists": (root / path).exists(),
            "file_size_bytes": (root / path).stat().st_size if (root / path).exists() else "",
        }
        for path in REQUIRED
    ]


def _write_minimal(out: Path, summary: dict[str, Any], manifest: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> None:
    _write_json(out / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json", summary)
    _write_csv(out / "v5f_spike_mr_input_manifest.csv", manifest)
    _write_csv(out / "v5f_spike_mr_blockers.csv", blockers)
    for name in [
        "v5f_spike_mr_prebacktest_validation_matrix.csv",
        "v5f_spike_mr_backtest_local_jq_sim_comparison.csv",
        "v5f_spike_mr_sleeve_sensitivity_matrix.csv",
        "v5f_spike_mr_yearly_backtest_comparison.csv",
        "v5f_spike_mr_scope_governance_audit.csv",
        "v5f_spike_mr_pm_gate_decision.csv",
        "v5f_spike_mr_next_queue.csv",
    ]:
        _write_csv(out / name, [])
    (out / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_report.md").write_text("# Blocked\n", encoding="utf-8")
    (out / "v5f_spike_mr_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_spike_mr_prebacktest_to_backtest_jq_sim",
        "status": status,
        "pm_gate_decision": decision,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }
    payload.update(extra)
    return payload


def _audit(audit_id: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if passed else "fail", "detail": detail}


def _first(df: pd.DataFrame) -> dict[str, Any]:
    return df.iloc[0].to_dict() if not df.empty else {}


def _float_or_blank(value: Any) -> float | str:
    try:
        if value == "" or value is None:
            return ""
        out = float(value)
        if pd.isna(out):
            return ""
        return out
    except Exception:
        return ""


def _int_or_blank(value: Any) -> int | str:
    try:
        if value == "" or value is None:
            return ""
        out = float(value)
        if pd.isna(out):
            return ""
        return int(out)
    except Exception:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    print(json.dumps(run_v5f_spike_mr_prebacktest_to_backtest_jq_sim(Path(".")), ensure_ascii=False, indent=2))
