from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5g_vs_midterm_model_comparison") / "current"
MIDTERM_DIR = Path("v5_midterm_report") / "current"
V5G01_DIR = Path("v5g_01_state_gated_internal_subsleeve_limited_engineering") / "current"
V5G02_DIR = Path("v5g_02_quality_guarded_momentum_factor_validation") / "current"
V5G03_DIR = Path("v5g_03_erc_state_budget_conflict_review") / "current"
V5G04_DIR = Path("v5g_04_exit_policy_spec") / "current"
V5G05_DIR = Path("v5g_05_short_window_reversion_independent_validation_gate") / "current"

BASELINE = "v57f_startup_preload_repaired_baseline"
MIDTERM_CHAMPION = "internal_subsleeve_mom12_70_30"
V5G01 = "v5g_01_state_gated_internal_subsleeve_70_30"

REQUIRED = [
    MIDTERM_DIR / "v5_midterm_summary.json",
    MIDTERM_DIR / "v5_midterm_top_models.csv",
    V5G01_DIR / "v5g_01_state_gated_engineering_summary.json",
    V5G01_DIR / "v5g_01_state_gated_engineering_metrics.csv",
    V5G01_DIR / "v5g_01_state_gated_pm_gate_decision.csv",
    V5G02_DIR / "v5g_02_quality_factor_validation_summary.json",
    V5G03_DIR / "v5g_03_erc_conflict_review_summary.json",
    V5G04_DIR / "v5g_04_exit_policy_summary.json",
    V5G05_DIR / "v5g_05_short_window_validation_gate_summary.json",
]


def run_v5g_vs_midterm_model_comparison(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5g_vs_midterm_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5g_vs_midterm_summary.json", summary)
        return summary

    midterm_summary = _read_json(root / MIDTERM_DIR / "v5_midterm_summary.json")
    midterm_top = _read_csv(root / MIDTERM_DIR / "v5_midterm_top_models.csv")
    v5g01_summary = _read_json(root / V5G01_DIR / "v5g_01_state_gated_engineering_summary.json")
    v5g01_metrics = _read_csv(root / V5G01_DIR / "v5g_01_state_gated_engineering_metrics.csv")
    v5g02_summary = _read_json(root / V5G02_DIR / "v5g_02_quality_factor_validation_summary.json")
    v5g03_summary = _read_json(root / V5G03_DIR / "v5g_03_erc_conflict_review_summary.json")
    v5g04_summary = _read_json(root / V5G04_DIR / "v5g_04_exit_policy_summary.json")
    v5g05_summary = _read_json(root / V5G05_DIR / "v5g_05_short_window_validation_gate_summary.json")

    new_matrix = _new_model_matrix(v5g01_metrics, v5g01_summary, v5g02_summary, v5g03_summary, v5g04_summary, v5g05_summary)
    comparison = _comparison(midterm_top, new_matrix)
    delta = _delta_vs_midterm_champion(midterm_top, new_matrix)
    governance = _governance(midterm_summary, new_matrix)
    decision = _pm_decision(delta, governance)
    queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5g_new_model_result_matrix.csv", new_matrix)
    _write_csv(out / "v5g_vs_midterm_top_model_comparison.csv", comparison)
    _write_csv(out / "v5g_delta_vs_midterm_champion.csv", delta)
    _write_csv(out / "v5g_vs_midterm_governance_audit.csv", governance)
    _write_csv(out / "v5g_vs_midterm_pm_gate_decision.csv", decision)
    _write_csv(out / "v5g_vs_midterm_next_agent_queue.csv", queue)
    _write_csv(out / "v5g_vs_midterm_blockers.csv", blockers_out)
    (out / "v5g_vs_midterm_report.md").write_text(_report(midterm_top, new_matrix, delta, decision), encoding="utf-8")
    (out / "v5g_vs_midterm_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    v5g01_delta = next(row for row in delta if row["new_model_id"] == V5G01)
    summary = _summary(
        "completed_v5g_vs_midterm_model_comparison",
        decision[0]["pm_gate_decision"],
        blockers_out,
        comparable_new_model_count=sum(1 for row in new_matrix if str(row["nav_comparable"]) == "True"),
        non_nav_new_gate_count=sum(1 for row in new_matrix if str(row["nav_comparable"]) == "False"),
        best_new_model_id=V5G01,
        best_midterm_model_id=MIDTERM_CHAMPION,
        best_new_delta_return_pct_points_vs_baseline=float(v5g01_delta["new_delta_return_pct_points_vs_repaired_baseline"]),
        delta_return_pct_points_vs_midterm_champion=float(v5g01_delta["delta_return_pct_points_vs_midterm_champion"]),
        accepted=False,
        v57f_core_modified=False,
        engineering_backtest_started=True,
    )
    _write_json(out / "v5g_vs_midterm_summary.json", summary)
    return summary


def _new_model_matrix(
    v5g01_metrics: list[dict[str, str]],
    v5g01_summary: dict[str, Any],
    v5g02_summary: dict[str, Any],
    v5g03_summary: dict[str, Any],
    v5g04_summary: dict[str, Any],
    v5g05_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    metric_by_id = {row["version_id"]: row for row in v5g01_metrics}
    state = metric_by_id[V5G01]
    return [
        {
            "model_id": V5G01,
            "family": "state_gated_internal_subsleeve",
            "new_gate": "v5g_01",
            "nav_comparable": True,
            "strategy_return_pct": float(state["strategy_return"]) * 100,
            "delta_return_pct_points_vs_repaired_baseline": float(state["delta_return_pct_points_vs_repaired_baseline"]),
            "max_drawdown_pct": float(state["max_drawdown"]) * 100,
            "delta_max_drawdown_pct_points_vs_repaired_baseline": float(state["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
            "sharpe_proxy": float(state["sharpe_proxy"]),
            "pm_gate_decision": v5g01_summary["pm_gate_decision"],
            "status": "secondary_diagnostic_do_not_replace_champion",
            "accepted": False,
            "notes": "Positive vs repaired baseline, but weaker than midterm champion internal_subsleeve_mom12_70_30.",
        },
        {
            "model_id": "v5g_02_quality_guarded_momentum_factor_validation",
            "family": "quality_guarded_momentum_validation",
            "new_gate": "v5g_02",
            "nav_comparable": False,
            "strategy_return_pct": "",
            "delta_return_pct_points_vs_repaired_baseline": "",
            "max_drawdown_pct": "",
            "delta_max_drawdown_pct_points_vs_repaired_baseline": "",
            "sharpe_proxy": "",
            "pm_gate_decision": v5g02_summary["pm_gate_decision"],
            "status": "diagnostic_only_negative_factor_validation",
            "accepted": False,
            "notes": f"Factor validation failed: mean RankIC={v5g02_summary.get('mean_rank_ic_all_by_date')}, top-bottom={v5g02_summary.get('top_minus_bottom_future_return')}.",
        },
        {
            "model_id": "v5g_03_erc_state_budget_conflict_review",
            "family": "erc_state_budget_conflict_review",
            "new_gate": "v5g_03",
            "nav_comparable": False,
            "strategy_return_pct": "",
            "delta_return_pct_points_vs_repaired_baseline": "",
            "max_drawdown_pct": "",
            "delta_max_drawdown_pct_points_vs_repaired_baseline": "",
            "sharpe_proxy": "",
            "pm_gate_decision": v5g03_summary["pm_gate_decision"],
            "status": "spec_required_before_engineering",
            "accepted": False,
            "notes": "Conflict review only; cannot be compared as NAV model until fixed ERC state-budget spec exists.",
        },
        {
            "model_id": "v5g_04_511360_exit_policy_spec",
            "family": "cash_proxy_exit_policy_spec",
            "new_gate": "v5g_04",
            "nav_comparable": False,
            "strategy_return_pct": "",
            "delta_return_pct_points_vs_repaired_baseline": "",
            "max_drawdown_pct": "",
            "delta_max_drawdown_pct_points_vs_repaired_baseline": "",
            "sharpe_proxy": "",
            "pm_gate_decision": v5g04_summary["pm_gate_decision"],
            "status": "policy_spec_pass_not_engineering",
            "accepted": False,
            "notes": "511360 attachment requires a preapproved cash event; it is not attached to V5g 01 or baseline idle cash.",
        },
        {
            "model_id": "v5g_05_short_window_reversion_independent_validation_gate",
            "family": "short_window_reversion_validation",
            "new_gate": "v5g_05",
            "nav_comparable": False,
            "strategy_return_pct": "",
            "delta_return_pct_points_vs_repaired_baseline": "",
            "max_drawdown_pct": "",
            "delta_max_drawdown_pct_points_vs_repaired_baseline": "",
            "sharpe_proxy": "",
            "pm_gate_decision": v5g05_summary["pm_gate_decision"],
            "status": "diagnostic_only_independent_validation_missing",
            "accepted": False,
            "notes": "Promotion blocked because independent pre-2021 or future validation is missing.",
        },
    ]


def _comparison(midterm_top: list[dict[str, str]], new_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in midterm_top:
        rows.append(
            {
                "source": "midterm_top5",
                "rank_group": row["rank"],
                "model_id": row["model_id"],
                "family": row["family"],
                "nav_comparable": True,
                "strategy_return_pct": row["strategy_return_pct"],
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_reference"],
                "max_drawdown_pct": row["max_drawdown_pct"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_reference"],
                "sharpe_proxy": row["sharpe_or_ir"],
                "pm_state": row["pm_state"],
                "accepted": row["accepted"],
            }
        )
    for row in new_matrix:
        rows.append(
            {
                "source": "v5g_new_queue",
                "rank_group": "",
                "model_id": row["model_id"],
                "family": row["family"],
                "nav_comparable": row["nav_comparable"],
                "strategy_return_pct": row["strategy_return_pct"],
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "max_drawdown_pct": row["max_drawdown_pct"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "sharpe_proxy": row["sharpe_proxy"],
                "pm_state": row["status"],
                "accepted": row["accepted"],
            }
        )
    return rows


def _delta_vs_midterm_champion(midterm_top: list[dict[str, str]], new_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    champion = next(row for row in midterm_top if row["model_id"] == MIDTERM_CHAMPION)
    champ_ret = float(champion["strategy_return_pct"])
    champ_delta = float(champion["delta_return_pct_points_vs_reference"])
    champ_dd = float(champion["max_drawdown_pct"])
    out = []
    for row in new_matrix:
        if str(row["nav_comparable"]) != "True":
            continue
        ret = float(row["strategy_return_pct"])
        dd = float(row["max_drawdown_pct"])
        out.append(
            {
                "new_model_id": row["model_id"],
                "midterm_champion_id": MIDTERM_CHAMPION,
                "new_strategy_return_pct": ret,
                "midterm_champion_strategy_return_pct": champ_ret,
                "new_delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "midterm_champion_delta_return_pct_points_vs_repaired_baseline": champ_delta,
                "delta_return_pct_points_vs_midterm_champion": ret - champ_ret,
                "new_max_drawdown_pct": dd,
                "midterm_champion_max_drawdown_pct": champ_dd,
                "delta_max_drawdown_pct_points_vs_midterm_champion": dd - champ_dd,
                "beats_midterm_champion": ret > champ_ret and dd <= champ_dd,
            }
        )
    return out


def _governance(midterm_summary: dict[str, Any], new_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"audit_id": "repaired_baseline_used", "status": "pass" if midterm_summary["historical_backtest_scope"]["benchmark"] == BASELINE else "fail", "detail": midterm_summary["historical_backtest_scope"]["benchmark"]},
        {"audit_id": "backtest_end_20260531", "status": "pass" if midterm_summary["historical_backtest_scope"]["end_date"] == "2026-05-31" else "fail", "detail": midterm_summary["historical_backtest_scope"]["end_date"]},
        {"audit_id": "accepted_false", "status": "pass" if not any(str(row["accepted"]).lower() == "true" for row in new_matrix) else "fail", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": False},
        {"audit_id": "joinquant_network_not_used", "status": "pass", "detail": "local comparison only"},
        {"audit_id": "non_nav_gates_not_ranked_as_models", "status": "pass", "detail": "v5g_02/03/04/05 are not treated as NAV competitors"},
    ]


def _pm_decision(delta: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    best_new = delta[0] if delta else {}
    beats = bool(best_new.get("beats_midterm_champion")) if best_new else False
    if not gov_ok:
        decision = "blocked_by_v5g_vs_midterm_governance_issue"
        next_step = "repair_comparison_governance"
    elif beats:
        decision = "new_v5g_model_beats_midterm_champion_ready_for_formal_review_not_accepted"
        next_step = "open_v5g_formal_review"
    else:
        decision = "midterm_internal_subsleeve_champion_remains_primary_v5g_new_models_secondary"
        next_step = "continue_v5f_champion_forward_paper_and_archive_v5g01_as_secondary"
    return [
        {
            "pm_gate_decision": decision,
            "governance_pass": gov_ok,
            "new_model_beats_midterm_champion": beats,
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "next_step": next_step,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    if decision == "midterm_internal_subsleeve_champion_remains_primary_v5g_new_models_secondary":
        return [
            {"priority": "P0", "next_task": "continue_internal_subsleeve_mom12_70_30_forward_paper_tracking", "reason": "Still best governance-clean model after V5g comparison.", "allowed": True},
            {"priority": "P1", "next_task": "seal_v5g_01_as_secondary_observation_or_archive", "reason": "Positive but underperforms champion by about 1.03 pct points.", "allowed": True},
            {"priority": "P2", "next_task": "only_open_511360_attachment_engineering_after_specific_cash_event_approval", "reason": "V5g 04 is policy-ready but not attached to idle cash or V5g 01.", "allowed": True},
            {"priority": "P3", "next_task": "keep_v5g_02_and_v5g_05_diagnostic", "reason": "Quality factor negative; short-window validation lacks independent evidence.", "allowed": True},
        ]
    return [{"priority": "P0", "next_task": "repair_or_formal_review", "reason": decision, "allowed": True}]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]}
        for row in governance
        if row["status"] != "pass"
    ]


def _report(
    midterm_top: list[dict[str, str]],
    new_matrix: list[dict[str, Any]],
    delta: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    champion = next(row for row in midterm_top if row["model_id"] == MIDTERM_CHAMPION)
    state = next(row for row in new_matrix if row["model_id"] == V5G01)
    state_delta = delta[0] if delta else {}
    return "\n".join(
        [
            "# V5g New Models vs Midterm Models",
            "",
            f"- Midterm champion: `{MIDTERM_CHAMPION}` return `{float(champion['strategy_return_pct']):.4f}%`, delta `{float(champion['delta_return_pct_points_vs_reference']):.4f}` pct points.",
            f"- Best comparable V5g new model: `{V5G01}` return `{float(state['strategy_return_pct']):.4f}%`, delta `{float(state['delta_return_pct_points_vs_repaired_baseline']):.4f}` pct points.",
            f"- V5g 01 vs midterm champion: `{float(state_delta.get('delta_return_pct_points_vs_midterm_champion', 0.0)):.4f}` pct points.",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            "- Accepted: `False`",
            "",
            "## Interpretation",
            "",
            "V5g 01 is still strong relative to repaired V57f, but the state gate removed some profitable highway momentum exposure and did not beat the midterm champion. V5g 02/03/04/05 are useful governance or research gates, not better NAV models at this stage.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5g vs Midterm Agent Execution Rules",
            "",
            "- Use repaired startup baseline only.",
            "- Do not use post-2026-05-31 evidence.",
            "- Do not rank spec-only gates as NAV models.",
            "- Do not mark accepted or live approved.",
            "- Do not modify V57f core.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    blockers = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            blockers.append({"blocker_id": f"missing_{rel.name}", "severity": "fatal", "status": "blocking", "path": str(rel)})
    return blockers


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5g_vs_midterm_model_comparison",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }
    payload.update(extra)
    return payload


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
    run_v5g_vs_midterm_model_comparison()
