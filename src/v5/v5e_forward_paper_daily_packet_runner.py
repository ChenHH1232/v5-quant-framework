from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARTIFACT_DIR = Path("v5f_paper_workflow_artifacts") / "current"
PROFIT_LOCK_DIR = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current"
PROXY_TRACKING_DIR = Path("v5e_511360_forward_paper_tracking") / "current"
SIGNAL_PATH = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
    / "rebalance_signals.csv"
)
OUT_DIR = Path("v5e_forward_paper_daily_packet") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_forward_paper_daily_packet(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_forward_daily_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_forward_daily_summary.json", summary)
        return summary

    artifact_summary = _read_json(root / ARTIFACT_DIR / "v5f_paper_artifact_summary.json")
    profit_lock = _read_json(root / PROFIT_LOCK_DIR / "v5e_profit_lock_forward_paper_summary.json")
    proxy = _read_json(root / PROXY_TRACKING_DIR / "v5e_511360_forward_tracking_summary.json")
    signal_info = _rebalance_signal_info(root / SIGNAL_PATH)

    paper_date = "2026-07-29"
    restore_available = signal_info["latest_rebalance_signal_date"] >= "2026-07-01"
    daily_log = _daily_signal_log(paper_date, profit_lock, proxy, restore_available)
    v57f_snapshot = _v57f_snapshot(paper_date, signal_info, restore_available)
    profit_observation = _profit_observation(paper_date, profit_lock)
    proxy_observation = _proxy_observation(paper_date, proxy, restore_available)
    governance_audit = _governance_audit(paper_date)
    restore_status = _restore_status(signal_info, restore_available)
    next_queue = _next_queue(restore_available)
    blockers_out = _blockers(restore_available, signal_info)

    _write_csv(out / "v5e_forward_daily_signal_log.csv", daily_log)
    _write_csv(out / "v5e_forward_daily_v57f_snapshot.csv", v57f_snapshot)
    _write_csv(out / "v5e_forward_daily_profit_lock_observation.csv", profit_observation)
    _write_csv(out / "v5e_forward_daily_511360_proxy_observation.csv", proxy_observation)
    _write_csv(out / "v5e_forward_daily_governance_audit.csv", governance_audit)
    _write_csv(out / "v5e_forward_daily_511360_restore_status.csv", restore_status)
    _write_csv(out / "v5e_forward_daily_next_queue.csv", next_queue)
    _write_csv(out / "v5e_forward_daily_blockers.csv", blockers_out)
    (out / "v5e_forward_daily_next_prompt.md").write_text(_next_prompt(restore_available), encoding="utf-8")
    (out / "v5e_forward_daily_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_forward_daily_report.md").write_text(
        _report(artifact_summary, profit_lock, proxy, signal_info, restore_available),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5e_forward_paper_daily_packet",
        "forward_tracking_recorded_official_restore_pending" if not restore_available else "official_restore_closeout_ready",
        [],
        paper_date=paper_date,
        latest_rebalance_signal_date=signal_info["latest_rebalance_signal_date"],
        official_202607_restore_available=restore_available,
        daily_log_rows=len(daily_log),
    )
    _write_json(out / "v5e_forward_daily_summary.json", summary)
    return summary


def _rebalance_signal_info(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    dates = sorted({row["trade_date"] for row in rows if row.get("trade_date")})
    latest = dates[-1] if dates else ""
    latest_rows = [row for row in rows if row.get("trade_date") == latest]
    return {
        "latest_rebalance_signal_date": latest,
        "latest_signal_row_count": len(latest_rows),
        "latest_selected_count": latest_rows[0].get("selected_count", "") if latest_rows else "",
        "official_202607_signal_required": True,
    }


def _daily_signal_log(
    paper_date: str,
    profit_lock: dict[str, Any],
    proxy: dict[str, Any],
    restore_available: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "paper_date": paper_date,
            "cycle_id": "forward_202607",
            "candidate_id": "v5e_profit_lock_main_20pct_sell50",
            "signal_type": "profit_lock_forward_status",
            "code": "",
            "sleeve_id": "",
            "visible_after_close": True,
            "paper_action": "continue_tracking_waiting_forward_records",
            "execution_proxy": "daily_t_plus_1_open_or_approved_vwap_proxy",
            "status": profit_lock.get("tracking_status", ""),
            "notes": "Not accepted; threshold remains pre-registered.",
        },
        {
            "paper_date": paper_date,
            "cycle_id": "forward_202607",
            "candidate_id": "v5e_511360_cash_proxy",
            "signal_type": "official_restore_status",
            "code": "511360",
            "sleeve_id": "cash_proxy",
            "visible_after_close": True,
            "paper_action": "wait_for_official_v57f_restore_signal" if not restore_available else "run_official_restore_closeout",
            "execution_proxy": "proxy_side_tracking_done",
            "status": proxy.get("pm_gate_decision", ""),
            "notes": "No acceptance or live approval.",
        },
    ]


def _v57f_snapshot(
    paper_date: str,
    signal_info: dict[str, Any],
    restore_available: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "paper_date": paper_date,
            "rebalance_cycle": signal_info["latest_rebalance_signal_date"],
            "holdings_hash": "not_computed_in_daily_packet",
            "target_count": signal_info["latest_selected_count"],
            "signal_row_count": signal_info["latest_signal_row_count"],
            "v57f_core_unchanged": True,
            "official_202607_signal_available": restore_available,
            "snapshot_status": "recorded_from_local_repaired_signal_path",
        }
    ]


def _profit_observation(paper_date: str, profit_lock: dict[str, Any]) -> list[dict[str, Any]]:
    status = profit_lock.get("candidate_status", {})
    return [
        {
            "paper_date": paper_date,
            "candidate_id": "v5e_profit_lock_main_20pct_sell50",
            "threshold": profit_lock.get("profit_lock_threshold", 0.2),
            "sell_fraction": profit_lock.get("sell_fraction", 0.5),
            "threshold_status": status.get("threshold_status", "pre_registered_not_optimized"),
            "vwap_adjusted_delta_vs_v57f_baseline": status.get("vwap_adjusted_delta_vs_v57f_baseline", ""),
            "cash_drag_delta_vs_baseline": status.get("cash_drag_delta_vs_baseline", ""),
            "accepted": False,
            "live_trading_approved": False,
            "observation_status": "forward_tracking_ready_waiting_new_records",
        }
    ]


def _proxy_observation(
    paper_date: str,
    proxy: dict[str, Any],
    restore_available: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "paper_date": paper_date,
            "candidate_id": "v5e_511360_cash_proxy",
            "proxy_code": "511360",
            "restore_closeout_count": proxy.get("restore_closeout_count", ""),
            "proxy_side_closeout_realized_pnl": proxy.get("proxy_side_closeout_realized_pnl", ""),
            "official_v57f_restore_available": restore_available,
            "accepted": False,
            "live_trading_approved": False,
            "observation_status": "official_restore_pending" if not restore_available else "official_restore_ready",
        }
    ]


def _governance_audit(paper_date: str) -> list[dict[str, Any]]:
    return [
        {
            "paper_date": paper_date,
            "audit_packet_id": "v5e_forward_daily_20260729",
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "accepted": False,
            "deployment_approved": False,
            "live_trading_approved": False,
            "joinquant_started": False,
            "network_fetch_started": False,
            "audit_status": "pass",
        }
    ]


def _restore_status(signal_info: dict[str, Any], restore_available: bool) -> list[dict[str, Any]]:
    return [
        {
            "restore_item": "511360_official_restore_closeout",
            "latest_local_v57f_rebalance_signal": signal_info["latest_rebalance_signal_date"],
            "required_signal": "2026-07-01_or_later_official_v57f_rebalance",
            "official_restore_available": restore_available,
            "allowed_to_run_closeout": restore_available,
            "historical_backtest_blocker": False,
            "forward_only_status": "pending" if not restore_available else "ready",
        }
    ]


def _next_queue(restore_available: bool) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "Continue V5e forward/paper tracking", "allowed": True, "requires_official_rebalance_signal": False},
        {"priority": 2, "next_task": "511360 official restore closeout", "allowed": restore_available, "requires_official_rebalance_signal": True},
        {"priority": 3, "next_task": "V5f deployment governance review", "allowed": False, "requires_official_rebalance_signal": False},
        {"priority": 4, "next_task": "V5e threshold scan", "allowed": False, "requires_official_rebalance_signal": False},
    ]


def _blockers(restore_available: bool, signal_info: dict[str, Any]) -> list[dict[str, Any]]:
    if restore_available:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Official restore closeout may proceed."}]
    return [
        {
            "blocker_id": "official_v57f_restore_signal_unavailable",
            "severity": "forward_only",
            "status": "blocks_restore_closeout_only",
            "description": f"Latest local V57f rebalance signal is {signal_info['latest_rebalance_signal_date']}; 2026-07 official restore signal not available.",
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    paper_date: str = "",
    latest_rebalance_signal_date: str = "",
    official_202607_restore_available: bool = False,
    daily_log_rows: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_forward_paper_daily_packet",
        "status": status,
        "paper_daily_decision": decision,
        "paper_date": paper_date,
        "latest_rebalance_signal_date": latest_rebalance_signal_date,
        "official_202607_restore_available": official_202607_restore_available,
        "daily_log_rows": daily_log_rows,
        "v5e_accepted": False,
        "deployment_approved": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    artifact_summary: dict[str, Any],
    profit_lock: dict[str, Any],
    proxy: dict[str, Any],
    signal_info: dict[str, Any],
    restore_available: bool,
) -> str:
    return "\n".join(
        [
            "# V5e Forward/Paper Daily Packet",
            "",
            f"- Artifact source status: `{artifact_summary['status']}`",
            f"- Profit-lock candidate: `{profit_lock.get('tracking_status', '')}`",
            f"- 511360 proxy status: `{proxy.get('pm_gate_decision', '')}`",
            f"- Latest local V57f rebalance signal: `{signal_info['latest_rebalance_signal_date']}`",
            f"- 2026-07 official restore available: `{restore_available}`",
            "- Accepted: `False`.",
            "- Deployment approved: `False`.",
            "- Live trading approved: `False`.",
            "",
            "## Decision",
            "- Continue V5e forward/paper tracking.",
            "- Keep 511360 official restore closeout pending until the official V57f rebalance signal is locally available.",
            "- Keep deployment approval and threshold scan blocked.",
            "",
        ]
    )


def _next_prompt(restore_available: bool) -> str:
    if restore_available:
        task = "V5e 511360 official restore closeout"
        goal = "Use the newly available official V57f rebalance signal to close out the 511360 restore leg. Do not approve live trading or mark accepted."
    else:
        task = "Continue V5e forward/paper tracking"
        goal = "Record the next forward/paper observation packet. Do not run 511360 official restore closeout until an official V57f rebalance signal is locally available."
    return f"""Working directory:
D:\\hh\\codex\\v5

Task:
{task}

Goal:
{goal}
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Forward Daily Agent Rules",
            "",
            "- Forward/paper tracking only.",
            "- Do not mark V5e or 511360 accepted.",
            "- Do not approve deployment or live trading.",
            "- Do not scan thresholds.",
            "- Do not modify V57f core.",
            "- Do not start JoinQuant.",
            "- Do not run 511360 official restore closeout without an official V57f rebalance signal.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        ARTIFACT_DIR / "v5f_paper_artifact_summary.json",
        PROFIT_LOCK_DIR / "v5e_profit_lock_forward_paper_summary.json",
        PROXY_TRACKING_DIR / "v5e_511360_forward_tracking_summary.json",
        SIGNAL_PATH,
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
    result = run_v5e_forward_paper_daily_packet()
    print(json.dumps(result, ensure_ascii=False, indent=2))
