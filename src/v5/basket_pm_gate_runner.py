from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_json_file
from v5.math_utils import to_float


DEFAULT_OUT_DIR = Path("pm_gate_packets")


@dataclass(frozen=True)
class BasketPmGateResult:
    summary_path: Path
    report_path: Path
    status: str
    blocker_count: int
    needs_review_count: int


def run_basket_pm_gate(
    *,
    strategy_id: str,
    formal_summary: Path,
    daily_summary: Path,
    overfit_summary: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    ablation_summary: Path | None = None,
    platform_packet: Path | None = None,
    paper_signal_summary: Path | None = None,
) -> BasketPmGateResult:
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)

    inputs = {
        "formal_summary": formal_summary,
        "daily_summary": daily_summary,
        "overfit_summary": overfit_summary,
        "ablation_summary": ablation_summary,
        "platform_packet": platform_packet,
        "paper_signal_summary": paper_signal_summary,
    }
    loaded = {name: _read_json_if_present(path) for name, path in inputs.items()}
    checks = _build_checks(loaded)
    blocker_count = sum(1 for check in checks if check["severity"] == "blocker")
    needs_review_count = sum(1 for check in checks if check["severity"] == "needs_review")
    status = _decide_status(loaded, blocker_count, needs_review_count)

    summary = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "status": status,
        "experiment_layer": "pm_decision_gate",
        "blocker_count": blocker_count,
        "needs_review_count": needs_review_count,
        "pass_count": sum(1 for check in checks if check["severity"] == "pass"),
        "checks": checks,
        "metrics_snapshot": _metrics_snapshot(loaded),
        "input_paths": {name: str(path) if path else None for name, path in inputs.items()},
        "pm_rules": [
            "Historical performance alone is never sufficient evidence for accepting a strategy.",
            "2021-2026 remains platform-confirmation context, not clean out-of-sample acceptance.",
            "A frozen candidate may enter platform replication or paper trading, but not live trading approval.",
            "Platform replication requires JoinQuant daily, transaction and position attribution.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    summary_path = out / "basket_pm_gate_summary.json"
    report_path = out / "basket_pm_gate_report.md"
    write_json_file(summary_path, summary)
    _write_report(report_path, summary)
    return BasketPmGateResult(summary_path, report_path, status, blocker_count, needs_review_count)


def _read_json_if_present(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _build_checks(loaded: dict[str, dict[str, Any] | None]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    formal = loaded["formal_summary"]
    daily = loaded["daily_summary"]
    overfit = loaded["overfit_summary"]
    ablation = loaded["ablation_summary"]
    platform = loaded["platform_packet"]
    paper = loaded["paper_signal_summary"]

    if formal is None:
        checks.append(_check("formal_validation", "blocker", "Formal validation summary is missing."))
    else:
        status = str(formal.get("status") or "")
        signal_count = int(to_float(formal.get("signal_count")) or 0)
        if "formal_validation_completed" not in status or signal_count <= 0:
            checks.append(_check("formal_validation", "blocker", "Formal validation did not complete with usable signals."))
        else:
            checks.append(_check("formal_validation", "pass", f"Formal validation completed with {signal_count} signals."))
        weak_years = [row for row in formal.get("weak_year_analysis", []) if row.get("diagnosis_required") == "yes"]
        if weak_years:
            years = ", ".join(str(row.get("year")) for row in weak_years)
            checks.append(_check("weak_year_analysis", "needs_review", f"Weak years still need monitoring/diagnosis: {years}."))

    if daily is None:
        checks.append(_check("local_daily_simulation", "blocker", "Local daily simulation summary is missing."))
    else:
        metrics = daily.get("metrics") or {}
        trade_count = int(to_float(daily.get("trade_count")) or 0)
        dividend_count = int(to_float(daily.get("dividend_count")) or 0)
        max_drawdown = to_float(metrics.get("max_drawdown"))
        if trade_count <= 0:
            checks.append(_check("local_daily_simulation", "blocker", "Local daily simulation produced no trades."))
        else:
            checks.append(_check("local_daily_simulation", "pass", f"Local daily simulation produced {trade_count} trades."))
        checks.extend(_rebalance_order_health_checks(daily))
        if dividend_count <= 0:
            checks.append(_check("dividend_accounting", "needs_review", "No cash dividend events were applied."))
        else:
            checks.append(_check("dividend_accounting", "pass", f"Cash dividend accounting applied {dividend_count} events."))
        if max_drawdown is not None and max_drawdown > 0.25:
            checks.append(_check("drawdown_control", "needs_review", f"Max drawdown is high: {max_drawdown:.2%}."))
        elif max_drawdown is not None:
            checks.append(_check("drawdown_control", "pass", f"Max drawdown is {max_drawdown:.2%}."))

    if overfit is None:
        checks.append(_check("overfit_audit", "blocker", "Overfit audit summary is missing."))
    else:
        blockers = int(to_float(overfit.get("blocker_count")) or 0)
        needs_review = int(to_float(overfit.get("needs_review_count")) or 0)
        if blockers > 0:
            checks.append(_check("overfit_audit", "blocker", f"Overfit audit has {blockers} blockers."))
        else:
            checks.append(_check("overfit_audit", "pass", "Overfit audit has no blockers."))
        if needs_review > 0:
            checks.append(_check("overfit_review_items", "needs_review", f"Overfit audit has {needs_review} review items."))

    if ablation is None:
        checks.append(_check("ablation", "needs_review", "Ablation summary is missing."))
    else:
        blocked_cases = [case for case in ablation.get("cases", []) if case.get("status") == "blocked"]
        if blocked_cases:
            names = ", ".join(str(case.get("case")) for case in blocked_cases[:5])
            checks.append(_check("ablation", "needs_review", f"Ablation has blocked cases: {names}."))
        else:
            checks.append(_check("ablation", "pass", "Ablation completed without blocked cases."))

    if platform is None:
        checks.append(_check("platform_replication", "needs_review", "Platform replication packet is missing."))
    else:
        platform_status = str(platform.get("status") or "")
        if platform_status == "platform_replication_passed":
            checks.append(_check("platform_replication", "pass", "Platform replication attribution passed."))
        elif platform_status == "pending_attribution":
            checks.append(_check("platform_replication", "needs_review", "Platform replication is waiting for JoinQuant exports."))
        elif platform_status in {"data_gap", "contract_mismatch"}:
            checks.append(_check("platform_replication", "blocker", f"Platform replication status is {platform_status}."))
        else:
            checks.append(_check("platform_replication", "needs_review", f"Platform replication status is {platform_status or 'unknown'}."))

    if paper is None:
        checks.append(_check("paper_trading", "needs_review", "Paper trading signal summary is missing."))
    else:
        paper_status = str(paper.get("status") or "")
        selected_count = int(to_float(paper.get("selected_count")) or to_float(paper.get("holding_count")) or 0)
        if paper_status == "pending_clean_future_rebalance":
            checks.append(_check("paper_trading", "needs_review", "Paper trading is waiting for the next clean future rebalance signal."))
        elif selected_count <= 0:
            checks.append(_check("paper_trading", "blocker", "Paper trading signal selected no stocks."))
        else:
            checks.append(_check("paper_trading", "pass", f"Paper trading signal exists with {selected_count} selected stocks."))
        if "late" in json.dumps(paper, ensure_ascii=False).lower():
            checks.append(_check("paper_recording_timing", "needs_review", "Paper signal appears to be late-recorded; next future rebalance must be clean."))

    return checks


def _check(name: str, severity: str, detail: str) -> dict[str, str]:
    return {"check": name, "severity": severity, "detail": detail}


def _rebalance_order_health_checks(daily: dict[str, Any]) -> list[dict[str, str]]:
    health = daily.get("rebalance_order_health")
    if not isinstance(health, dict):
        return [
            _check(
                "rebalance_order_health",
                "blocker",
                "Local JoinQuant-like simulation is missing rebalance_order_health; every rebalance date must prove order and holding execution before platform replication.",
            )
        ]
    signal_count = int(to_float(health.get("rebalance_signal_count")) or 0)
    missing_daily = int(to_float(health.get("missing_daily_rebalance_count")) or 0)
    no_order = int(to_float(health.get("no_order_rebalance_count")) or 0)
    no_order_no_position = int(to_float(health.get("no_order_no_position_count")) or 0)
    blocked_or_unfilled = int(to_float(health.get("blocked_or_unfilled_rebalance_count")) or 0)
    leading_empty = int(to_float(health.get("leading_no_order_no_position_count")) or 0)
    first_order = health.get("first_executed_order_date")
    first_position = health.get("first_position_date")
    blockers = []
    if signal_count <= 0:
        blockers.append("no rebalance signals were checked")
    if missing_daily > 0:
        blockers.append(f"{missing_daily} rebalance dates are missing daily rows")
    if no_order > 0:
        blockers.append(f"{no_order} rebalance dates had no executed orders")
    if no_order_no_position > 0:
        blockers.append(f"{no_order_no_position} rebalance dates had neither orders nor selected holdings")
    if blocked_or_unfilled > 0:
        blockers.append(f"{blocked_or_unfilled} rebalance dates had blocked or unfilled orders")
    if leading_empty > 0:
        blockers.append(f"{leading_empty} leading rebalance dates had no orders and no selected holdings")
    if blockers:
        return [
            _check(
                "rebalance_order_health",
                "blocker",
                "Rebalance order health requires attribution before platform replication: " + "; ".join(blockers) + ".",
            )
        ]
    return [
        _check(
            "rebalance_order_health",
            "pass",
            f"All {signal_count} rebalance signals have executable order/holding evidence; first order={first_order}, first position={first_position}.",
        )
    ]


def _decide_status(loaded: dict[str, dict[str, Any] | None], blocker_count: int, needs_review_count: int) -> str:
    if blocker_count > 0:
        return "blocked"
    platform = loaded["platform_packet"] or {}
    if platform.get("status") == "platform_replication_passed":
        return "platform_replication_passed_pending_clean_forward"
    if platform.get("status") == "pending_attribution":
        return "formal_candidate_pending_platform_exports"
    if loaded["paper_signal_summary"] is not None:
        return "formal_candidate_paper_tracking_started_needs_review" if needs_review_count else "formal_candidate_paper_tracking_started"
    return "formal_candidate_needs_pm_review"


def _metrics_snapshot(loaded: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    daily = loaded["daily_summary"] or {}
    formal = loaded["formal_summary"] or {}
    platform = loaded["platform_packet"] or {}
    metrics = daily.get("metrics") or {}
    return {
        "local_strategy_return": metrics.get("strategy_return"),
        "local_benchmark_return": metrics.get("benchmark_return"),
        "local_excess_return": metrics.get("excess_return"),
        "local_max_drawdown": metrics.get("max_drawdown"),
        "local_trade_count": daily.get("trade_count"),
        "local_dividend_count": daily.get("dividend_count"),
        "formal_signal_count": formal.get("signal_count"),
        "formal_panel_row_count": formal.get("panel_row_count"),
        "platform_status": platform.get("status"),
    }


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# Basket PM Gate: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        f"- Needs review: `{summary['needs_review_count']}`",
        "",
        "## Metrics Snapshot",
        "",
    ]
    for key, value in summary["metrics_snapshot"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks", ""])
    for check in summary["checks"]:
        lines.append(f"- `{check['severity']}` {check['check']}: {check['detail']}")
    lines.extend(
        [
            "",
            "## PM Rules",
            "",
            "- Historical performance alone is never sufficient evidence for accepting a strategy.",
            "- Platform replication and clean forward records are required before any acceptance decision.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
