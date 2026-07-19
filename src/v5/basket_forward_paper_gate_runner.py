from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows, write_json_file


DEFAULT_OUT_DIR = Path("paper_trading_gates")


@dataclass(frozen=True)
class BasketForwardPaperGateResult:
    summary_path: Path
    report_path: Path
    status: str
    next_rebalance_date: str | None


def prepare_basket_forward_paper_gate(
    *,
    strategy_id: str,
    config_path: Path,
    current_paper_summary: Path,
    pm_gate_summary: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    as_of_date: str | None = None,
    next_rebalance_date: str | None = None,
    trading_calendar_csv: Path | None = None,
) -> BasketForwardPaperGateResult:
    as_of = date.fromisoformat(as_of_date or date.today().isoformat())
    config = _read_json(config_path)
    paper = _read_json(current_paper_summary)
    pm_gate = _read_json(pm_gate_summary)
    last_signal_date = _latest_signal_date(paper)
    next_quarter_start = _next_quarter_start(last_signal_date)
    resolved_next_date = next_rebalance_date or _resolve_next_trading_day(next_quarter_start, trading_calendar_csv)

    status = "pending_clean_future_rebalance"
    if resolved_next_date and date.fromisoformat(resolved_next_date) <= as_of:
        status = "blocked_rebalance_date_not_future"

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "status": status,
        "experiment_layer": "paper_trading_preparation",
        "as_of_date": as_of.isoformat(),
        "last_recorded_signal_date": last_signal_date,
        "last_record_type": _record_type(paper, last_signal_date),
        "next_quarter_start": next_quarter_start,
        "next_rebalance_date": resolved_next_date,
        "next_rebalance_date_source": _date_source(next_rebalance_date, trading_calendar_csv, resolved_next_date),
        "included_sleeves": [str(sector.get("sector_id") or "") for sector in config.get("sectors", [])],
        "pm_gate_status": pm_gate.get("status"),
        "pm_gate_needs_review_count": pm_gate.get("needs_review_count"),
        "required_inputs_before_signal": [
            "Fresh PIT sector panels for all included sleeves, with every row visible on or before the signal generation date.",
            "Updated daily unadjusted open/close prices through the prior trading day for low-volatility calculation.",
            "Updated cash dividend files with 20% tax-adjusted net_cash_per_share where applicable.",
            "Explicit stale-fallback audit for any bank quality field; refreshed PIT bank fundamentals are preferred.",
            "Trading calendar confirmation for the next rebalance date.",
        ],
        "execution_rules": [
            "Do not change V5.7f factor weights, sector weights, target count or guards.",
            "Do not use 2021-2026 platform-confirmation results to tune parameters.",
            "Generate the paper signal on or before the actual rebalance date, not after the fact.",
            "Record selected stocks, sleeve weights, factor fields, stale fallback usage and data sources.",
            "After JoinQuant exports are available, run platform daily/transaction/position attribution before any promotion.",
        ],
        "blocked_actions": [
            "accepted_strategy",
            "live_trading_approved",
            "return_tuning",
            "adding_new_sleeves_without_research_pit_validation",
        ],
        "recommended_next_commands": _command_templates(strategy_id, resolved_next_date),
        "input_paths": {
            "config": str(config_path),
            "current_paper_summary": str(current_paper_summary),
            "pm_gate_summary": str(pm_gate_summary),
            "trading_calendar_csv": str(trading_calendar_csv) if trading_calendar_csv else None,
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    summary_path = out / "forward_paper_gate_summary.json"
    report_path = out / "forward_paper_gate_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return BasketForwardPaperGateResult(summary_path, report_path, status, resolved_next_date)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _latest_signal_date(paper_summary: dict[str, Any]) -> str:
    signals_path = paper_summary.get("signals_path")
    if signals_path:
        path = Path(str(signals_path))
        if path.exists():
            dates = sorted({str(row.get("trade_date") or "")[:10] for row in read_csv_rows(path) if row.get("trade_date")})
            if dates:
                return dates[-1]
    signal_date = str(paper_summary.get("signal_date") or "")[:10]
    if signal_date:
        return signal_date
    raise ValueError("paper summary must include signals_path with trade_date rows or signal_date")


def _next_quarter_start(last_signal_date: str) -> str:
    day = date.fromisoformat(last_signal_date)
    quarter_months = [1, 4, 7, 10]
    for month in quarter_months:
        candidate = date(day.year, month, 1)
        if candidate > day:
            return candidate.isoformat()
    return date(day.year + 1, 1, 1).isoformat()


def _resolve_next_trading_day(next_quarter_start: str, trading_calendar_csv: Path | None) -> str | None:
    if trading_calendar_csv is None or not trading_calendar_csv.exists():
        return None
    rows = read_csv_rows(trading_calendar_csv)
    candidates = []
    for row in rows:
        raw = row.get("trade_date") or row.get("date") or row.get("day")
        if not raw:
            continue
        day = str(raw)[:10]
        if day >= next_quarter_start:
            candidates.append(day)
    return min(candidates) if candidates else None


def _looks_late_recorded(paper_summary: dict[str, Any]) -> bool:
    text = json.dumps(paper_summary, ensure_ascii=False).lower()
    return "late" in text or "initialization" in text or "初始化" in text


def _record_type(paper_summary: dict[str, Any], last_signal_date: str) -> str:
    if _looks_late_recorded(paper_summary):
        return "late_recorded_initialization"
    created_at = str(paper_summary.get("created_at_utc") or "")[:10]
    if created_at and created_at > last_signal_date:
        return "late_recorded_initialization"
    return "clean_or_unknown"


def _date_source(manual_date: str | None, calendar: Path | None, resolved: str | None) -> str:
    if manual_date:
        return "manual_override"
    if calendar and resolved:
        return "trading_calendar_csv"
    return "pending_trading_calendar_confirmation"


def _command_templates(strategy_id: str, next_rebalance_date: str | None) -> dict[str, str]:
    signal_date = next_rebalance_date or "<confirmed_next_rebalance_date>"
    return {
        "construct_clean_signal": (
            "python -m v5.cli construct-dividend-low-vol-fcf-basket "
            "--config config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_paper_<yyyymm>.json "
            f"--out paper_trading_signals/{strategy_id}/{signal_date}"
        ),
        "run_local_monitoring": (
            "python -m v5.cli daily-backtest-dividend-low-vol-fcf-basket "
            "--config config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_paper_<yyyymm>.json "
            f"--signals paper_trading_signals/{strategy_id}/{signal_date}/basket_rebalance_signals.csv "
            f"--out paper_trading_signals/{strategy_id}/{signal_date}/local_monitoring"
        ),
        "refresh_pm_gate_after_signal": (
            "python -m v5.cli basket-pm-gate "
            f"--strategy-id {strategy_id} "
            "--formal-summary validation_formal_v57f_etf/<strategy>/basket_formal_validation_summary.json "
            "--daily-summary local_daily_backtests_v57f_etf/<strategy>/summary.json "
            "--overfit-summary validation_overfit_v57f_etf/<strategy>/overfit_audit_summary.json "
            "--ablation-summary validation_ablation_v57f_etf/<strategy>/basket_ablation_summary.json "
            "--platform-packet platform_replication_packets_v57f_etf/<strategy>/platform_replication_packet.json "
            f"--paper-signal-summary paper_trading_signals/{strategy_id}/{signal_date}/basket_construction_summary.json "
            "--out pm_gate_packets_v57f"
        ),
    }


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# Forward Paper Gate: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- As of date: `{summary['as_of_date']}`",
        f"- Last recorded signal date: `{summary['last_recorded_signal_date']}`",
        f"- Last record type: `{summary['last_record_type']}`",
        f"- Next quarter start: `{summary['next_quarter_start']}`",
        f"- Next rebalance date: `{summary['next_rebalance_date']}`",
        f"- Date source: `{summary['next_rebalance_date_source']}`",
        f"- PM gate status: `{summary['pm_gate_status']}`",
        "",
        "## Required Inputs",
        "",
    ]
    for item in summary["required_inputs_before_signal"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Execution Rules", ""])
    for item in summary["execution_rules"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Blocked Actions", ""])
    for item in summary["blocked_actions"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Command Templates", ""])
    for name, command in summary["recommended_next_commands"].items():
        lines.append(f"- `{name}`: `{command}`")
    return "\n".join(lines)
