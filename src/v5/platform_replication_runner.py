from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.platform_attribution_runner import (
    run_platform_attribution,
    run_position_attribution,
    run_transaction_attribution,
)


@dataclass(frozen=True)
class PlatformReplicationDecision:
    status: str
    reason: str


def run_platform_replication_packet(
    local_run_dir: Path,
    joinquant_daily_csv: Path | None,
    out_dir: Path,
    strategy_id: str,
    panel_csv: Path | None = None,
    joinquant_transaction_csv: Path | None = None,
    joinquant_position_csv: Path | None = None,
    expected_rebalance_dates: list[str] | None = None,
    final_strategy_diff_threshold: float = 0.01,
    max_strategy_diff_threshold: float = 0.03,
) -> Path:
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)

    local_daily_csv = local_run_dir / "daily_returns.csv"
    local_signals_csv = local_run_dir / "rebalance_signals.csv"
    local_trades_csv = local_run_dir / "trades.csv"
    local_holdings_csv = local_run_dir / "holdings.csv"
    local_dividends_csv = local_run_dir / "dividends.csv"
    local_order_health_csv = local_run_dir / "rebalance_order_health.csv"

    signal_dates = _load_dates(local_signals_csv, "trade_date")
    local_order_health_summary = _summarize_local_order_health(local_order_health_csv)
    platform_rebalance_dates = _derive_platform_rebalance_dates(
        joinquant_transaction_csv,
        expected_rebalance_dates,
    )
    panel_dates = _load_dates(panel_csv, "trade_date") if panel_csv else []

    coverage = _coverage_check(
        panel_dates=panel_dates,
        signal_dates=signal_dates,
        platform_rebalance_dates=platform_rebalance_dates,
    )

    outputs: dict[str, str] = {}
    daily_summary: dict[str, Any] | None = None
    transaction_summary: dict[str, Any] | None = None
    position_summary: dict[str, Any] | None = None
    position_rebalance_summary: dict[str, Any] | None = None

    if joinquant_daily_csv is not None:
        daily_report = run_platform_attribution(
            local_daily_csv,
            joinquant_daily_csv,
            out_dir,
            strategy_id,
            local_rebalance_signals_csv=local_signals_csv,
            local_trades_csv=local_trades_csv,
            local_dividends_csv=local_dividends_csv,
        )
        outputs["daily_attribution_report"] = str(daily_report)
        daily_summary = _read_json(daily_report.parent / "platform_attribution_summary.json")

    if joinquant_transaction_csv is not None:
        transaction_report = run_transaction_attribution(
            joinquant_transaction_csv,
            local_trades_csv,
            out_dir,
            f"{strategy_id}_transactions",
        )
        outputs["transaction_attribution_report"] = str(transaction_report)
        transaction_summary = _read_json(transaction_report.parent / "transaction_attribution_summary.json")

    if joinquant_position_csv is not None:
        position_report = run_position_attribution(
            joinquant_position_csv,
            local_holdings_csv,
            out_dir,
            f"{strategy_id}_positions",
        )
        outputs["position_attribution_report"] = str(position_report)
        position_summary = _read_json(position_report.parent / "position_attribution_summary.json")
        position_rebalance_summary = _summarize_position_rebalance_dates(
            position_report.parent / "position_comparison_summary.csv",
        )

    decision = _decide(
        coverage=coverage,
        daily_summary=daily_summary,
        transaction_summary=transaction_summary,
        position_rebalance_summary=position_rebalance_summary,
        local_order_health_summary=local_order_health_summary,
        final_strategy_diff_threshold=final_strategy_diff_threshold,
        max_strategy_diff_threshold=max_strategy_diff_threshold,
    )

    packet = {
        "strategy_id": strategy_id,
        "status": decision.status,
        "reason": decision.reason,
        "local_run_dir": str(local_run_dir),
        "panel_csv": str(panel_csv) if panel_csv else None,
        "joinquant_daily_csv": str(joinquant_daily_csv) if joinquant_daily_csv else None,
        "joinquant_transaction_csv": str(joinquant_transaction_csv) if joinquant_transaction_csv else None,
        "joinquant_position_csv": str(joinquant_position_csv) if joinquant_position_csv else None,
        "coverage": coverage,
        "local_rebalance_order_health": local_order_health_summary,
        "daily_summary": _compact_daily(daily_summary),
        "transaction_summary": _compact_transaction(transaction_summary),
        "position_rebalance_summary": position_rebalance_summary,
        "thresholds": {
            "final_strategy_diff": final_strategy_diff_threshold,
            "max_strategy_diff": max_strategy_diff_threshold,
        },
        "outputs": outputs,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(out / "platform_replication_packet.json", packet)
    _write_report(out / "platform_replication_packet.md", packet)
    return out / "platform_replication_packet.md"


def _derive_platform_rebalance_dates(transaction_csv: Path | None, expected_dates: list[str] | None) -> list[str]:
    if expected_dates:
        return sorted({date[:10] for date in expected_dates if date})
    if transaction_csv is None or not transaction_csv.exists():
        return []
    rows = _read_joinquant_transaction_dates(transaction_csv)
    return sorted(set(rows))


def _read_joinquant_transaction_dates(path: Path) -> list[str]:
    encodings = ["utf-8-sig", "gb18030", "gbk"]
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.reader(handle)
                next(reader, None)
                return [row[0][:10] for row in reader if row and row[0]]
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"failed to read transaction CSV: {path}")


def _coverage_check(panel_dates: list[str], signal_dates: list[str], platform_rebalance_dates: list[str]) -> dict[str, Any]:
    expected = sorted(set(platform_rebalance_dates))
    panel_set = set(panel_dates)
    signal_set = set(signal_dates)
    missing_panel = [day for day in expected if panel_dates and day not in panel_set]
    missing_signals = [day for day in expected if day not in signal_set]
    latest_expected = expected[-1] if expected else None
    latest_signal = signal_dates[-1] if signal_dates else None
    missing_last_signal = bool(latest_expected and latest_signal and latest_signal < latest_expected)
    return {
        "expected_rebalance_dates": expected,
        "panel_date_count": len(set(panel_dates)),
        "signal_date_count": len(set(signal_dates)),
        "latest_expected_rebalance_date": latest_expected,
        "latest_local_signal_date": latest_signal,
        "missing_panel_dates": missing_panel,
        "missing_signal_dates": missing_signals,
        "missing_last_signal": missing_last_signal,
        "passed": not missing_panel and not missing_signals and not missing_last_signal,
    }


def _summarize_position_rebalance_dates(position_summary_csv: Path) -> dict[str, Any]:
    if not position_summary_csv.exists():
        return {"available": False}
    rows = _read_csv(position_summary_csv)
    local_rows = [row for row in rows if _to_int(row.get("local_count")) > 0]
    code_mismatch_rows = [
        row
        for row in local_rows
        if _to_int(row.get("only_jq_count")) > 0 or _to_int(row.get("only_local_count")) > 0
    ]
    return {
        "available": True,
        "local_rebalance_dates_checked": len(local_rows),
        "code_mismatch_dates": len(code_mismatch_rows),
        "max_abs_share_diff": max((_to_float(row.get("amount_abs_diff")) for row in local_rows), default=0.0),
        "max_abs_weight_diff": max((_to_float(row.get("weight_abs_diff")) for row in local_rows), default=0.0),
    }


def _summarize_local_order_health(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "available": False,
            "passed": False,
            "reason": "missing rebalance_order_health.csv",
            "blocker_statuses": ["missing_rebalance_order_health"],
        }
    rows = _read_csv(path)
    status_counts: dict[str, int] = {}
    leading_no_order_no_position_count = 0
    first_executed_order_date = None
    first_position_date = None
    still_leading = True
    blocker_rows: list[dict[str, Any]] = []
    blocker_statuses = {
        "missing_daily_row",
        "no_selected_stocks",
        "no_order_no_position",
        "order_blocked_or_unfilled",
        "ordered_but_no_position",
    }
    for row in rows:
        status = str(row.get("order_health_status") or "")
        status_counts[status] = status_counts.get(status, 0) + 1
        day = str(row.get("trade_date") or "")[:10]
        executed_count = _to_int(row.get("executed_order_count"))
        held_count = _to_int(row.get("holding_count_after_rebalance"))
        selected_count = _to_int(row.get("selected_count"))
        if executed_count > 0 and first_executed_order_date is None:
            first_executed_order_date = day
        if held_count > 0 and first_position_date is None:
            first_position_date = day
        if still_leading and executed_count == 0 and held_count == 0:
            leading_no_order_no_position_count += 1
        else:
            still_leading = False
        if status in blocker_statuses or (selected_count > 0 and held_count <= 0):
            blocker_rows.append(
                {
                    "trade_date": day,
                    "status": status,
                    "selected_count": selected_count,
                    "executed_order_count": executed_count,
                    "holding_count_after_rebalance": held_count,
                }
            )
    passed = bool(rows) and not blocker_rows and leading_no_order_no_position_count == 0
    return {
        "available": True,
        "passed": passed,
        "reason": "passed" if passed else "local rebalance order health failed",
        "rebalance_signal_count": len(rows),
        "status_counts": status_counts,
        "blocker_count": len(blocker_rows),
        "blocker_rows": blocker_rows[:20],
        "leading_no_order_no_position_count": leading_no_order_no_position_count,
        "first_executed_order_date": first_executed_order_date,
        "first_position_date": first_position_date,
    }


def _decide(
    coverage: dict[str, Any],
    daily_summary: dict[str, Any] | None,
    transaction_summary: dict[str, Any] | None,
    position_rebalance_summary: dict[str, Any] | None,
    local_order_health_summary: dict[str, Any],
    final_strategy_diff_threshold: float,
    max_strategy_diff_threshold: float,
) -> PlatformReplicationDecision:
    if not coverage["passed"]:
        return PlatformReplicationDecision("data_gap", "local PIT panel or rebalance signals do not cover platform rebalance dates")
    if not local_order_health_summary.get("passed"):
        return PlatformReplicationDecision("data_gap", "local rebalance order health is missing or failed")
    if daily_summary is None or transaction_summary is None or position_rebalance_summary is None:
        return PlatformReplicationDecision("pending_attribution", "daily, transaction, and position attribution are all required")

    final_diff = abs(float(daily_summary.get("final_strategy_diff") or 0.0))
    max_diff = abs(float(daily_summary.get("max_abs_strategy_diff") or 0.0))
    if final_diff > final_strategy_diff_threshold or max_diff > max_strategy_diff_threshold:
        return PlatformReplicationDecision("pending_attribution", "daily NAV residual exceeds configured threshold")

    if int(transaction_summary.get("matched_key_count") or 0) <= 0:
        return PlatformReplicationDecision("contract_mismatch", "no matched transaction keys")

    if int(position_rebalance_summary.get("code_mismatch_dates") or 0) > 0:
        return PlatformReplicationDecision("contract_mismatch", "position code sets differ on local rebalance dates")

    return PlatformReplicationDecision("platform_replication_passed", "daily, transaction, and position attribution passed with minor residuals")


def _compact_daily(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "matched_days": summary.get("matched_days"),
        "final_strategy_diff": summary.get("final_strategy_diff"),
        "max_abs_strategy_diff": summary.get("max_abs_strategy_diff"),
        "final_benchmark_diff": summary.get("final_benchmark_diff"),
        "max_abs_benchmark_diff": summary.get("max_abs_benchmark_diff"),
        "local_rebalance_count": (summary.get("local_execution_diagnostics") or {}).get("rebalance_count"),
        "local_trade_count": (summary.get("local_execution_diagnostics") or {}).get("trade_count"),
    }


def _compact_transaction(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "joinquant_rows": summary.get("joinquant_rows"),
        "local_rows": summary.get("local_rows"),
        "matched_key_count": summary.get("matched_key_count"),
        "joinquant_only_count": summary.get("joinquant_only_count"),
        "local_only_count": summary.get("local_only_count"),
    }


def _load_dates(path: Path | None, field: str) -> list[str]:
    if path is None or not path.exists():
        return []
    return sorted({row[field][:10] for row in _read_csv(path) if row.get(field)})


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_report(path: Path, packet: dict[str, Any]) -> None:
    lines = [
        f"# Platform Replication Packet: {packet['strategy_id']}",
        "",
        f"- Status: `{packet['status']}`",
        f"- Reason: {packet['reason']}",
        f"- Latest expected rebalance: `{packet['coverage']['latest_expected_rebalance_date']}`",
        f"- Latest local signal: `{packet['coverage']['latest_local_signal_date']}`",
        f"- Missing panel dates: `{';'.join(packet['coverage']['missing_panel_dates'])}`",
        f"- Missing signal dates: `{';'.join(packet['coverage']['missing_signal_dates'])}`",
        "",
        "## Local Rebalance Order Health",
        "",
        f"- Summary: `{packet['local_rebalance_order_health']}`",
        "",
        "## Daily",
        "",
        f"- Summary: `{packet['daily_summary']}`",
        "",
        "## Transactions",
        "",
        f"- Summary: `{packet['transaction_summary']}`",
        "",
        "## Positions",
        "",
        f"- Rebalance summary: `{packet['position_rebalance_summary']}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _to_float(value: Any) -> float:
    try:
        if value in {None, ""}:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    return int(round(_to_float(value)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-platform-replication-packet")
    parser.add_argument("local_run_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("platform_replication_packets"))
    parser.add_argument("--strategy-id", default="bank_value_15y")
    parser.add_argument("--panel-csv", type=Path)
    parser.add_argument("--joinquant-daily-csv", type=Path)
    parser.add_argument("--joinquant-transaction-csv", type=Path)
    parser.add_argument("--joinquant-position-csv", type=Path)
    parser.add_argument("--expected-rebalance-date", action="append", default=[])
    parser.add_argument("--final-strategy-diff-threshold", type=float, default=0.01)
    parser.add_argument("--max-strategy-diff-threshold", type=float, default=0.03)
    args = parser.parse_args(argv)
    print(
        run_platform_replication_packet(
            args.local_run_dir,
            args.joinquant_daily_csv,
            args.out,
            args.strategy_id,
            panel_csv=args.panel_csv,
            joinquant_transaction_csv=args.joinquant_transaction_csv,
            joinquant_position_csv=args.joinquant_position_csv,
            expected_rebalance_dates=args.expected_rebalance_date,
            final_strategy_diff_threshold=args.final_strategy_diff_threshold,
            max_strategy_diff_threshold=args.max_strategy_diff_threshold,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
