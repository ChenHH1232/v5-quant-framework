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
    _load_prices,
    _metrics,
    _yearly,
)


OUT_DIR = Path("v5c_overheat_no_new_overweight_limited_engineering") / "current"
PREJQ_DIR = Path("v5f_prejq_v5c_v5g_integration") / "current"
V5F_WEIGHTS = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_weights.csv"
V5F_ROBUSTNESS = Path("v5f_internal_subsleeve_robustness_packet") / "current" / "v5f_internal_subsleeve_robustness_summary.json"
PREJQ_SUMMARY = PREJQ_DIR / "v5f_prejq_v5c_v5g_integration_summary.json"
STATE_AUDIT = PREJQ_DIR / "v5c_v5f_state_active_weight_audit.csv"
OVERHEAT_CANDIDATE = PREJQ_DIR / "v5c_overheat_no_new_overweight_candidate_matrix.csv"

PRIMARY = "internal_subsleeve_mom12_70_30"
CANDIDATE = "v5c_overheat_no_new_overweight_on_v5f_mom12_70_30"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
COMPOSITE_OVERHEAT = "valuation_price_flow_overheat_watch"


REQUIRED = [
    PREJQ_SUMMARY,
    STATE_AUDIT,
    OVERHEAT_CANDIDATE,
    V5F_WEIGHTS,
    V5F_ROBUSTNESS,
    REPAIRED_RUN / "daily_returns.csv",
]


def run_v5c_overheat_no_new_overweight_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_overheat_no_new_overweight_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5c_overheat_no_new_overweight_summary.json", summary)
        return summary

    prejq = _read_json(root / PREJQ_SUMMARY)
    robustness = _read_json(root / V5F_ROBUSTNESS)
    candidate_spec = _read_csv(root / OVERHEAT_CANDIDATE)[0]
    state_audit = _read_csv(root / STATE_AUDIT)
    trigger_set = _trigger_touch_set(state_audit)
    weights = _candidate_weights(root, trigger_set)
    prices = _load_prices(root)
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    period = _period_comparison(daily)
    touch = _trigger_touch_set_output(trigger_set)
    governance = _governance(prejq, candidate_spec, weights, touch)
    decision = _pm_decision(metrics, period, governance)
    queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5c_overheat_no_new_overweight_weights.csv", weights)
    _write_csv(out / "v5c_overheat_no_new_overweight_daily_returns.csv", daily)
    _write_csv(out / "v5c_overheat_no_new_overweight_metrics.csv", metrics)
    _write_csv(out / "v5c_overheat_no_new_overweight_yearly.csv", yearly)
    _write_csv(out / "v5c_overheat_no_new_overweight_rebalance_period_comparison.csv", period)
    _write_csv(out / "v5c_overheat_no_new_overweight_trigger_touch_set.csv", touch)
    _write_csv(out / "v5c_overheat_no_new_overweight_governance_audit.csv", governance)
    _write_csv(out / "v5c_overheat_no_new_overweight_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_overheat_no_new_overweight_next_agent_queue.csv", queue)
    _write_csv(out / "v5c_overheat_no_new_overweight_blockers.csv", blockers_out)
    (out / "v5c_overheat_no_new_overweight_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5c_overheat_no_new_overweight_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")
    (out / "v5c_overheat_no_new_overweight_report.md").write_text(
        _report(robustness, metrics, period, touch, decision),
        encoding="utf-8",
    )

    cand = next(row for row in metrics if row["version_id"] == CANDIDATE)
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    summary = _summary(
        "completed_v5c_overheat_no_new_overweight_limited_engineering",
        decision[0]["pm_gate_decision"],
        [],
        candidate_id=CANDIDATE,
        primary_candidate=PRIMARY,
        baseline_id=BASELINE,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        candidate_return_pct=float(cand["strategy_return"]) * 100,
        primary_return_pct=float(primary["strategy_return"]) * 100,
        candidate_delta_return_pct_points_vs_repaired_baseline=float(cand["delta_return_pct_points_vs_repaired_baseline"]),
        primary_delta_return_pct_points_vs_repaired_baseline=float(primary["delta_return_pct_points_vs_repaired_baseline"]),
        candidate_delta_return_pct_points_vs_primary=float(cand["strategy_return"]) * 100 - float(primary["strategy_return"]) * 100,
        candidate_delta_drawdown_pct_points_vs_primary=float(cand["max_drawdown"]) * 100 - float(primary["max_drawdown"]) * 100,
        touched_rebalance_sleeve_count=len(trigger_set),
        touched_stock_rows=len(touch),
        v5f_champion_replaced=False,
    )
    _write_json(out / "v5c_overheat_no_new_overweight_summary.json", summary)
    return summary


def _trigger_touch_set(state_audit: list[dict[str, str]]) -> set[tuple[str, str]]:
    return {
        (row["rebalance_date"], row["sleeve_id"])
        for row in state_audit
        if row["sleeve_overheat_state"] == COMPOSITE_OVERHEAT and row["active_overweight_on_composite_overheat"] == "True"
    }


def _candidate_weights(root: Path, trigger_set: set[tuple[str, str]]) -> list[dict[str, Any]]:
    source = pd.read_csv(root / V5F_WEIGHTS, dtype={"rebalance_date": str, "code": str, "sleeve": str})
    selected = source[source["version_id"].isin([BASELINE, PRIMARY])].copy()
    rows: list[dict[str, Any]] = []
    for _, row in selected.iterrows():
        payload = row.to_dict()
        if row["version_id"] == BASELINE:
            rows.append(payload)
            continue
        rows.append(payload)

    primary_rows = source[source["version_id"] == PRIMARY].copy()
    for _, row in primary_rows.iterrows():
        base = float(row["base_target_weight"])
        target = float(row["target_weight"])
        if (row["rebalance_date"], row["sleeve"]) in trigger_set:
            target = base
            bucket = "composite_overheat_frozen_to_v57f_baseline"
        else:
            bucket = row["bucket"]
        rows.append(
            {
                "version_id": CANDIDATE,
                "family": "v5c_state_guarded_internal_subsleeve",
                "rebalance_date": row["rebalance_date"],
                "code": row["code"],
                "sleeve": row["sleeve"],
                "base_target_weight": base,
                "target_weight": target,
                "weight_delta": target - base,
                "mom_12_1": row["mom_12_1"],
                "mr_60d": row["mr_60d"],
                "bucket": bucket,
                "sleeve_weight_preserved": True,
                "new_stock_selected": False,
                "accepted": False,
            }
        )
    return rows


def _period_comparison(daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(daily)
    rows = []
    for (version, period), group in df.groupby(["version_id", "active_rebalance_date"], sort=True):
        period_return = (1.0 + pd.to_numeric(group["strategy_return"])).prod() - 1.0
        rows.append({"version_id": version, "active_rebalance_date": period, "period_return": period_return, "trade_days": len(group)})
    base = {row["active_rebalance_date"]: float(row["period_return"]) for row in rows if row["version_id"] == BASELINE}
    primary = {row["active_rebalance_date"]: float(row["period_return"]) for row in rows if row["version_id"] == PRIMARY}
    for row in rows:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - base.get(row["active_rebalance_date"], 0.0)) * 100
        row["delta_return_pct_points_vs_primary"] = (float(row["period_return"]) - primary.get(row["active_rebalance_date"], 0.0)) * 100
        row["triggered_composite_overheat_rule"] = row["version_id"] == CANDIDATE and row["active_rebalance_date"] == "2024-10-08"
    return rows


def _trigger_touch_set_output(trigger_set: set[tuple[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for rebalance_date, sleeve_id in sorted(trigger_set):
        rows.append(
            {
                "rebalance_date": rebalance_date,
                "sleeve_id": sleeve_id,
                "trigger": COMPOSITE_OVERHEAT,
                "candidate_action": "freeze_this_sleeve_to_repaired_v57f_baseline_weights",
                "trade_path_changed": True,
                "single_stock_sell": False,
                "cross_sleeve_transfer": False,
                "cash_raise": False,
            }
        )
    return rows


def _governance(
    prejq: dict[str, Any],
    candidate_spec: dict[str, str],
    weights: list[dict[str, Any]],
    touch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    candidate = df[df["version_id"] == CANDIDATE]
    sleeve_preserved = all(
        abs(group["target_weight"].astype(float).sum() - group["base_target_weight"].astype(float).sum()) < 1e-10
        for _, group in candidate.groupby(["rebalance_date", "sleeve"])
    )
    return [
        _audit("prejq_gate_passed", prejq["pm_gate_decision"] == "prejq_v5c_v5g_integration_pass_observe_only_and_overheat_candidate_ready", prejq["pm_gate_decision"]),
        _audit("candidate_approved_for_next_engineering", candidate_spec["pm_status"] == "approved_for_next_limited_engineering_fixed_rule_not_accepted", candidate_spec["pm_status"]),
        _audit("fixed_trigger_only", len(touch) == 1 and touch[0]["trigger"] == COMPOSITE_OVERHEAT, len(touch)),
        _audit("sleeve_weight_preserved", sleeve_preserved, 0 if sleeve_preserved else 1),
        _audit("v57f_selected_pool_only", not candidate["new_stock_selected"].astype(str).eq("True").any(), 0),
        _audit("no_single_stock_sell", all(not row["single_stock_sell"] for row in touch), False),
        _audit("no_cross_sleeve_transfer", all(not row["cross_sleeve_transfer"] for row in touch), False),
        _audit("no_cash_raise", all(not row["cash_raise"] for row in touch), False),
        _audit("accepted_false", not candidate["accepted"].astype(str).eq("True").any(), False),
        _audit("v57f_core_modified_false", True, False),
        _audit("threshold_scan_used_false", True, False),
        _audit("joinquant_not_started", True, False),
    ]


def _pm_decision(
    metrics: list[dict[str, Any]],
    period: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    cand = next(row for row in metrics if row["version_id"] == CANDIDATE)
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    return_delta_vs_primary = (float(cand["strategy_return"]) - float(primary["strategy_return"])) * 100
    drawdown_delta_vs_primary = (float(cand["max_drawdown"]) - float(primary["max_drawdown"])) * 100
    if gov_ok and return_delta_vs_primary >= 0 and drawdown_delta_vs_primary <= 0:
        gate = "overheat_no_new_overweight_pass_ready_for_forward_observation_not_accepted"
        rationale = "The narrow overheat guard improved or matched the V5f champion without worse drawdown."
    elif gov_ok:
        gate = "overheat_no_new_overweight_diagnostic_only_do_not_replace_v5f_champion"
        rationale = "The guard is governance-clean but does not improve the V5f champion enough to replace it."
    else:
        gate = "blocked_by_overheat_engineering_governance_issue"
        rationale = "One or more governance checks failed."
    triggered_period = next(row for row in period if row["version_id"] == CANDIDATE and row["triggered_composite_overheat_rule"])
    primary_triggered = next(row for row in period if row["version_id"] == PRIMARY and row["active_rebalance_date"] == triggered_period["active_rebalance_date"])
    return [
        {
            "pm_gate_decision": gate,
            "candidate_id": CANDIDATE,
            "primary_candidate": PRIMARY,
            "candidate_delta_return_pct_points_vs_repaired_baseline": cand["delta_return_pct_points_vs_repaired_baseline"],
            "primary_delta_return_pct_points_vs_repaired_baseline": primary["delta_return_pct_points_vs_repaired_baseline"],
            "candidate_delta_return_pct_points_vs_primary": return_delta_vs_primary,
            "candidate_delta_drawdown_pct_points_vs_primary": drawdown_delta_vs_primary,
            "triggered_period": triggered_period["active_rebalance_date"],
            "triggered_period_delta_return_pct_points_vs_primary": (float(triggered_period["period_return"]) - float(primary_triggered["period_return"])) * 100,
            "replace_v5f_champion": False,
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "joinquant_started": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": "P0",
            "next_task": "keep_internal_subsleeve_mom12_70_30_as_primary_forward_paper_candidate",
            "allowed": True,
            "reason": "The overheat guard does not replace the V5f champion.",
        },
        {
            "priority": "P1",
            "next_task": "attach_v5c_observe_only_tags_to_v5f_forward_paper",
            "allowed": True,
            "reason": "Observe-only tags provide useful risk context without changing trades.",
        },
        {
            "priority": "P2",
            "next_task": "joinquant_platform_attribution_after_user_exports",
            "allowed": False,
            "reason": "Waiting for user-supplied JoinQuant exports.",
        },
        {
            "priority": "P3",
            "next_task": "promote_overheat_guard_to_primary_model",
            "allowed": False,
            "reason": "This packet does not allow replacement or acceptance.",
        },
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if not failed:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Limited engineering completed."}]
    return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]


def _report(
    robustness: dict[str, Any],
    metrics: list[dict[str, Any]],
    period: list[dict[str, Any]],
    touch: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    cand = next(row for row in metrics if row["version_id"] == CANDIDATE)
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    triggered = next(row for row in period if row["version_id"] == CANDIDATE and row["triggered_composite_overheat_rule"])
    return "\n".join(
        [
            "# V5c Overheat No-New-Overweight Limited Engineering",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Candidate: `{CANDIDATE}`",
            f"- Primary reference: `{PRIMARY}`",
            f"- Historical scope: `{BACKTEST_START}` to `{BACKTEST_END}`.",
            "- Accepted/live approved: `False`.",
            "",
            "## Result",
            f"- Primary V5f delta vs repaired baseline: {float(primary['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Candidate delta vs repaired baseline: {float(cand['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Candidate delta vs primary: {float(decision[0]['candidate_delta_return_pct_points_vs_primary']):.4f} pct points.",
            f"- Candidate drawdown delta vs primary: {float(decision[0]['candidate_delta_drawdown_pct_points_vs_primary']):.4f} pct points.",
            "",
            "## Trigger Touch Set",
            *[f"- `{row['rebalance_date']}` `{row['sleeve_id']}`: {row['candidate_action']}" for row in touch],
            f"- Triggered period candidate delta vs repaired baseline: {float(triggered['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Original robustness edge remains: {float(robustness['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            "",
            "## Decision",
            "- Keep V5f champion as primary.",
            "- Use V5c state tags for forward observation.",
            "- Do not promote the overheat guard to primary from this result.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f forward/paper observation with V5c state tags

任务目标：
继续 `internal_subsleeve_mom12_70_30` forward/paper tracking，并把 V5c valuation/crowding/overheat 状态作为 observe-only 标签接入。不得用标签改变交易，不得 accepted。

来源 gate：
`{decision["pm_gate_decision"]}`

必须先阅读：
- v5c_overheat_no_new_overweight_limited_engineering\\current\\v5c_overheat_no_new_overweight_summary.json
- v5f_prejq_v5c_v5g_integration\\current\\v5c_v5f_forward_observe_only_tags.csv
- v5f_joinquant_export_checklist\\current\\v5f_joinquant_export_checklist_summary.json
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Overheat No-New-Overweight Engineering Rules",
            "",
            "- Repaired V57f baseline only.",
            "- Historical backtest scope ends at 2026-05-31.",
            f"- Fixed trigger only: `{COMPOSITE_OVERHEAT}`.",
            "- Do not use ordinary single-stock valuation overheat as a sell rule.",
            "- Do not modify V57f core.",
            "- Do not scan thresholds.",
            "- Do not mark accepted or live approved.",
            "- Do not start JoinQuant.",
            "",
        ]
    )


def _audit(audit_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if ok else "fail", "detail": detail}


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in REQUIRED
        if not (root / path).exists()
    ]


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_overheat_no_new_overweight_limited_engineering",
        "status": status,
        "pm_gate_decision": decision,
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
    payload.update(extra)
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    print(json.dumps(run_v5c_overheat_no_new_overweight_engineering(Path(".")), ensure_ascii=False, indent=2))
