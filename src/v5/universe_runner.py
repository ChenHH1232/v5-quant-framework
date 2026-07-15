from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_point_in_time_universe(panel_path: Path, execution_price_csv: Path, out_dir: Path, strategy_id: str = "bank_value_15y") -> Path:
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    panel_codes = _load_panel_codes(panel_path)
    price_rows = _load_prices(execution_price_csv, panel_codes)
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    first_seen: dict[str, str] = {}
    last_seen: dict[str, str] = {}
    for row in price_rows:
        code = row["code"]
        day = row["date"]
        first_seen.setdefault(code, day)
        last_seen[code] = day
        by_date[day].append(row)
    snapshot_rows = []
    for day, rows in sorted(by_date.items()):
        for row in sorted(rows, key=lambda item: item["code"]):
            snapshot_rows.append(
                {
                    "date": day,
                    "code": row["code"],
                    "in_panel_universe": True,
                    "has_real_price": True,
                    "paused": row.get("paused", ""),
                    "is_tradable_proxy": str(row.get("paused", "0")) in {"", "0", "0.0", "False", "false"},
                    "first_seen": first_seen[row["code"]],
                    "last_seen": last_seen[row["code"]],
                    "source": "panel_codes_intersect_joinquant_real_daily_prices",
                }
            )
    security_rows = [
        {
            "code": code,
            "first_seen": first_seen.get(code, ""),
            "last_seen": last_seen.get(code, ""),
            "days": sum(1 for row in price_rows if row["code"] == code),
            "source": "panel_codes_intersect_joinquant_real_daily_prices",
        }
        for code in sorted(panel_codes)
    ]
    _write_csv(out / "universe_snapshots.csv", list(snapshot_rows[0].keys()) if snapshot_rows else [], snapshot_rows)
    _write_csv(out / "universe_securities.csv", list(security_rows[0].keys()) if security_rows else [], security_rows)
    manifest = {
        "strategy_id": strategy_id,
        "panel": str(panel_path),
        "execution_price_csv": str(execution_price_csv),
        "snapshot_rows": len(snapshot_rows),
        "security_count": len(panel_codes),
        "date_count": len(by_date),
        "status": "point_in_time_tradable_snapshot_proxy",
        "limitations": [
            "This is a point-in-time tradability snapshot based on collected bank panel codes and JoinQuant daily price availability.",
            "It is not yet a full historical industry-classification reconstruction.",
            "Future versions should add listing dates, delisting dates, ST status, and industry membership by date.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(out / "universe_manifest.json", manifest)
    return out / "universe_manifest.json"


def _load_panel_codes(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["code"] for row in csv.DictReader(handle) if row.get("code")}


def _load_prices(path: Path, codes: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("code") in codes and row.get("date")]
    rows.sort(key=lambda item: (item["date"], item["code"]))
    return rows


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
    parser = argparse.ArgumentParser(prog="v5-universe")
    parser.add_argument("panel", type=Path)
    parser.add_argument("execution_price_csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("universes"))
    parser.add_argument("--strategy-id", default="bank_value_15y")
    args = parser.parse_args(argv)
    print(build_point_in_time_universe(args.panel, args.execution_price_csv, args.out, args.strategy_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
