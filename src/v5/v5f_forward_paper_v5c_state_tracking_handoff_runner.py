from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5f_forward_paper_tracking_with_v5c_state_tags") / "current"

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    platform = _read_json(root / "v5f_joinquant_platform_forward_handoff" / "current" / "v5f_platform_forward_handoff_summary.json")
    v5c_p4 = _read_json(root / "v5c_p4_state_forward_observation_packet" / "current" / "v5c_p4_state_forward_observation_summary.json")
    v5c_overheat = _read_json(root / "v5c_overheat_no_new_overweight_limited_engineering" / "current" / "v5c_overheat_no_new_overweight_summary.json")
    v5g = _read_json(root / "v5g_vs_midterm_model_comparison" / "current" / "v5g_vs_midterm_summary.json")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_forward_paper_tracking_with_v5c_state_tags",
        "status": "completed_forward_tracking_handoff",
        "primary_candidate": PRIMARY,
        "baseline": BASELINE,
        "v5c_role": "state_tag_observation_layer_not_trading_rule",
        "v5g_role": "secondary_observation_not_replacement",
        "platform_clean_edge_pct_points": platform["clean_platform_edge_pct_points"],
        "platform_relative_wealth_edge_pct": platform["relative_wealth_edge_pct"],
        "v5c_overheat_delta_vs_primary_pct_points": v5c_overheat["candidate_delta_return_pct_points_vs_primary"],
        "v5g_best_delta_vs_primary_pct_points": v5g["delta_return_pct_points_vs_midterm_champion"],
        "v5c_p4_watchlist_seed_rows": v5c_p4["watchlist_seed_rows"],
        "v5c_p4_pm_review_queue_rows": v5c_p4["pm_review_queue_rows"],
        "round_lot_policy_status": platform["round_lot_policy_status"],
        "pm_gate_decision": "continue_v5f_primary_forward_paper_with_v5c_state_tags_observation_only",
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "new_trading_rule_added": False,
        "v5c_changes_weights": False,
    }

    _write_json(out / "v5f_v5c_state_tracking_handoff_summary.json", summary)
    _write_csv(out / "v5f_v5c_state_tracking_model_roles.csv", _model_roles(platform, v5c_overheat, v5g))
    _write_csv(out / "v5f_v5c_state_tag_schema.csv", _state_tag_schema())
    _write_csv(out / "v5f_v5c_forward_tracking_template.csv", _tracking_template())
    _write_csv(out / "v5f_v5c_platform_export_checklist.csv", _platform_export_checklist())
    _write_csv(out / "v5f_v5c_allowed_blocked_actions.csv", _allowed_blocked_actions())
    _write_csv(out / "v5f_v5c_pm_gate_decision.csv", [_pm_decision(summary)])
    _write_csv(out / "v5f_v5c_next_queue.csv", _next_queue())
    _write_rules(out / "v5f_v5c_agent_execution_rules.md")
    _write_report(out / "v5f_v5c_state_tracking_handoff_report.md", summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5f_v5c_state_tracking_handoff_summary.json"


def _model_roles(platform: dict[str, Any], v5c_overheat: dict[str, Any], v5g: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "component": "V5f primary",
            "id": PRIMARY,
            "role": "forward_paper_primary",
            "evidence": f"JoinQuant clean platform edge {platform['clean_platform_edge_pct_points']:.4f} pct points vs repaired baseline",
            "changes_trading": True,
            "accepted": False,
            "decision": "retain_as_primary_forward_paper",
        },
        {
            "component": "V5c state tags",
            "id": "v5c_p4_state_forward_observation_packet",
            "role": "state_observation_and_risk_explanation",
            "evidence": "P4 observation packet ready; V5c overheat overlay underperformed V5f primary",
            "changes_trading": False,
            "accepted": False,
            "decision": "attach_tags_only_do_not_trade",
        },
        {
            "component": "V5c overheat no-new-overweight",
            "id": v5c_overheat["candidate_id"],
            "role": "diagnostic_only",
            "evidence": f"Delta vs V5f primary {v5c_overheat['candidate_delta_return_pct_points_vs_primary']:.4f} pct points",
            "changes_trading": False,
            "accepted": False,
            "decision": "do_not_replace_v5f_champion",
        },
        {
            "component": "V5g state gated",
            "id": v5g["best_new_model_id"],
            "role": "secondary_observation",
            "evidence": f"Delta vs V5f primary {v5g['delta_return_pct_points_vs_midterm_champion']:.4f} pct points",
            "changes_trading": False,
            "accepted": False,
            "decision": "secondary_observation_only",
        },
    ]


def _state_tag_schema() -> list[dict[str, Any]]:
    return [
        {"field": "observation_date", "required": True, "description": "Forward observation date; no future data."},
        {"field": "rebalance_date", "required": True, "description": "Official V57f/V5f rebalance date if applicable."},
        {"field": "code", "required": True, "description": "Stock code in V57f/V5f pool only."},
        {"field": "sleeve", "required": True, "description": "Existing V57f sleeve."},
        {"field": "v5f_target_weight", "required": True, "description": "Frozen V5f primary target weight."},
        {"field": "v5c_valuation_state", "required": False, "description": "Cheap/neutral/expensive state from V5c P2/P3 where available."},
        {"field": "v5c_crowding_state", "required": False, "description": "Crowding or overheat observation tag."},
        {"field": "v5c_overheat_flag", "required": False, "description": "Observation-only flag, must not change target weight."},
        {"field": "v5c_quality_flag", "required": False, "description": "Financial quality tag if PIT available."},
        {"field": "platform_execution_residual", "required": False, "description": "sub_lot, paused, limit_blocked, cancelled, or none."},
        {"field": "pm_review_required", "required": True, "description": "True when V5c state needs human review."},
        {"field": "trade_rule_changed", "required": True, "description": "Must remain false."},
    ]


def _tracking_template() -> list[dict[str, Any]]:
    return [
        {
            "tracking_window_id": "next_official_forward_window",
            "observation_date": "",
            "rebalance_date": "",
            "model_id": PRIMARY,
            "baseline_id": BASELINE,
            "code": "",
            "sleeve": "",
            "v5f_target_weight": "",
            "v5c_valuation_state": "",
            "v5c_crowding_state": "",
            "v5c_overheat_flag": "",
            "v5c_quality_flag": "",
            "platform_execution_residual": "",
            "pm_review_required": "",
            "trade_rule_changed": "false",
            "notes": "V5c tags are observation only.",
        }
    ]


def _platform_export_checklist() -> list[dict[str, Any]]:
    return [
        {"rank": 1, "export_item": "primary_daily_returns", "model": PRIMARY, "required": True, "timing": "after forward window close"},
        {"rank": 2, "export_item": "baseline_daily_returns", "model": BASELINE, "required": True, "timing": "after forward window close"},
        {"rank": 3, "export_item": "primary_transactions_positions_logs", "model": PRIMARY, "required": True, "timing": "after forward window close"},
        {"rank": 4, "export_item": "baseline_transactions_positions_logs", "model": BASELINE, "required": True, "timing": "after forward window close"},
        {"rank": 5, "export_item": "v5c_state_tag_snapshot", "model": "v5c_observation_layer", "required": True, "timing": "at signal/rebalance date"},
        {"rank": 6, "export_item": "round_lot_residual_log", "model": "platform_execution", "required": True, "timing": "during platform run"},
    ]


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "continue_v5f_forward_paper_tracking", "allowed": True, "blocked": False, "notes": "Primary line."},
        {"action": "attach_v5c_state_tags", "allowed": True, "blocked": False, "notes": "Observation only."},
        {"action": "use_v5c_tags_for_pm_review_queue", "allowed": True, "blocked": False, "notes": "No automatic trading."},
        {"action": "use_v5c_tags_to_change_weights", "allowed": False, "blocked": True, "notes": "Not supported by current evidence."},
        {"action": "replace_v5f_with_v5g_state_gated", "allowed": False, "blocked": True, "notes": "V5g underperformed V5f champion."},
        {"action": "mark_accepted", "allowed": False, "blocked": True, "notes": "Not allowed."},
        {"action": "mark_live_approved", "allowed": False, "blocked": True, "notes": "Not allowed."},
        {"action": "modify_v57f_core", "allowed": False, "blocked": True, "notes": "Not allowed."},
    ]


def _pm_decision(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "pm_gate_decision": summary["pm_gate_decision"],
        "primary_candidate": PRIMARY,
        "v5c_role": summary["v5c_role"],
        "v5g_role": summary["v5g_role"],
        "accepted": False,
        "live_trading_approved": False,
        "next_action": "forward_paper_tracking_with_state_tags",
    }


def _next_queue() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "next_task": "continue_v5f_primary_forward_paper_tracking",
            "status": "ready",
            "detail": "Track internal_subsleeve_mom12_70_30 vs repaired baseline.",
        },
        {
            "rank": 2,
            "next_task": "attach_v5c_state_tags_to_each_forward_observation",
            "status": "ready",
            "detail": "Use P4 observation fields; no automatic weight changes.",
        },
        {
            "rank": 3,
            "next_task": "next_official_rebalance_forward_closeout",
            "status": "waiting_future_official_rebalance",
            "detail": "After next forward window, compare platform primary vs baseline and review V5c tag usefulness.",
        },
    ]


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    text = f"""# V5f Forward/Paper Tracking With V5c State Tags

## Decision

Continue `{PRIMARY}` as V5f forward/paper primary. V5c is attached as a state-tag observation layer only.

## Why

- JoinQuant clean platform edge vs repaired baseline: `{summary['platform_clean_edge_pct_points']:.4f}` pct points.
- V5c overheat/no-new-overweight underperformed V5f primary by `{summary['v5c_overheat_delta_vs_primary_pct_points']:.4f}` pct points.
- V5g best state-gated model underperformed V5f primary by `{summary['v5g_best_delta_vs_primary_pct_points']:.4f}` pct points.
- V5c P4 is ready for observation with `{summary['v5c_p4_watchlist_seed_rows']}` watchlist rows and `{summary['v5c_p4_pm_review_queue_rows']}` PM review rows.

## Boundary

V5c tags can explain valuation, crowding, overheat and quality states. They cannot change V5f target weights, trigger trades, or replace V57f/V5f rules.

## PM Gate

`{summary['pm_gate_decision']}`
"""
    path.write_text(text, encoding="utf-8")


def _write_rules(path: Path) -> None:
    path.write_text(
        """# V5f + V5c State Tracking Rules

- V5f primary: internal_subsleeve_mom12_70_30.
- Baseline: v57f_startup_preload_repaired_baseline.
- V5c tags are observation only.
- Do not change V5f weights based on V5c tags.
- Do not modify V57f core.
- Do not scan parameters.
- Do not mark accepted or live approved.
- Use JoinQuant platform exports only for attribution/forward tracking.
- Use BaoStock as local 5min data source when raw 5min data is needed.
""",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
    run()
