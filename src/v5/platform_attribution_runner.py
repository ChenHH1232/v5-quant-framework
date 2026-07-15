from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_platform_attribution(local_daily_csv: Path, joinquant_daily_csv: Path, out_dir: Path, strategy_id: str = "bank_value_15y") -> Path:
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
    summary = _summary(rows, local_daily_csv, joinquant_daily_csv, strategy_id)
    _write_json(out / "platform_attribution_summary.json", summary)
    _write_report(out / "platform_attribution_report.md", summary)
    return out / "platform_attribution_report.md"


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


def _pct(value: Any) -> float:
    return float(str(value).replace("%", "").strip()) / 100.0


def _summary(rows: list[dict[str, Any]], local_daily_csv: Path, joinquant_daily_csv: Path, strategy_id: str) -> dict[str, Any]:
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
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


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
        "",
        "Use this report only after local and JoinQuant runs share the same frozen signal contract.",
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
    parser.add_argument("local_daily_csv", type=Path)
    parser.add_argument("joinquant_daily_csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    parser.add_argument("--strategy-id", default="bank_value_15y")
    args = parser.parse_args(argv)
    print(run_platform_attribution(args.local_daily_csv, args.joinquant_daily_csv, args.out, args.strategy_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
