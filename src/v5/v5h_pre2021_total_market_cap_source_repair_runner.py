from __future__ import annotations

import csv
import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5h_pre2021_total_market_cap_source_repair") / "current"
SIZE_LIQ_DIR = Path("v5h_size_liquidity_interaction_independent_validation") / "current"
QUIET_DIR = Path("v5h_quiet_or_active_independent_validation") / "current"

SIZE_LIQ_PRE2021_PANEL = SIZE_LIQ_DIR / "v5h_size_liquidity_pre2021_order_panel.csv"
QUIET_PRE2021_PANEL = QUIET_DIR / "v5h_quiet_or_active_independent_order_panel.csv"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_pre2021_total_market_cap_source_repair(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    existing_summary_path = out / "v5h_pre2021_total_market_cap_source_repair_summary.json"
    source_path = root / SIZE_LIQ_PRE2021_PANEL if (root / SIZE_LIQ_PRE2021_PANEL).exists() else root / QUIET_PRE2021_PANEL
    if not source_path.exists():
        blockers = [_blocker("missing_pre2021_order_panel", str(source_path))]
        summary = _summary("blocked_missing_pre2021_order_panel", "blocked_missing_pre2021_order_panel", blockers)
        _write_json(out / "v5h_pre2021_total_market_cap_source_repair_summary.json", summary)
        _write_csv(out / "v5h_pre2021_total_market_cap_repair_blockers.csv", blockers)
        return summary

    rows = _read_csv(source_path)
    missing = _missing_market_cap_rows(rows)
    repaired_rows_path = out / "v5h_pre2021_total_market_cap_repaired_rows.csv"
    existing_repaired = _read_csv(repaired_rows_path)
    if not missing and existing_repaired:
        blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
        reconstructed_missing = [
            {
                "trade_date": row.get("trade_date", ""),
                "code": row.get("code", ""),
                "sleeve": row.get("sleeve", ""),
                "day_close": row.get("close", ""),
                "source_status": "repaired_previously",
                "accepted": False,
            }
            for row in existing_repaired
        ]
        _write_csv(out / "v5h_pre2021_total_market_cap_missing_rows_before.csv", reconstructed_missing)
        summary = _summary(
            "completed_pre2021_total_market_cap_source_repair",
            "baostock_total_share_repair_success",
            blockers,
            source_panel=str(source_path),
            missing_rows_before=len(existing_repaired),
            repaired_rows=len(existing_repaired),
            unresolved_rows=0,
            network_fetch_started=False,
            baostock_started=False,
            joinquant_started=False,
            idempotent_reuse=True,
        )
        _write_json(existing_summary_path, summary)
        _write_csv(out / "v5h_pre2021_total_market_cap_repair_blockers.csv", blockers)
        return summary
    if not missing and existing_summary_path.exists():
        existing_summary = json.loads(existing_summary_path.read_text(encoding="utf-8-sig"))
        if existing_summary.get("repair_decision") == "baostock_total_share_repair_success":
            return existing_summary
    _write_csv(out / "v5h_pre2021_total_market_cap_missing_rows_before.csv", missing)
    if not missing:
        blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
        summary = _summary("completed_no_missing_pre2021_market_cap_rows", "no_repair_needed", blockers)
        _write_json(out / "v5h_pre2021_total_market_cap_source_repair_summary.json", summary)
        _write_csv(out / "v5h_pre2021_total_market_cap_repair_blockers.csv", blockers)
        return summary

    fetch_result = _fetch_baostock_profit_records(sorted({row["code"] for row in missing}))
    repaired_rows = _build_repaired_rows(missing, fetch_result["records_by_code"])
    unresolved = [
        row
        for row in missing
        if (row.get("trade_date", ""), row.get("code", ""), row.get("sleeve", "")) not in {
            (r.get("trade_date", ""), r.get("code", ""), r.get("sleeve", "")) for r in repaired_rows
        }
    ]
    decision = "baostock_total_share_repair_success" if not unresolved else "baostock_total_share_repair_partial"
    status = "completed_pre2021_total_market_cap_source_repair" if repaired_rows else "blocked_no_baostock_total_share_repair"
    blockers = (
        [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
        if not unresolved
        else [_blocker("unresolved_pre2021_market_cap_rows", f"{len(unresolved)} rows remain unresolved")]
    )

    _write_csv(out / "v5h_pre2021_total_market_cap_baostock_fetch_audit.csv", fetch_result["fetch_audit"])
    _write_csv(out / "v5h_pre2021_total_market_cap_repaired_rows.csv", repaired_rows)
    _write_csv(out / "v5h_pre2021_total_market_cap_unresolved_rows.csv", unresolved)
    _write_csv(out / "v5h_pre2021_total_market_cap_repair_decision.csv", [_decision_row(decision, len(missing), len(repaired_rows), len(unresolved))])
    _write_csv(out / "v5h_pre2021_total_market_cap_repair_blockers.csv", blockers)
    (out / "v5h_pre2021_total_market_cap_source_repair_report.md").write_text(
        _report(missing, repaired_rows, unresolved, decision),
        encoding="utf-8",
    )
    (out / "v5h_pre2021_total_market_cap_repair_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        status,
        decision,
        blockers,
        source_panel=str(source_path),
        missing_rows_before=len(missing),
        repaired_rows=len(repaired_rows),
        unresolved_rows=len(unresolved),
        network_fetch_started=fetch_result["started"],
        baostock_started=fetch_result["started"],
        joinquant_started=False,
    )
    _write_json(out / "v5h_pre2021_total_market_cap_source_repair_summary.json", summary)
    return summary


def _missing_market_cap_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        status = row.get("market_cap_pit_status")
        market_cap = _none_float(row.get("market_cap_100m_cny"))
        if status == "pass" and market_cap is not None:
            continue
        key = (row.get("trade_date", ""), row.get("code", ""), row.get("sleeve", ""))
        if key not in unique:
            unique[key] = {
                "trade_date": row.get("trade_date", ""),
                "code": row.get("code", ""),
                "sleeve": row.get("sleeve", ""),
                "day_close": row.get("day_close", ""),
                "source_status": status or "missing",
                "accepted": False,
            }
    return list(unique.values())


def _fetch_baostock_profit_records(codes: list[str]) -> dict[str, Any]:
    started = False
    audit: list[dict[str, Any]] = []
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    try:
        import baostock as bs
    except Exception as exc:
        return {
            "started": False,
            "records_by_code": {},
            "fetch_audit": [{"source": "baostock_profit_data", "status": "import_error", "detail": str(exc)}],
        }

    started = True
    t0 = time.perf_counter()
    lg = bs.login()
    try:
        if getattr(lg, "error_code", "") != "0":
            return {
                "started": True,
                "records_by_code": {},
                "fetch_audit": [{"source": "baostock_login", "status": "error", "detail": getattr(lg, "error_msg", "")}],
            }
        for code in codes:
            bs_code = _to_baostock_code(code)
            for year in range(2017, 2021):
                for quarter in range(1, 5):
                    q0 = time.perf_counter()
                    result = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
                    row_count = 0
                    if getattr(result, "error_code", "") == "0":
                        while result.next():
                            record = dict(zip(result.fields, result.get_row_data()))
                            record["v5_code"] = code
                            record["bs_code"] = bs_code
                            record["year"] = year
                            record["quarter"] = quarter
                            records[code].append(record)
                            row_count += 1
                        status = "pass"
                        detail = ""
                    else:
                        status = "query_error"
                        detail = str(getattr(result, "error_msg", ""))
                    audit.append(
                        {
                            "source": "baostock_profit_data",
                            "code": code,
                            "bs_code": bs_code,
                            "year": year,
                            "quarter": quarter,
                            "status": status,
                            "row_count": row_count,
                            "elapsed_sec": round(time.perf_counter() - q0, 3),
                            "detail": detail,
                        }
                    )
    finally:
        bs.logout()
    audit.append(
        {
            "source": "baostock_profit_data",
            "status": "completed",
            "code_count": len(codes),
            "record_count": sum(len(value) for value in records.values()),
            "elapsed_sec": round(time.perf_counter() - t0, 3),
            "detail": "query_profit_data used for totalShare/liqaShare only.",
        }
    )
    return {"started": started, "records_by_code": dict(records), "fetch_audit": audit}


def _build_repaired_rows(missing: list[dict[str, Any]], records_by_code: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in missing:
        trade_date = str(row.get("trade_date", ""))
        code = str(row.get("code", ""))
        close = _none_float(row.get("day_close"))
        record = _latest_visible_record(records_by_code.get(code, []), trade_date)
        total_share = _none_float(record.get("totalShare")) if record else None
        liqa_share = _none_float(record.get("liqaShare")) if record else None
        if close is None or total_share is None:
            continue
        out.append(
            {
                "trade_date": trade_date,
                "code": code,
                "sleeve": row.get("sleeve", ""),
                "close": close,
                "total_share": total_share,
                "liqa_share": liqa_share if liqa_share is not None else "",
                "market_cap_100m_cny": close * total_share / 100000000.0,
                "free_float_market_cap_100m_cny": close * liqa_share / 100000000.0 if liqa_share is not None else "",
                "market_cap_visible_date": record.get("pubDate", ""),
                "market_cap_report_period": record.get("statDate", ""),
                "market_cap_source": "baostock.query_profit_data.totalShare",
                "market_cap_pit_method": "derived_close_times_baostock_visible_total_share",
                "market_cap_pit_status": "pass",
                "accepted": False,
            }
        )
    return out


def _latest_visible_record(records: list[dict[str, Any]], trade_date: str) -> dict[str, Any]:
    visible = [
        record
        for record in records
        if str(record.get("pubDate", ""))[:10] <= trade_date
        and str(record.get("statDate", ""))[:10] <= trade_date
        and str(record.get("pubDate", ""))[:10]
    ]
    visible.sort(key=lambda record: (str(record.get("statDate", ""))[:10], str(record.get("pubDate", ""))[:10]))
    return visible[-1] if visible else {}


def _to_baostock_code(code: str) -> str:
    if code.endswith(".XSHG"):
        return "sh." + code[:6]
    if code.endswith(".XSHE"):
        return "sz." + code[:6]
    return code


def _decision_row(decision: str, missing_count: int, repaired_count: int, unresolved_count: int) -> dict[str, Any]:
    return {
        "repair_decision": decision,
        "missing_rows_before": missing_count,
        "repaired_rows": repaired_count,
        "unresolved_rows": unresolved_count,
        "network_fetch_started": True,
        "baostock_started": True,
        "joinquant_started": False,
        "accepted": False,
    }


def _report(missing: list[dict[str, Any]], repaired: list[dict[str, Any]], unresolved: list[dict[str, Any]], decision: str) -> str:
    return "\n".join(
        [
            "# V5h Pre-2021 Total Market-Cap Source Repair",
            "",
            f"- Repair decision: `{decision}`",
            f"- Missing rows before: `{len(missing)}`",
            f"- Repaired rows: `{len(repaired)}`",
            f"- Unresolved rows: `{len(unresolved)}`",
            "- Source: BaoStock `query_profit_data.totalShare`, PIT by `pubDate <= trade_date`.",
            "- Market cap unit: 100m CNY, computed as `close * totalShare / 100000000`.",
            "- This is a data-source repair only; it does not change V57f/V5f rules.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5h Pre-2021 Total Market-Cap Repair Rules",
            "",
            "- Use BaoStock profit `totalShare` only when `pubDate <= trade_date` and `statDate <= trade_date`.",
            "- Use existing PIT same-day close from the order panel.",
            "- Do not use future dividend/share-capital events.",
            "- Do not modify V57f core or V5f mainline.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5h_pre2021_total_market_cap_source_repair",
        "status": status,
        "repair_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "trading_frequency_increased": False,
        "new_buy_signal_used": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("status") == "blocking"]),
        "fatal_blockers": [row for row in blockers if row.get("status") == "blocking"],
        **extra,
    }


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _none_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        text = str(value).strip()
        if text == "" or text.lower() in {"nan", "none", "null"}:
            return None
        out = float(text)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    summary = run_v5h_pre2021_total_market_cap_source_repair(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
