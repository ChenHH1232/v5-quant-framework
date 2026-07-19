from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re


def run_platform_attribution(
    local_daily_csv: Path,
    joinquant_daily_csv: Path,
    out_dir: Path,
    strategy_id: str = "bank_value_15y",
    local_rebalance_signals_csv: Path | None = None,
    local_trades_csv: Path | None = None,
    local_dividends_csv: Path | None = None,
) -> Path:
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    local = _load_local(local_daily_csv)
    jq = _load_joinquant(joinquant_daily_csv)
    rows = []
    for day in sorted(set(local) & set(jq)):
        lrow = local[day]
        jrow = jq[day]
        local_strategy = float(lrow["strategy_nav"]) - 1.0
        local_benchmark = float(lrow["benchmark_nav"]) - 1.0
        jq_strategy = jrow["strategy_return"]
        jq_benchmark = jrow["benchmark_return"]
        rows.append(
            {
                "date": day,
                "local_strategy_return": local_strategy,
                "joinquant_strategy_return": jq_strategy,
                "strategy_diff": local_strategy - jq_strategy,
                "local_benchmark_return": local_benchmark,
                "joinquant_benchmark_return": jq_benchmark,
                "benchmark_diff": local_benchmark - jq_benchmark,
                "local_cash_weight": lrow.get("cash_weight", ""),
                "local_defensive_state": lrow.get("defensive_state", ""),
            }
        )
    _write_csv(out / "daily_attribution.csv", list(rows[0].keys()) if rows else [], rows)
    diagnostics = _local_execution_diagnostics(local, local_rebalance_signals_csv, local_trades_csv, local_dividends_csv)
    _write_json(out / "local_execution_diagnostics.json", diagnostics)
    summary = _summary(rows, local_daily_csv, joinquant_daily_csv, strategy_id, diagnostics)
    _write_json(out / "platform_attribution_summary.json", summary)
    _write_report(out / "platform_attribution_report.md", summary)
    return out / "platform_attribution_report.md"


def run_position_attribution(
    joinquant_position_csv: Path,
    local_holdings_csv: Path,
    out_dir: Path,
    strategy_id: str = "bank_value_15y",
) -> Path:
    out = out_dir / f"{strategy_id}_positions"
    out.mkdir(parents=True, exist_ok=True)
    jq_positions, jq_cash_by_date, jq_value_by_date, encoding = _load_joinquant_positions(joinquant_position_csv)
    local_positions = _load_local_holdings(local_holdings_csv)
    normalized_path = out / "normalized_joinquant_positions.csv"
    comparison_path = out / "position_comparison_summary.csv"
    diff_path = out / "position_common_diffs.csv"
    _write_csv(normalized_path, list(jq_positions[0].keys()) if jq_positions else [], jq_positions)
    summary_rows, diff_rows = _compare_positions(jq_positions, local_positions, jq_cash_by_date, jq_value_by_date)
    _write_csv(comparison_path, list(summary_rows[0].keys()) if summary_rows else [], summary_rows)
    _write_csv(diff_path, list(diff_rows[0].keys()) if diff_rows else [], diff_rows)
    summary = {
        "strategy_id": strategy_id,
        "joinquant_position_csv": str(joinquant_position_csv),
        "local_holdings_csv": str(local_holdings_csv),
        "encoding": encoding,
        "joinquant_position_rows": len(jq_positions),
        "joinquant_dates": len({row["trade_date"] for row in jq_positions}),
        "local_dates": len({row["trade_date"] for row in local_positions}),
        "date_range": _date_range(summary_rows),
        "perfect_position_dates": sum(
            1
            for row in summary_rows
            if row["only_jq_count"] == 0 and row["only_local_count"] == 0 and row["amount_abs_diff"] == 0
        ),
        "dates_with_code_mismatch": sum(1 for row in summary_rows if row["only_jq_count"] or row["only_local_count"]),
        "dates_with_amount_diff": sum(1 for row in summary_rows if row["amount_abs_diff"] != 0),
        "first_mismatch": next(
            (
                row
                for row in summary_rows
                if row["only_jq_count"] or row["only_local_count"] or row["amount_abs_diff"] != 0
            ),
            None,
        ),
        "outputs": {
            "normalized_joinquant_positions": normalized_path.name,
            "position_comparison_summary": comparison_path.name,
            "position_common_diffs": diff_path.name,
            "position_attribution_summary": "position_attribution_summary.json",
            "position_attribution_report": "position_attribution_report.md",
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "note": "JoinQuant position exports are position/cash diagnostics. Daily NAV attribution still requires JoinQuant daily result CSV.",
    }
    _write_json(out / "position_attribution_summary.json", summary)
    _write_position_report(out / "position_attribution_report.md", summary)
    return out / "position_attribution_report.md"


def run_transaction_attribution(
    joinquant_transaction_csv: Path,
    local_trades_csv: Path,
    out_dir: Path,
    strategy_id: str = "bank_value_15y",
) -> Path:
    out = out_dir / f"{strategy_id}_transactions"
    out.mkdir(parents=True, exist_ok=True)
    jq_transactions, encoding = _load_joinquant_transactions(joinquant_transaction_csv)
    local_transactions = _load_local_trades(local_trades_csv)
    normalized_path = out / "normalized_joinquant_transactions.csv"
    comparison_path = out / "transaction_comparison.csv"
    date_summary_path = out / "transaction_comparison_by_date.csv"
    _write_csv(normalized_path, list(jq_transactions[0].keys()) if jq_transactions else [], jq_transactions)
    comparison_rows, date_rows = _compare_transactions(jq_transactions, local_transactions)
    _write_csv(comparison_path, list(comparison_rows[0].keys()) if comparison_rows else [], comparison_rows)
    _write_csv(date_summary_path, list(date_rows[0].keys()) if date_rows else [], date_rows)
    first_mismatch = next(
        (
            row
            for row in date_rows
            if row["joinquant_only"] or row["local_only"] or row["abs_amount_diff"]
        ),
        None,
    )
    first_day = first_mismatch["trade_date"] if first_mismatch else None
    summary = {
        "strategy_id": strategy_id,
        "joinquant_transaction_csv": str(joinquant_transaction_csv),
        "local_trades_csv": str(local_trades_csv),
        "encoding": encoding,
        "joinquant_rows": len(jq_transactions),
        "local_rows": len(local_transactions),
        "joinquant_dates": len({row["trade_date"] for row in jq_transactions}),
        "local_dates": len({row["trade_date"] for row in local_transactions}),
        "matched_key_count": sum(1 for row in comparison_rows if row["match_type"] == "both"),
        "joinquant_only_count": sum(1 for row in comparison_rows if row["match_type"] == "joinquant_only"),
        "local_only_count": sum(1 for row in comparison_rows if row["match_type"] == "local_only"),
        "first_mismatch_by_date": first_mismatch,
        "first_day_joinquant_codes": _codes_on_day(jq_transactions, first_day),
        "first_day_local_codes": _codes_on_day(local_transactions, first_day),
        "first_day_matched_codes": sorted(set(_codes_on_day(jq_transactions, first_day)) & set(_codes_on_day(local_transactions, first_day))),
        "outputs": {
            "normalized_joinquant_transactions": normalized_path.name,
            "transaction_comparison": comparison_path.name,
            "transaction_comparison_by_date": date_summary_path.name,
            "transaction_attribution_summary": "transaction_attribution_summary.json",
            "transaction_attribution_report": "transaction_attribution_report.md",
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "note": "Transaction exports diagnose fills, prices, commissions, and order-level differences. Use daily NAV CSV for full return attribution.",
    }
    _write_json(out / "transaction_attribution_summary.json", summary)
    _write_transaction_report(out / "transaction_attribution_report.md", summary)
    return out / "transaction_attribution_report.md"


def _load_local(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["trade_date"][:10]: row for row in csv.DictReader(handle) if row.get("trade_date")}


def _load_joinquant(path: Path) -> dict[str, dict[str, float]]:
    encodings = ["utf-8-sig", "gbk"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                rows = list(csv.DictReader(handle))
            result = {}
            for row in rows:
                values = list(row.values())
                if len(values) < 3:
                    continue
                day = str(values[0])[:10]
                result[day] = {
                    "benchmark_return": _pct(values[1]),
                    "strategy_return": _pct(values[2]),
                }
            return result
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise RuntimeError(f"failed to read JoinQuant daily CSV: {last_error}")


def _load_joinquant_positions(path: Path) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, float], str]:
    encodings = ["utf-8-sig", "gb18030", "gbk"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.reader(handle)
                next(reader, None)
                rows = list(reader)
            positions: list[dict[str, Any]] = []
            cash_by_date: dict[str, float] = {}
            value_by_date: dict[str, float] = {}
            for row in rows:
                if len(row) < 8:
                    continue
                day = row[0][:10]
                target = row[2]
                if target == "Cash":
                    cash_by_date[day] = _parse_number(row[7]) or 0.0
                    value_by_date.setdefault(day, cash_by_date[day])
                    continue
                code = _extract_joinquant_code(target)
                if not code:
                    continue
                amount = int(round(_parse_number(row[4]) or 0.0))
                close = _parse_number(row[6]) or 0.0
                market_value = _parse_number(row[7]) or 0.0
                total_value = _parse_number(row[15]) if len(row) > 16 else None
                weight = _parse_number(row[16]) if len(row) > 16 else _parse_number(row[15])
                if weight is not None:
                    weight /= 100.0
                if total_value is not None:
                    value_by_date[day] = max(value_by_date.get(day, 0.0), total_value)
                positions.append(
                    {
                        "trade_date": day,
                        "code": code,
                        "amount": amount,
                        "close": close,
                        "market_value": market_value,
                        "weight": weight if weight is not None else "",
                        "target_raw": target,
                    }
                )
            return positions, cash_by_date, value_by_date, encoding
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise RuntimeError(f"failed to read JoinQuant position CSV: {last_error}")


def _load_joinquant_transactions(path: Path) -> tuple[list[dict[str, Any]], str]:
    encodings = ["utf-8-sig", "gb18030", "gbk"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.reader(handle)
                next(reader, None)
                rows = list(reader)
            transactions: list[dict[str, Any]] = []
            for row in rows:
                if len(row) < 15:
                    continue
                code = _extract_joinquant_code(row[3])
                if not code:
                    continue
                amount = abs(int(round(_parse_number(row[6]) or 0.0)))
                if amount <= 0 or row[13] in {"已撤单", "撤单", "废单"}:
                    continue
                transactions.append(
                    {
                        "trade_date": row[0][:10],
                        "time": row[1],
                        "code": code,
                        "side": _parse_joinquant_side(row[4]),
                        "amount": amount,
                        "price": _parse_number(row[7]) or 0.0,
                        "value": abs(_parse_number(row[8]) or 0.0),
                        "commission": _parse_number(row[12]) or 0.0,
                        "status": row[13],
                        "target_raw": row[3],
                    }
                )
            return transactions, encoding
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise RuntimeError(f"failed to read JoinQuant transaction CSV: {last_error}")


def _load_local_holdings(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("trade_date") or not row.get("code"):
                continue
            amount = int(float(row.get("amount") or 0))
            if amount <= 0:
                continue
            result.append(
                {
                    "trade_date": row["trade_date"][:10],
                    "code": row["code"],
                    "amount": amount,
                    "close": _float(row.get("close")) or 0.0,
                    "actual_weight": _float(row.get("actual_weight")) or 0.0,
                }
            )
    return result


def _load_local_trades(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("trade_date") or not row.get("code") or "skipped" in row.get("side", ""):
                continue
            result.append(
                {
                    "trade_date": row["trade_date"][:10],
                    "time": "",
                    "code": row["code"],
                    "side": row["side"],
                    "amount": int(float(row.get("amount") or 0)),
                    "price": _float(row.get("price")) or 0.0,
                    "value": _float(row.get("value")) or 0.0,
                    "commission": _float(row.get("commission")) or 0.0,
                    "status": "",
                    "target_raw": "",
                }
            )
    return result


def _compare_positions(
    joinquant_positions: list[dict[str, Any]],
    local_positions: list[dict[str, Any]],
    joinquant_cash_by_date: dict[str, float],
    joinquant_value_by_date: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    jq_by_date: dict[str, dict[str, dict[str, Any]]] = {}
    for row in joinquant_positions:
        jq_by_date.setdefault(row["trade_date"], {})[row["code"]] = row
    local_by_date: dict[str, dict[str, dict[str, Any]]] = {}
    for row in local_positions:
        local_by_date.setdefault(row["trade_date"], {})[row["code"]] = row
    summary_rows: list[dict[str, Any]] = []
    diff_rows: list[dict[str, Any]] = []
    for day in sorted(set(jq_by_date) | set(local_by_date)):
        jq_codes = set(jq_by_date.get(day, {}))
        local_codes = set(local_by_date.get(day, {}))
        common = jq_codes & local_codes
        amount_abs_diff = sum(abs(jq_by_date[day][code]["amount"] - local_by_date[day][code]["amount"]) for code in common)
        weight_abs_diff = sum(
            abs((_coerce_float(jq_by_date[day][code].get("weight")) or 0.0) - local_by_date[day][code]["actual_weight"])
            for code in common
        )
        only_jq = sorted(jq_codes - local_codes)
        only_local = sorted(local_codes - jq_codes)
        summary_rows.append(
            {
                "trade_date": day,
                "jq_count": len(jq_codes),
                "local_count": len(local_codes),
                "common_count": len(common),
                "only_jq_count": len(only_jq),
                "only_local_count": len(only_local),
                "amount_abs_diff": amount_abs_diff,
                "weight_abs_diff": weight_abs_diff,
                "jq_cash": joinquant_cash_by_date.get(day, ""),
                "jq_portfolio_value": joinquant_value_by_date.get(day, ""),
                "only_jq_codes": ";".join(only_jq),
                "only_local_codes": ";".join(only_local),
            }
        )
        for code in sorted(common):
            jq = jq_by_date[day][code]
            local = local_by_date[day][code]
            amount_diff = jq["amount"] - local["amount"]
            jq_weight = _coerce_float(jq.get("weight")) or 0.0
            weight_diff = jq_weight - local["actual_weight"]
            if amount_diff or abs(weight_diff) > 0.002:
                diff_rows.append(
                    {
                        "trade_date": day,
                        "code": code,
                        "jq_amount": jq["amount"],
                        "local_amount": local["amount"],
                        "amount_diff": amount_diff,
                        "jq_weight": jq_weight,
                        "local_weight": local["actual_weight"],
                        "weight_diff": weight_diff,
                    }
                )
    return summary_rows, diff_rows


def _compare_transactions(
    joinquant_transactions: list[dict[str, Any]],
    local_transactions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    jq_by_key = {_transaction_key(row): row for row in joinquant_transactions}
    local_by_key = {_transaction_key(row): row for row in local_transactions}
    comparison_rows: list[dict[str, Any]] = []
    for key in sorted(set(jq_by_key) | set(local_by_key)):
        jq = jq_by_key.get(key)
        local = local_by_key.get(key)
        both = jq is not None and local is not None
        comparison_rows.append(
            {
                "trade_date": key[0],
                "side": key[1],
                "code": key[2],
                "match_type": "both" if both else ("joinquant_only" if jq else "local_only"),
                "jq_amount": jq["amount"] if jq else "",
                "local_amount": local["amount"] if local else "",
                "amount_diff": (jq["amount"] if jq else 0) - (local["amount"] if local else 0),
                "jq_price": jq["price"] if jq else "",
                "local_price": local["price"] if local else "",
                "price_diff": jq["price"] - local["price"] if both else "",
                "jq_value": jq["value"] if jq else "",
                "local_value": local["value"] if local else "",
                "value_diff": jq["value"] - local["value"] if both else "",
                "jq_commission": jq["commission"] if jq else "",
                "local_commission": local["commission"] if local else "",
                "commission_diff": jq["commission"] - local["commission"] if both else "",
                "jq_time": jq["time"] if jq else "",
                "jq_status": jq["status"] if jq else "",
                "jq_target_raw": jq["target_raw"] if jq else "",
            }
        )
    date_rows: list[dict[str, Any]] = []
    for day in sorted({row["trade_date"] for row in comparison_rows}):
        rows = [row for row in comparison_rows if row["trade_date"] == day]
        both_rows = [row for row in rows if row["match_type"] == "both"]
        date_rows.append(
            {
                "trade_date": day,
                "jq_trades": sum(1 for row in rows if row["match_type"] in {"both", "joinquant_only"}),
                "local_trades": sum(1 for row in rows if row["match_type"] in {"both", "local_only"}),
                "matched_trades": len(both_rows),
                "joinquant_only": sum(1 for row in rows if row["match_type"] == "joinquant_only"),
                "local_only": sum(1 for row in rows if row["match_type"] == "local_only"),
                "abs_amount_diff": sum(abs(float(row["amount_diff"] or 0.0)) for row in both_rows),
                "abs_value_diff": sum(abs(float(row["value_diff"] or 0.0)) for row in both_rows if row["value_diff"] != ""),
                "abs_commission_diff": sum(abs(float(row["commission_diff"] or 0.0)) for row in both_rows if row["commission_diff"] != ""),
            }
        )
    return comparison_rows, date_rows


def _pct(value: Any) -> float:
    return float(str(value).replace("%", "").strip()) / 100.0


def _extract_joinquant_code(target: str) -> str | None:
    match = re.search(r"\((\d{6}\.XS(?:HG|HE))\)", target or "")
    return match.group(1) if match else None


def _parse_joinquant_side(value: str) -> str:
    text = (value or "").strip()
    if text in {"买", "买入", "开仓买入", "买开", "\u0392\u03c2"} or text.startswith("\u0392"):
        return "buy"
    if text in {"卖", "卖出", "平仓卖出", "卖平", "\u0392\u03c4"}:
        return "sell"
    return text


def _parse_number(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    text = str(value).replace(",", "").replace("%", "").strip()
    if text in {"-", "--"}:
        return None
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", "-", "--"}:
        return None
    return float(text)


def _coerce_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def _transaction_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return row["trade_date"], row["side"], row["code"]


def _codes_on_day(rows: list[dict[str, Any]], day: str | None) -> list[str]:
    if day is None:
        return []
    return sorted({row["code"] for row in rows if row["trade_date"] == day})


def _local_execution_diagnostics(
    local: dict[str, dict[str, str]],
    local_rebalance_signals_csv: Path | None,
    local_trades_csv: Path | None,
    local_dividends_csv: Path | None,
) -> dict[str, Any]:
    trades = _read_optional(local_trades_csv)
    dividends = _read_optional(local_dividends_csv)
    signals = _read_optional(local_rebalance_signals_csv)
    cash_weights = [_float(row.get("cash_weight")) for row in local.values()]
    cash_weights = [value for value in cash_weights if value is not None]
    return {
        "local_daily_days": len(local),
        "rebalance_count": len(signals),
        "trade_count": len(trades),
        "buy_count": sum(1 for row in trades if row.get("side") == "buy"),
        "sell_count": sum(1 for row in trades if row.get("side") == "sell"),
        "skipped_trade_count": sum(1 for row in trades if "skipped" in str(row.get("side", ""))),
        "dividend_event_count": len(dividends),
        "total_local_dividend_cash": sum(_float(row.get("dividend_cash")) or 0.0 for row in dividends),
        "final_cash": _float(list(local.values())[-1].get("cash")) if local else None,
        "max_cash_weight": max(cash_weights) if cash_weights else None,
        "mean_cash_weight": sum(cash_weights) / len(cash_weights) if cash_weights else None,
        "rebalance_signal_sample": signals[:5],
        "diagnostic_note": "Compare JoinQuant logs against local rebalances/trades/dividends when daily attribution diverges.",
    }


def _read_optional(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(value: Any) -> float | None:
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _summary(rows: list[dict[str, Any]], local_daily_csv: Path, joinquant_daily_csv: Path, strategy_id: str, diagnostics: dict[str, Any]) -> dict[str, Any]:
    if rows:
        last = rows[-1]
        max_abs_strategy_diff = max(abs(float(row["strategy_diff"])) for row in rows)
        max_abs_benchmark_diff = max(abs(float(row["benchmark_diff"])) for row in rows)
    else:
        last = {}
        max_abs_strategy_diff = None
        max_abs_benchmark_diff = None
    return {
        "strategy_id": strategy_id,
        "local_daily_csv": str(local_daily_csv),
        "joinquant_daily_csv": str(joinquant_daily_csv),
        "matched_days": len(rows),
        "last_date": last.get("date"),
        "final_strategy_diff": last.get("strategy_diff"),
        "final_benchmark_diff": last.get("benchmark_diff"),
        "max_abs_strategy_diff": max_abs_strategy_diff,
        "max_abs_benchmark_diff": max_abs_benchmark_diff,
        "status": "platform_attribution_completed",
        "local_execution_diagnostics": diagnostics,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _date_range(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    return [rows[0]["trade_date"], rows[-1]["trade_date"]]


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# Platform Attribution Report: {summary['strategy_id']}",
        "",
        f"- Matched days: `{summary['matched_days']}`",
        f"- Last date: `{summary['last_date']}`",
        f"- Final strategy diff: `{summary['final_strategy_diff']}`",
        f"- Final benchmark diff: `{summary['final_benchmark_diff']}`",
        f"- Max abs strategy diff: `{summary['max_abs_strategy_diff']}`",
        f"- Max abs benchmark diff: `{summary['max_abs_benchmark_diff']}`",
        f"- Local trade count: `{summary['local_execution_diagnostics']['trade_count']}`",
        f"- Local dividend event count: `{summary['local_execution_diagnostics']['dividend_event_count']}`",
        f"- Local rebalance count: `{summary['local_execution_diagnostics']['rebalance_count']}`",
        "",
        "Use this report only after local and JoinQuant runs share the same frozen signal contract.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_position_report(path: Path, summary: dict[str, Any]) -> None:
    first = summary.get("first_mismatch") or {}
    lines = [
        f"# Position Attribution Report: {summary['strategy_id']}",
        "",
        f"- JoinQuant position rows: `{summary['joinquant_position_rows']}`",
        f"- JoinQuant dates: `{summary['joinquant_dates']}`",
        f"- Local holding dates: `{summary['local_dates']}`",
        f"- Date range: `{summary['date_range']}`",
        f"- Perfect matched dates: `{summary['perfect_position_dates']}`",
        f"- Dates with code mismatch: `{summary['dates_with_code_mismatch']}`",
        f"- Dates with amount diff: `{summary['dates_with_amount_diff']}`",
        "",
        "## First Mismatch",
        "",
        f"- Date: `{first.get('trade_date')}`",
        f"- JoinQuant count: `{first.get('jq_count')}`",
        f"- Local count: `{first.get('local_count')}`",
        f"- Common count: `{first.get('common_count')}`",
        f"- Only JoinQuant: `{first.get('only_jq_codes')}`",
        f"- Only local: `{first.get('only_local_codes')}`",
        f"- Amount abs diff: `{first.get('amount_abs_diff')}`",
        "",
        "This file diagnoses positions and cash. Use the JoinQuant daily result CSV for full NAV attribution.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_transaction_report(path: Path, summary: dict[str, Any]) -> None:
    first = summary.get("first_mismatch_by_date") or {}
    lines = [
        f"# Transaction Attribution Report: {summary['strategy_id']}",
        "",
        f"- JoinQuant transactions: `{summary['joinquant_rows']}`",
        f"- Local transactions: `{summary['local_rows']}`",
        f"- Matched transaction keys: `{summary['matched_key_count']}`",
        f"- JoinQuant-only keys: `{summary['joinquant_only_count']}`",
        f"- Local-only keys: `{summary['local_only_count']}`",
        "",
        "## First Mismatch By Date",
        "",
        f"- Date: `{first.get('trade_date')}`",
        f"- JoinQuant trades: `{first.get('jq_trades')}`",
        f"- Local trades: `{first.get('local_trades')}`",
        f"- Matched trades: `{first.get('matched_trades')}`",
        f"- JoinQuant-only: `{first.get('joinquant_only')}`",
        f"- Local-only: `{first.get('local_only')}`",
        f"- Abs amount diff on matched names: `{first.get('abs_amount_diff')}`",
        f"- Abs value diff on matched names: `{first.get('abs_value_diff')}`",
        f"- Abs commission diff on matched names: `{first.get('abs_commission_diff')}`",
        "",
        "## First-Day Codes",
        "",
        f"- JoinQuant: `{';'.join(summary.get('first_day_joinquant_codes') or [])}`",
        f"- Local: `{';'.join(summary.get('first_day_local_codes') or [])}`",
        f"- Matched: `{';'.join(summary.get('first_day_matched_codes') or [])}`",
        "",
        "This report diagnoses trade fills, quantities, prices, and commissions. It does not replace daily NAV attribution.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-platform-attribution")
    subparsers = parser.add_subparsers(dest="command", required=True)
    daily_parser = subparsers.add_parser("daily")
    daily_parser.add_argument("local_daily_csv", type=Path)
    daily_parser.add_argument("joinquant_daily_csv", type=Path)
    daily_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    daily_parser.add_argument("--strategy-id", default="bank_value_15y")
    daily_parser.add_argument("--local-rebalance-signals-csv", type=Path)
    daily_parser.add_argument("--local-trades-csv", type=Path)
    daily_parser.add_argument("--local-dividends-csv", type=Path)
    position_parser = subparsers.add_parser("positions")
    position_parser.add_argument("joinquant_position_csv", type=Path)
    position_parser.add_argument("local_holdings_csv", type=Path)
    position_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    position_parser.add_argument("--strategy-id", default="bank_value_15y")
    transaction_parser = subparsers.add_parser("transactions")
    transaction_parser.add_argument("joinquant_transaction_csv", type=Path)
    transaction_parser.add_argument("local_trades_csv", type=Path)
    transaction_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    transaction_parser.add_argument("--strategy-id", default="bank_value_15y")
    args = parser.parse_args(argv)
    if args.command == "daily":
        print(
            run_platform_attribution(
                args.local_daily_csv,
                args.joinquant_daily_csv,
                args.out,
                args.strategy_id,
                local_rebalance_signals_csv=args.local_rebalance_signals_csv,
                local_trades_csv=args.local_trades_csv,
                local_dividends_csv=args.local_dividends_csv,
            )
        )
    if args.command == "positions":
        print(
            run_position_attribution(
                args.joinquant_position_csv,
                args.local_holdings_csv,
                args.out,
                args.strategy_id,
            )
        )
    if args.command == "transactions":
        print(
            run_transaction_attribution(
                args.joinquant_transaction_csv,
                args.local_trades_csv,
                args.out,
                args.strategy_id,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
