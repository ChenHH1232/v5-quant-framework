from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_json_file


DEFAULT_OUT_DIR = Path("paper_input_preflight_checks")


@dataclass(frozen=True)
class BasketPaperInputPreflightResult:
    summary_path: Path
    report_path: Path
    status: str
    sector_count: int
    blocker_count: int
    needs_review_count: int


def run_basket_paper_input_preflight(
    *,
    config_path: Path,
    strategy_id: str,
    target_rebalance_date: str,
    as_of_date: str,
    out_dir: Path = DEFAULT_OUT_DIR,
    prior_trading_date: str | None = None,
) -> BasketPaperInputPreflightResult:
    config = _read_json(config_path)
    target_day = date.fromisoformat(target_rebalance_date)
    as_of = date.fromisoformat(as_of_date)
    prior_day = prior_trading_date or target_rebalance_date
    required_fields = [str(item) for item in config.get("portfolio", {}).get("required_fields", [])]
    sector_checks = [_check_sector(sector, target_rebalance_date, prior_day, required_fields) for sector in config.get("sectors", [])]
    blocker_count = _blocker_count(sector_checks, target_day, as_of)
    needs_review_count = _needs_review_count(sector_checks)
    status = _status(target_day, as_of, blocker_count, needs_review_count)

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "experiment_layer": "paper_trading_preparation",
        "status": status,
        "config": str(config_path),
        "as_of_date": as_of_date,
        "target_rebalance_date": target_rebalance_date,
        "prior_trading_date": prior_day,
        "target_date_is_future": target_day > as_of,
        "sector_count": len(sector_checks),
        "blocker_count": blocker_count,
        "needs_review_count": needs_review_count,
        "sector_checks": sector_checks,
        "pm_rules": [
            "Do not generate a clean paper signal after the rebalance date and call it forward evidence.",
            "Do not change frozen V5.7f factors, weights, target count, sleeves or guards in this preflight.",
            "If the target date is still in the future, missing target-date rows are expected and should be handled as pending refresh work.",
            "If stale fallback is used, it must be explicitly recorded in the paper signal log.",
        ],
        "allowed_next_action": _allowed_next_action(status),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    summary_path = out / "paper_input_preflight_summary.json"
    report_path = out / "paper_input_preflight_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return BasketPaperInputPreflightResult(summary_path, report_path, status, len(sector_checks), blocker_count, needs_review_count)


def _check_sector(sector: dict[str, Any], target_date: str, prior_date: str, required_fields: list[str]) -> dict[str, Any]:
    sector_id = str(sector.get("sector_id") or "")
    panel_path = Path(str(sector.get("panel_csv") or ""))
    price_path = Path(str(sector.get("price_csv") or ""))
    dividend_path = Path(str(sector.get("dividend_csv") or ""))
    panel_rows = read_csv_rows_if_exists(panel_path)
    price_rows = read_csv_rows_if_exists(price_path)
    dividend_rows = read_csv_rows_if_exists(dividend_path)
    target_rows = [row for row in panel_rows if _row_date(row, "trade_date") == target_date]
    latest_panel_date = _latest_date(panel_rows, "trade_date")
    latest_price_date = _latest_date(price_rows, "date")
    latest_dividend_pay_date = _latest_date(dividend_rows, "pay_date")
    missing_required_rows = [
        row
        for row in target_rows
        if any(str(row.get(field) or "").strip() == "" for field in required_fields)
    ]
    stale_rows = [
        row
        for row in target_rows
        if str(row.get("basket_stale_fundamental_fallback_fields") or "").strip()
    ]
    latest_stale_rows = [
        row
        for row in panel_rows
        if _row_date(row, "trade_date") == latest_panel_date and str(row.get("basket_stale_fundamental_fallback_fields") or "").strip()
    ]
    return {
        "sector_id": sector_id,
        "role": sector.get("role", ""),
        "panel_csv": str(panel_path),
        "price_csv": str(price_path),
        "dividend_csv": str(dividend_path),
        "panel_exists": panel_path.exists(),
        "price_exists": price_path.exists(),
        "dividend_exists": dividend_path.exists(),
        "panel_row_count": len(panel_rows),
        "price_row_count": len(price_rows),
        "dividend_row_count": len(dividend_rows),
        "latest_panel_trade_date": latest_panel_date,
        "latest_price_date": latest_price_date,
        "latest_dividend_pay_date": latest_dividend_pay_date,
        "target_panel_rows": len(target_rows),
        "target_rows_missing_required_fields": len(missing_required_rows),
        "target_stale_fallback_rows": len(stale_rows),
        "latest_stale_fallback_rows": len(latest_stale_rows),
        "price_reaches_prior_trading_date": bool(latest_price_date and latest_price_date >= prior_date),
        "required_fields": required_fields,
        "status": _sector_status(panel_path, price_path, dividend_path, target_rows, missing_required_rows, latest_price_date, prior_date),
    }


def _sector_status(
    panel_path: Path,
    price_path: Path,
    dividend_path: Path,
    target_rows: list[dict[str, str]],
    missing_required_rows: list[dict[str, str]],
    latest_price_date: str | None,
    prior_date: str,
) -> str:
    if not panel_path.exists() or not price_path.exists() or not dividend_path.exists():
        return "missing_file"
    if not target_rows:
        return "target_panel_rows_missing"
    if missing_required_rows:
        return "target_required_fields_missing"
    if not latest_price_date or latest_price_date < prior_date:
        return "price_not_refreshed_to_prior_trading_date"
    return "ready"


def _status(target_day: date, as_of: date, blocker_count: int, needs_review_count: int) -> str:
    if target_day > as_of:
        return "pending_future_data_window"
    if blocker_count:
        return "blocked_missing_or_stale_inputs"
    if needs_review_count:
        return "ready_with_review"
    return "ready_to_construct_clean_paper_signal"


def _blocker_count(sector_checks: list[dict[str, Any]], target_day: date, as_of: date) -> int:
    if target_day > as_of:
        return sum(1 for item in sector_checks if item["status"] == "missing_file")
    return sum(1 for item in sector_checks if item["status"] != "ready")


def _needs_review_count(sector_checks: list[dict[str, Any]]) -> int:
    return sum(1 for item in sector_checks if item.get("target_stale_fallback_rows") or item.get("latest_stale_fallback_rows"))


def _allowed_next_action(status: str) -> str:
    if status == "pending_future_data_window":
        return "wait_until_refresh_window_then_collect_fresh_pit_prices_dividends"
    if status == "ready_to_construct_clean_paper_signal":
        return "construct_clean_paper_signal_without_tuning"
    if status == "ready_with_review":
        return "construct_signal_only_if_stale_fallback_is_logged_and_pm_allows"
    return "repair_missing_inputs_before_signal_generation"


def _latest_date(rows: list[dict[str, str]], field: str) -> str | None:
    dates = sorted({_row_date(row, field) for row in rows if _row_date(row, field)})
    return dates[-1] if dates else None


def _row_date(row: dict[str, str], field: str) -> str:
    return str(row.get(field) or "")[:10]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# Basket Paper Input Preflight: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- As of date: `{summary['as_of_date']}`",
        f"- Target rebalance date: `{summary['target_rebalance_date']}`",
        f"- Target date is future: `{summary['target_date_is_future']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        f"- Needs review: `{summary['needs_review_count']}`",
        f"- Allowed next action: `{summary['allowed_next_action']}`",
        "",
        "## Sector Checks",
        "",
        "| Sector | Status | Latest panel | Target rows | Latest price | Dividends | Target stale | Latest stale |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summary["sector_checks"]:
        lines.append(
            f"| {item['sector_id']} | `{item['status']}` | {item['latest_panel_trade_date']} | "
            f"{item['target_panel_rows']} | {item['latest_price_date']} | {item['dividend_row_count']} | "
            f"{item['target_stale_fallback_rows']} | {item['latest_stale_fallback_rows']} |"
        )
    lines.extend(["", "## PM Rules", ""])
    for item in summary["pm_rules"]:
        lines.append(f"- {item}")
    return "\n".join(lines)
