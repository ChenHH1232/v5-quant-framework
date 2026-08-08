from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_internal_subsleeve_deep_research_spec") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_internal_subsleeve_deep_research_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_internal_subsleeve_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_internal_subsleeve_summary.json", summary)
        return summary

    rough_summary = _read_json(root / ROUGH_DIR / "v5f_structural_rough_screen_summary.json")
    comparison = _read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_comparison_matrix.csv")
    deep = [row for row in comparison if row["rough_screen_status"] == "worth_deep_research"]
    diagnostic = [row for row in comparison if row["rough_screen_status"] != "worth_deep_research"]
    rule_spec = _rule_spec(deep)
    boundary = _boundary()
    decision = _decision(deep)
    queue = _next_queue(deep)

    _write_csv(out / "v5f_internal_subsleeve_admitted_candidates.csv", deep)
    _write_csv(out / "v5f_internal_subsleeve_diagnostic_archive.csv", diagnostic)
    _write_csv(out / "v5f_internal_subsleeve_rule_spec.csv", rule_spec)
    _write_csv(out / "v5f_internal_subsleeve_boundary_matrix.csv", boundary)
    _write_csv(out / "v5f_internal_subsleeve_pm_decision.csv", decision)
    _write_csv(out / "v5f_internal_subsleeve_next_queue.csv", queue)
    _write_csv(out / "v5f_internal_subsleeve_blockers.csv", [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Deep research spec generated from rough screen."}])
    (out / "v5f_internal_subsleeve_next_prompt.md").write_text(_prompt(deep), encoding="utf-8")
    (out / "v5f_internal_subsleeve_report.md").write_text(_report(deep, diagnostic, decision), encoding="utf-8")
    (out / "v5f_internal_subsleeve_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = deep[0] if deep else {}
    summary = _summary(
        "completed_v5f_internal_subsleeve_deep_research_spec",
        decision[0]["pm_gate_decision"],
        [],
        admitted_count=len(deep),
        primary_candidate=best.get("direction_id", ""),
        primary_delta_return=float(best.get("delta_return_pct_points_vs_repaired_baseline", 0.0) or 0.0),
        primary_delta_drawdown=float(best.get("delta_max_drawdown_pct_points_vs_repaired_baseline", 0.0) or 0.0),
    )
    _write_json(out / "v5f_internal_subsleeve_summary.json", summary)
    return summary


def _rule_spec(deep: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in deep:
        budget = "70_30" if "70_30" in row["direction_id"] else "80_20"
        rows.append(
            {
                "candidate_id": row["direction_id"],
                "structure": "v57f_pool_internal_subsleeve",
                "value_core_budget": "70%" if budget == "70_30" else "80%",
                "momentum_subsleeve_budget": "30%" if budget == "70_30" else "20%",
                "momentum_feature": "mom_12_1",
                "selection_scope": "same-sleeve top tercile inside repaired V57f selected stocks",
                "sleeve_total_weight_preserved": True,
                "full_market_selection": False,
                "threshold_scan_used": False,
                "accepted": False,
            }
        )
    return rows


def _boundary() -> list[dict[str, Any]]:
    return [
        {"boundary": "benchmark", "rule": "startup preload repaired V57f only", "allowed": True},
        {"boundary": "full_market_stock_selection", "rule": "blocked", "allowed": False},
        {"boundary": "new_v57f_stock", "rule": "blocked", "allowed": False},
        {"boundary": "sleeve_total_weight_change", "rule": "blocked", "allowed": False},
        {"boundary": "v57f_core_change", "rule": "blocked", "allowed": False},
        {"boundary": "parameter_scan", "rule": "blocked; only admitted 70/30 and 80/20 fixed versions", "allowed": False},
        {"boundary": "accepted_or_live_status", "rule": "blocked", "allowed": False},
    ]


def _decision(deep: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "admit_internal_subsleeve_to_deep_research_not_accepted" if deep else "no_internal_subsleeve_deep_candidate",
            "admitted_count": len(deep),
            "primary_candidate": deep[0]["direction_id"] if deep else "",
            "accepted": False,
            "live_trading_approved": False,
            "rationale": "Rough screen found V57f-pool internal sub-sleeve versions with positive return and non-worse drawdown."
            if deep
            else "No rough-screen candidate met the deep-research rule.",
        }
    ]


def _next_queue(deep: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for idx, row in enumerate(deep, start=1):
        rows.append({"priority": idx, "next_task": f"Deep engineering review for {row['direction_id']}", "allowed": True, "requires_threshold_scan": False})
    rows.append({"priority": len(rows) + 1, "next_task": "Compare admitted internal sub-sleeve against current equal-blend overlay", "allowed": True, "requires_threshold_scan": False})
    rows.append({"priority": len(rows) + 1, "next_task": "Full dual-sleeve allocation", "allowed": False, "requires_threshold_scan": False})
    return rows


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    admitted_count: int = 0,
    primary_candidate: str = "",
    primary_delta_return: float = 0.0,
    primary_delta_drawdown: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_internal_subsleeve_deep_research_spec",
        "status": status,
        "pm_gate_decision": decision,
        "admitted_count": admitted_count,
        "primary_candidate": primary_candidate,
        "primary_delta_return_pct_points_vs_repaired_baseline": primary_delta_return,
        "primary_delta_max_drawdown_pct_points_vs_repaired_baseline": primary_delta_drawdown,
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


def _prompt(deep: list[dict[str, str]]) -> str:
    candidates = ", ".join(row["direction_id"] for row in deep)
    return f"""Working directory:
D:\\hh\\codex\\v5

Task name:
V5f internal sub-sleeve deep engineering review

Objective:
Run a deep engineering review for the admitted fixed V57f-pool internal sub-sleeve candidates: {candidates}. Use startup-preload repaired V57f as the only benchmark. Do not modify V57f, do not select full-market stocks, do not change sleeve total weights, do not scan parameters, and do not mark accepted/live approved.

Read first:
- v5f_internal_subsleeve_deep_research_spec/current/v5f_internal_subsleeve_summary.json
- v5f_internal_subsleeve_deep_research_spec/current/v5f_internal_subsleeve_rule_spec.csv
- v5f_structural_rough_screen/current/v5f_structural_rough_screen_comparison_matrix.csv
- v5f_repaired_baseline_overlay_comparison/current/v5f_repaired_overlay_summary.json

Required outputs:
- deep metrics
- yearly stability
- sleeve attribution
- turnover/cost health
- comparison vs current equal-blend candidate
- PM gate not accepted
"""


def _report(deep: list[dict[str, str]], diagnostic: list[dict[str, str]], decision: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Deep Research Spec",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            "- Status: not accepted; deep research only.",
            "",
            "## Admitted",
            *[
                f"- `{row['direction_id']}`: delta={float(row['delta_return_pct_points_vs_repaired_baseline']):.4f} pct, dd_delta={float(row['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct"
                for row in deep
            ],
            "",
            "## Diagnostic / Archive",
            *[f"- `{row['direction_id']}`: {row['rough_screen_status']}" for row in diagnostic],
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Rules",
            "",
            "- Repaired V57f baseline only.",
            "- V57f selected-stock pool only.",
            "- Same-sleeve sub-sleeve only.",
            "- No full-market stock selection.",
            "- No parameter scan.",
            "- Not accepted and not live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        ROUGH_DIR / "v5f_structural_rough_screen_summary.json",
        ROUGH_DIR / "v5f_structural_rough_screen_comparison_matrix.csv",
        ROUGH_DIR / "v5f_structural_rough_screen_next_queue.csv",
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
    print(json.dumps(run_v5f_internal_subsleeve_deep_research_spec(Path(".")), ensure_ascii=False, indent=2))
