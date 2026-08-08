from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_momentum_weight_tilt_pm_quant_review") / "current"
SPEC_DIR = Path("v5f_momentum_weight_tilt_quant_spec") / "current"
ENG_DIR = Path("v5f_momentum_weight_tilt_limited_engineering") / "current"
HISTORICAL_CLOSEOUT = Path("v5e_historical_closeout_governance_packet") / "current" / "v5e_historical_closeout_summary.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_momentum_weight_tilt_pm_quant_review(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_momentum_weight_tilt_pm_quant_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_momentum_weight_tilt_pm_quant_summary.json", summary)
        return summary

    spec_summary = _read_json(root / SPEC_DIR / "v5f_momentum_weight_tilt_summary.json")
    eng_summary = _read_json(root / ENG_DIR / "v5f_momentum_weight_tilt_summary.json")
    metrics = _read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_metrics.csv")
    governance = _read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_governance_audit.csv")
    pm_gate = _read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_pm_gate_decision.csv")[0]
    attribution = _read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_rebalance_attribution.csv")

    variant_review = _variant_review(metrics)
    candidate_checks = _candidate_checks(eng_summary, governance, pm_gate, variant_review)
    risk_benefit = _risk_benefit_matrix(variant_review)
    attribution_review = _attribution_review(attribution)
    decision = _pm_decision(candidate_checks, variant_review)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(candidate_checks)

    _write_csv(out / "v5f_momentum_weight_tilt_variant_review.csv", variant_review)
    _write_csv(out / "v5f_momentum_weight_tilt_candidate_checks.csv", candidate_checks)
    _write_csv(out / "v5f_momentum_weight_tilt_risk_benefit_matrix.csv", risk_benefit)
    _write_csv(out / "v5f_momentum_weight_tilt_attribution_review.csv", attribution_review)
    _write_csv(out / "v5f_momentum_weight_tilt_governance_review.csv", _governance_review(governance, spec_summary, eng_summary))
    _write_csv(out / "v5f_momentum_weight_tilt_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_momentum_weight_tilt_next_queue.csv", next_queue)
    _write_csv(out / "v5f_momentum_weight_tilt_pm_quant_blockers.csv", blockers_out)
    (out / "v5f_momentum_weight_tilt_report.md").write_text(
        _report(variant_review, candidate_checks, risk_benefit, decision),
        encoding="utf-8",
    )
    (out / "v5f_momentum_weight_tilt_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5f_momentum_weight_tilt_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    primary = next(row for row in variant_review if row["version_id"] == "mom_12_1_sleeve_tilt_10pct")
    summary = _summary(
        "completed_v5f_momentum_weight_tilt_pm_quant_review",
        decision[0]["pm_gate_decision"],
        [],
        primary_delta_return_pct_points=float(primary["delta_return_pct_points_vs_baseline_proxy"]),
        primary_delta_max_drawdown_pct_points=float(primary["delta_max_drawdown_pct_points_vs_baseline_proxy"]),
        stress_delta_return_pct_points=float(next(row for row in variant_review if row["version_id"] == "mom_9_1_sleeve_tilt_10pct")["delta_return_pct_points_vs_baseline_proxy"]),
    )
    _write_json(out / "v5f_momentum_weight_tilt_pm_quant_summary.json", summary)
    return summary


def _variant_review(metrics: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in metrics:
        version = row["version_id"]
        if version == "v57f_repaired_baseline_proxy":
            role = "baseline_proxy"
        elif version == "mom_12_1_sleeve_tilt_10pct":
            role = "primary_pre_registered_candidate"
        else:
            role = "stress_reference_not_selection"
        rows.append(
            {
                "version_id": version,
                "role": role,
                "strategy_return": row["strategy_return"],
                "annualized_return": row["annualized_return"],
                "max_drawdown": row["max_drawdown"],
                "volatility": row["volatility"],
                "sharpe_proxy": row["sharpe_proxy"],
                "delta_return_pct_points_vs_baseline_proxy": row["delta_return_pct_points_vs_baseline_proxy"],
                "delta_max_drawdown_pct_points_vs_baseline_proxy": row["delta_max_drawdown_pct_points_vs_baseline_proxy"],
                "delta_turnover_proxy_vs_baseline": row["delta_turnover_proxy_vs_baseline"],
                "accepted": False,
                "review_status": "review_candidate_not_accepted" if role == "primary_pre_registered_candidate" else role,
            }
        )
    return rows


def _candidate_checks(
    eng_summary: dict[str, Any],
    governance: list[dict[str, str]],
    pm_gate: dict[str, str],
    variant_review: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    primary = next(row for row in variant_review if row["version_id"] == "mom_12_1_sleeve_tilt_10pct")
    stress = next(row for row in variant_review if row["version_id"] == "mom_9_1_sleeve_tilt_10pct")
    governance_ok = all(row["status"] == "pass" and int(float(row["violation_count"])) == 0 for row in governance)
    return [
        {"check_id": "engineering_gate", "pass": pm_gate["pm_gate_decision"] == "admit_momentum_weight_tilt_to_pm_quant_review_not_accepted", "detail": pm_gate["pm_gate_decision"]},
        {"check_id": "primary_delta_return_positive", "pass": float(primary["delta_return_pct_points_vs_baseline_proxy"]) > 0.0, "detail": primary["delta_return_pct_points_vs_baseline_proxy"]},
        {"check_id": "primary_drawdown_not_worse", "pass": float(primary["delta_max_drawdown_pct_points_vs_baseline_proxy"]) <= 0.0, "detail": primary["delta_max_drawdown_pct_points_vs_baseline_proxy"]},
        {"check_id": "stress_reference_positive", "pass": float(stress["delta_return_pct_points_vs_baseline_proxy"]) > 0.0, "detail": stress["delta_return_pct_points_vs_baseline_proxy"]},
        {"check_id": "stress_reference_drawdown_note", "pass": True, "detail": f"stress drawdown delta {stress['delta_max_drawdown_pct_points_vs_baseline_proxy']} pct points; review note, not promotion basis"},
        {"check_id": "governance_clean", "pass": governance_ok, "detail": "selected pool only, sleeve preserved, rebalance day only"},
        {"check_id": "not_accepted_or_live", "pass": not eng_summary.get("accepted") and not eng_summary.get("live_trading_approved"), "detail": "not accepted and not live approved"},
        {"check_id": "no_threshold_scan", "pass": not eng_summary.get("threshold_scan_used"), "detail": "primary 12-1 fixed; 9-1 stress/reference only"},
        {"check_id": "no_new_buy_signal", "pass": not eng_summary.get("new_buy_signal_used"), "detail": "only V57f selected stocks receive within-sleeve weight tilt"},
    ]


def _risk_benefit_matrix(variant_review: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = next(row for row in variant_review if row["version_id"] == "mom_12_1_sleeve_tilt_10pct")
    stress = next(row for row in variant_review if row["version_id"] == "mom_9_1_sleeve_tilt_10pct")
    return [
        {
            "topic": "return_edge",
            "benefit": f"{float(primary['delta_return_pct_points_vs_baseline_proxy']):.4f} pct points vs baseline proxy",
            "risk": "historical backtest window only; needs forward/paper confirmation",
            "pm_read": "positive_but_not_accepted",
        },
        {
            "topic": "drawdown",
            "benefit": f"{float(primary['delta_max_drawdown_pct_points_vs_baseline_proxy']):.4f} pct point max drawdown delta",
            "risk": "drawdown change is tiny and should not be oversold",
            "pm_read": "neutral_to_mild_positive",
        },
        {
            "topic": "stress_reference",
            "benefit": f"9-1 reference remains positive at {float(stress['delta_return_pct_points_vs_baseline_proxy']):.4f} pct points",
            "risk": "9-1 drawdown is slightly worse; confirms this is not a broad momentum green light",
            "pm_read": "supports_review_only",
        },
        {
            "topic": "governance",
            "benefit": "No new stock selection, no sleeve total weight change, no V57f core modification.",
            "risk": "Still changes rebalance target weights inside selected stocks, so it belongs in V5f/deployment governance rather than V5e exit rules.",
            "pm_read": "clean_boundary",
        },
    ]


def _attribution_review(attribution: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in attribution:
        key = (row["version_id"], row["sleeve"])
        item = grouped.setdefault(
            key,
            {
                "version_id": row["version_id"],
                "sleeve": row["sleeve"],
                "row_count": 0,
                "absolute_weight_delta": 0.0,
                "next_day_contribution_delta": 0.0,
            },
        )
        item["row_count"] += 1
        item["absolute_weight_delta"] += abs(float(row["weight_delta"]))
        item["next_day_contribution_delta"] += float(row["next_day_contribution_delta"])
    rows = list(grouped.values())
    rows.sort(key=lambda r: (r["version_id"], -abs(float(r["next_day_contribution_delta"]))))
    return rows


def _governance_review(governance: list[dict[str, str]], spec_summary: dict[str, Any], eng_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [{"check_id": row["audit_id"], "status": row["status"], "detail": row["violation_count"]} for row in governance]
    rows.extend(
        [
            {"check_id": "spec_not_accepted", "status": "pass" if not spec_summary.get("accepted") else "fail", "detail": spec_summary.get("accepted")},
            {"check_id": "engineering_not_accepted", "status": "pass" if not eng_summary.get("accepted") else "fail", "detail": eng_summary.get("accepted")},
            {"check_id": "v57f_core_modified_false", "status": "pass" if not eng_summary.get("v57f_core_modified") else "fail", "detail": eng_summary.get("v57f_core_modified")},
        ]
    )
    return rows


def _pm_decision(checks: list[dict[str, Any]], variant_review: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passed = all(bool(row["pass"]) for row in checks)
    primary = next(row for row in variant_review if row["version_id"] == "mom_12_1_sleeve_tilt_10pct")
    if passed:
        decision = "promote_momentum_weight_tilt_to_forward_paper_candidate_not_accepted"
        next_gate = "v5f_momentum_weight_tilt_forward_paper_tracking"
        rationale = "Primary 12-1 fixed within-sleeve tilt has positive return edge, non-worse drawdown proxy, and clean governance; still requires forward/paper validation."
    else:
        decision = "retain_momentum_weight_tilt_as_diagnostic_only"
        next_gate = "diagnostic_closeout"
        rationale = "One or more PM/Quant checks failed."
    return [
        {
            "pm_gate_decision": decision,
            "next_gate": next_gate,
            "candidate_id": "mom_12_1_sleeve_tilt_10pct",
            "candidate_promoted": passed,
            "delta_return_pct_points_vs_baseline_proxy": primary["delta_return_pct_points_vs_baseline_proxy"],
            "delta_max_drawdown_pct_points_vs_baseline_proxy": primary["delta_max_drawdown_pct_points_vs_baseline_proxy"],
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    promoted = decision == "promote_momentum_weight_tilt_to_forward_paper_candidate_not_accepted"
    return [
        {"priority": 1, "task": "V5f momentum weight tilt forward/paper tracking packet", "allowed": promoted, "requires_threshold_scan": False},
        {"priority": 2, "task": "V5f deployment governance boundary review for rebalance-day weight tilt", "allowed": promoted, "requires_threshold_scan": False},
        {"priority": 3, "task": "Keep V5e momentum addenda closed as diagnostic", "allowed": True, "requires_threshold_scan": False},
        {"priority": 4, "task": "Scan tilt strength or momentum windows", "allowed": False, "requires_threshold_scan": True},
    ]


def _blockers(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in checks if not bool(row["pass"])]
    if not failed:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "No PM/Quant blocker."}]
    return [
        {
            "blocker_id": row["check_id"],
            "severity": "review",
            "status": "blocking",
            "description": row["detail"],
        }
        for row in failed
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_delta_return_pct_points: float = 0.0,
    primary_delta_max_drawdown_pct_points: float = 0.0,
    stress_delta_return_pct_points: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_momentum_weight_tilt_pm_quant_review",
        "status": status,
        "pm_gate_decision": decision,
        "primary_candidate": "mom_12_1_sleeve_tilt_10pct",
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
    variant_review: list[dict[str, Any]],
    candidate_checks: list[dict[str, Any]],
    risk_benefit: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    primary = next(row for row in variant_review if row["version_id"] == "mom_12_1_sleeve_tilt_10pct")
    stress = next(row for row in variant_review if row["version_id"] == "mom_9_1_sleeve_tilt_10pct")
    return "\n".join(
        [
            "# V5f Momentum Weight Tilt PM/Quant Review",
            "",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`",
            "- Status: forward/paper review candidate only; not accepted.",
            "- Scope: V57f-selected stocks only, official rebalance dates only, same sleeve total weight preserved.",
            f"- Primary 12-1 delta return: {float(primary['delta_return_pct_points_vs_baseline_proxy']):.4f} pct points vs baseline proxy.",
            f"- Primary 12-1 max drawdown delta: {float(primary['delta_max_drawdown_pct_points_vs_baseline_proxy']):.4f} pct points.",
            f"- 9-1 stress/reference delta return: {float(stress['delta_return_pct_points_vs_baseline_proxy']):.4f} pct points.",
            "",
            "## PM Read",
            "- Momentum should not reopen V5e exit/delay-sell acceptance.",
            "- The useful branch is rebalance-day weight governance inside the existing V57f holding pool.",
            "- The edge is positive but modest; it needs forward/paper evidence and deployment governance before any stronger status.",
            "",
            "## Checks",
            *[f"- {row['check_id']}: {'pass' if row['pass'] else 'fail'} ({row['detail']})" for row in candidate_checks],
            "",
            "## Risk Benefit",
            *[f"- {row['topic']}: {row['pm_read']} | benefit={row['benefit']} | risk={row['risk']}" for row in risk_benefit],
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f momentum weight tilt forward/paper tracking packet

任务目标：
基于 `v5f_momentum_weight_tilt_pm_quant_review/current/`，对 `mom_12_1_sleeve_tilt_10pct` 做 forward/paper tracking 准备。它只能在 V57f 已选股票内、正式调仓日、同 sleeve 内做固定 10% 权重倾斜，不得新增股票、不得改变 sleeve 总权重、不得扫描参数、不得标记 accepted。

当前 PM gate：
`{decision["pm_gate_decision"]}`

必须输出：
- forward/paper tracking schema
- rebalance-day checklist
- governance audit
- next restore/deployment queue
- not accepted / not live approved status
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Momentum Weight Tilt PM/Quant Rules",
            "",
            "- Use only V57f selected stocks.",
            "- Apply only on official V57f rebalance dates.",
            "- Preserve each sleeve total weight.",
            "- Do not scan momentum windows or tilt strength.",
            "- Do not mark accepted or live approved.",
            "- Do not modify V57f core.",
            "- Do not reopen V5e exit/delay-sell gate.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPEC_DIR / "v5f_momentum_weight_tilt_summary.json",
        SPEC_DIR / "v5f_momentum_weight_tilt_rule_spec.csv",
        SPEC_DIR / "v5f_momentum_weight_tilt_boundary.csv",
        ENG_DIR / "v5f_momentum_weight_tilt_summary.json",
        ENG_DIR / "v5f_momentum_weight_tilt_metrics.csv",
        ENG_DIR / "v5f_momentum_weight_tilt_rebalance_attribution.csv",
        ENG_DIR / "v5f_momentum_weight_tilt_governance_audit.csv",
        ENG_DIR / "v5f_momentum_weight_tilt_pm_gate_decision.csv",
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
    print(json.dumps(run_v5f_momentum_weight_tilt_pm_quant_review(Path(".")), ensure_ascii=False, indent=2))
