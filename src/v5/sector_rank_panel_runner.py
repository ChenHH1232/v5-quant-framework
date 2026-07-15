from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def build_sector_rank_panel(
    source_panel: Path,
    out_dir: Path,
    factor_config: Path,
    date_field: str = "trade_date",
    group_field: str = "sub_industry",
    min_group_size: int = 8,
) -> Path:
    rows = _read_csv(source_panel)
    configs = json.loads(factor_config.read_text(encoding="utf-8"))
    if not isinstance(configs, list) or not configs:
        raise ValueError("factor_config must be a non-empty JSON list")

    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_date_group: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_date[row[date_field]].append(row)
        by_date_group[(row[date_field], row.get(group_field, ""))].append(row)

    added_fields = [str(item["output"]) for item in configs]
    enhanced = []
    for row in rows:
        date_rows = by_date[row[date_field]]
        group_rows = by_date_group[(row[date_field], row.get(group_field, ""))]
        peers = group_rows if len(group_rows) >= min_group_size else date_rows
        item = dict(row)
        for config in configs:
            item[str(config["output"])] = _fmt(
                _percentile(
                    row,
                    peers,
                    str(config["input"]),
                    higher_is_better=str(config.get("direction", "higher_is_better")) == "higher_is_better",
                )
            )
        enhanced.append(item)

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel.csv"
    fieldnames = list(rows[0].keys()) + [field for field in added_fields if field not in rows[0]]
    _write_csv(panel_path, fieldnames, enhanced)
    _write_json(
        out_dir / "collection_manifest.json",
        {
            "dataset": "sector_rank_panel",
            "source_panel": str(source_panel),
            "panel": str(panel_path),
            "factor_config": str(factor_config),
            "date_field": date_field,
            "group_field": group_field,
            "min_group_size": min_group_size,
            "added_fields": added_fields,
            "row_count": len(enhanced),
            "date_count": len({row[date_field] for row in enhanced}),
            "code_count": len({row.get("code", "") for row in enhanced if row.get("code")}),
            "governance": "Generic sector rank panel is a research data transform only. It is not strategy acceptance.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return panel_path


def _percentile(row: dict[str, str], peers: list[dict[str, str]], field: str, higher_is_better: bool) -> float | None:
    current = _to_float(row.get(field))
    if current is None:
        return None
    values = [_to_float(peer.get(field)) for peer in peers]
    values = sorted(value for value in values if value is not None)
    if len(values) < 3:
        return None
    below_or_equal = sum(1 for value in values if value <= current)
    percentile = below_or_equal / len(values)
    if not higher_is_better:
        percentile = 1.0 - percentile
    return percentile


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric or numeric in {float("inf"), float("-inf")}:
        return None
    return numeric


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-sector-rank-panel")
    parser.add_argument("source_panel", type=Path)
    parser.add_argument("factor_config", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("数据库") / "processed" / "sector_rank_panel")
    parser.add_argument("--date-field", default="trade_date")
    parser.add_argument("--group-field", default="sub_industry")
    parser.add_argument("--min-group-size", type=int, default=8)
    args = parser.parse_args(argv)
    print(
        build_sector_rank_panel(
            args.source_panel,
            args.out_dir,
            args.factor_config,
            date_field=args.date_field,
            group_field=args.group_field,
            min_group_size=args.min_group_size,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
