from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_forward_paper_continuation_v5f_prep") / "current"
CLOSEOUT_DIR = Path("v5e_historical_closeout_governance_packet") / "current"
TRACKING_DIR = Path("v5e_511360_forward_paper_tracking") / "current"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_forward_paper_continuation_v5f_prep(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_continuation_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_continuation_summary.json", summary)
        return summary

    closeout = _read_json(root / CLOSEOUT_DIR / "v5e_historical_closeout_summary.json")
    tracking = _read_json(root / TRACKING_DIR / "v5e_511360_forward_tracking_summary.json")
    final_governance = _read_csv(root / CLOSEOUT_DIR / "v5e_final_governance_decision.csv")[0]
    rebalance_dates = _rebalance_dates(root)
    official_202607_available = "2026-07-01" in rebalance_dates

    tracking_registry = _tracking_registry(closeout, tracking)
    restore_status = _official_restore_status(tracking, official_202607_available, rebalance_dates)
    v5f_prep = _v5f_prep_matrix(final_governance)
    paper_workflow = _paper_workflow()
    blocked_actions = _blocked_actions()
    decision = _final_decision(closeout, tracking, official_202607_available)
    queue = _next_queue(official_202607_available)
    blockers_out = _blockers(restore_status)

    _write_csv(out / "v5e_forward_tracking_registry.csv", tracking_registry)
    _write_csv(out / "v5e_511360_official_restore_status.csv", restore_status)
    _write_csv(out / "v5f_deployment_governance_prep_matrix.csv", v5f_prep)
    _write_csv(out / "v5f_paper_trading_workflow_preparation.csv", paper_workflow)
    _write_csv(out / "v5e_continuation_allowed_blocked_actions.csv", blocked_actions)
    _write_csv(out / "v5e_continuation_final_decision.csv", decision)
    _write_csv(out / "v5e_continuation_next_queue.csv", queue)
    _write_csv(out / "v5e_continuation_blockers.csv", blockers_out)
    (out / "v5e_continuation_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5e_continuation_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_continuation_report.md").write_text(
        _report(closeout, tracking, restore_status, decision),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5e_forward_paper_continuation_v5f_prep",
        decision[0]["continuation_decision"],
        [],
        forward_tracking_item_count=len(tracking_registry),
        v5f_prep_item_count=len(v5f_prep),
        official_202607_restore_available=official_202607_available,
        accepted=False,
    )
    _write_json(out / "v5e_continuation_summary.json", summary)
    return summary


def _tracking_registry(closeout: dict[str, Any], tracking: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "tracking_id": "v5e_profit_lock_main_20pct_sell50",
            "status": "forward_paper_candidate_not_accepted",
            "frequency": "each_paper_cycle",
            "metric": "trigger_count, exit_count, cash_drag, VWAP-adjusted edge",
            "accepted": False,
            "current_note": "Do not tune threshold; keep pre-registered +20pct sell50 rule.",
        },
        {
            "tracking_id": "v5e_511360_cash_proxy",
            "status": "forward_review_candidate_not_accepted",
            "frequency": "daily_or_each_paper_cycle",
            "metric": "price, NAV, premium/discount, proxy PnL, liquidity, restore status",
            "accepted": False,
            "current_note": f"Proxy-side realized PnL from latest closeout: {tracking.get('proxy_side_closeout_realized_pnl')}",
        },
        {
            "tracking_id": "v5e_historical_closeout",
            "status": closeout.get("historical_closeout_status", "complete"),
            "frequency": "closed",
            "metric": "governance flags",
            "accepted": False,
            "current_note": "Historical closeout complete; V5e remains not accepted.",
        },
    ]


def _official_restore_status(
    tracking: dict[str, Any],
    official_202607_available: bool,
    rebalance_dates: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "restore_item": "511360_202607_official_restore_closeout",
            "proxy_side_closeout_done": tracking.get("restore_closeout_count", 0) == 3,
            "proxy_side_realized_pnl": tracking.get("proxy_side_closeout_realized_pnl", 0.0),
            "official_v57f_202607_signal_available": official_202607_available,
            "latest_local_v57f_rebalance_signal": rebalance_dates[-1] if rebalance_dates else "",
            "restore_status": "ready_for_official_closeout" if official_202607_available else "forward_only_pending",
            "historical_backtest_blocker": False,
            "accepted": False,
        }
    ]


def _v5f_prep_matrix(final_governance: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "prep_item": "v57f_frozen_baseline_reference",
            "status": "ready",
            "requirement": "Use V57f repaired baseline as frozen reference; do not replace with V5e.",
            "blocks_deployment_until_done": False,
        },
        {
            "prep_item": "v5e_candidate_registry",
            "status": "ready_not_accepted",
            "requirement": "Register profit-lock and 511360 as paper/forward candidates only.",
            "blocks_deployment_until_done": False,
        },
        {
            "prep_item": "paper_trading_governance",
            "status": "prepare_next",
            "requirement": "Define paper signal calendar, audit logs, no-accepted flags, and reporting cadence.",
            "blocks_deployment_until_done": True,
        },
        {
            "prep_item": "acceptance_gate",
            "status": "blocked",
            "requirement": "No acceptance or live approval from historical V5e evidence.",
            "blocks_deployment_until_done": True,
        },
        {
            "prep_item": "threshold_scan_guard",
            "status": "locked",
            "requirement": "Do not scan V5e profit-lock thresholds.",
            "blocks_deployment_until_done": False,
        },
    ]


def _paper_workflow() -> list[dict[str, Any]]:
    return [
        {"step": 1, "workflow_item": "daily_data_intake", "description": "Collect paper-date V57f/V5e candidate inputs; no JoinQuant execution.", "owner": "data_agent"},
        {"step": 2, "workflow_item": "paper_signal_generation", "description": "Generate candidate-only V5e profit-lock and 511360 proxy observations.", "owner": "engineering_agent"},
        {"step": 3, "workflow_item": "governance_audit", "description": "Verify V57f unchanged, thresholds unchanged, accepted=false.", "owner": "quant_validation_agent"},
        {"step": 4, "workflow_item": "pm_review_packet", "description": "Summarize forward evidence and blockers without live approval.", "owner": "pm_agent"},
        {"step": 5, "workflow_item": "restore_closeout", "description": "Run 511360 official restore closeout only when official rebalance signals exist.", "owner": "execution_governance_agent"},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "continue_forward_paper_tracking", "allowed": True, "blocked": False},
        {"action": "prepare_v5f_deployment_governance_workflow", "allowed": True, "blocked": False},
        {"action": "run_511360_official_restore_without_official_signal", "allowed": False, "blocked": True},
        {"action": "mark_v5e_accepted", "allowed": False, "blocked": True},
        {"action": "mark_511360_live_approved", "allowed": False, "blocked": True},
        {"action": "modify_v57f_core", "allowed": False, "blocked": True},
        {"action": "scan_v5e_profit_lock_thresholds", "allowed": False, "blocked": True},
        {"action": "start_joinquant", "allowed": False, "blocked": True},
    ]


def _final_decision(
    closeout: dict[str, Any],
    tracking: dict[str, Any],
    official_202607_available: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "continuation_decision": "continue_v5e_forward_paper_tracking_and_prepare_v5f_governance",
            "historical_closeout_complete": closeout.get("historical_closeout_status") == "complete",
            "v5e_forward_tracking_continues": True,
            "official_restore_closeout_now": official_202607_available,
            "official_restore_status": "ready" if official_202607_available else "pending_future_official_signal",
            "v5f_governance_prep_allowed": True,
            "v5e_accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "joinquant_started": False,
            "accepted": False,
        }
    ]


def _next_queue(official_202607_available: bool) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "V5f deployment governance / paper trading workflow packet",
            "allowed": True,
            "requires_official_202607_signal": False,
        },
        {
            "priority": 2,
            "next_task": "V5e 511360 official restore closeout",
            "allowed": official_202607_available,
            "requires_official_202607_signal": True,
        },
        {
            "priority": 3,
            "next_task": "V5e forward/paper tracking continuation",
            "allowed": True,
            "requires_official_202607_signal": False,
        },
        {
            "priority": 4,
            "next_task": "V5e threshold scan",
            "allowed": False,
            "requires_official_202607_signal": False,
        },
    ]


def _blockers(restore_status: list[dict[str, Any]]) -> list[dict[str, Any]]:
    row = restore_status[0]
    if row["official_v57f_202607_signal_available"]:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Official restore signal available."}]
    return [
        {
            "blocker_id": "official_v57f_202607_signal_unavailable",
            "severity": "forward_only",
            "status": "blocks_restore_closeout_not_tracking_or_v5f_prep",
            "description": "Local official V57f rebalance signals are unavailable beyond 2026-04-01.",
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    forward_tracking_item_count: int = 0,
    v5f_prep_item_count: int = 0,
    official_202607_restore_available: bool = False,
    accepted: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_forward_paper_continuation_v5f_prep",
        "status": status,
        "continuation_decision": decision,
        "forward_tracking_item_count": forward_tracking_item_count,
        "v5f_prep_item_count": v5f_prep_item_count,
        "official_202607_restore_available": official_202607_restore_available,
        "v5e_accepted": accepted,
        "v5e_replacement_for_v57f": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    closeout: dict[str, Any],
    tracking: dict[str, Any],
    restore_status: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    restore = restore_status[0]
    return "\n".join(
        [
            "# V5e Forward/Paper Continuation + V5f Prep",
            "",
            f"- Decision: `{decision[0]['continuation_decision']}`",
            f"- Historical closeout: `{closeout.get('historical_closeout_status')}`",
            f"- 511360 proxy-side realized PnL: {tracking.get('proxy_side_closeout_realized_pnl')}",
            f"- Official 2026-07 restore available: `{restore['official_v57f_202607_signal_available']}`",
            "- V5e accepted: `False`.",
            "- V57f core modified: `False`.",
            "",
            "## Next",
            "- Prepare V5f deployment governance / paper trading workflow packet.",
            "- Continue V5e forward/paper tracking.",
            "- Run 511360 official restore closeout only when official V57f rebalance signals are available.",
            "- Do not run V5e threshold scan.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""Working directory:
D:\\hh\\codex\\v5

Task:
V5f deployment governance / paper trading workflow packet

Goal:
Use `v5e_forward_paper_continuation_v5f_prep/current/` to prepare V5f deployment governance and paper trading workflow. Keep V5e components as not accepted. Do not modify V57f, do not scan V5e thresholds, and do not start JoinQuant.

Current decision:
`{decision["continuation_decision"]}`
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Continuation / V5f Prep Agent Rules",
            "",
            "- Continue forward/paper tracking only.",
            "- Do not mark V5e or 511360 accepted.",
            "- Do not modify V57f core.",
            "- Do not scan profit-lock thresholds.",
            "- Do not run official 511360 restore closeout without official V57f rebalance signals.",
            "- Do not start JoinQuant.",
            "",
        ]
    )


def _rebalance_dates(root: Path) -> list[str]:
    with (root / REPAIRED_RUN / "rebalance_signals.csv").open("r", encoding="utf-8-sig", newline="") as f:
        return sorted({row["trade_date"] for row in csv.DictReader(f)})


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        CLOSEOUT_DIR / "v5e_historical_closeout_summary.json",
        CLOSEOUT_DIR / "v5e_final_governance_decision.csv",
        TRACKING_DIR / "v5e_511360_forward_tracking_summary.json",
        REPAIRED_RUN / "rebalance_signals.csv",
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required continuation input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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
    result = run_v5e_forward_paper_continuation_v5f_prep()
    print(json.dumps(result, ensure_ascii=False, indent=2))
