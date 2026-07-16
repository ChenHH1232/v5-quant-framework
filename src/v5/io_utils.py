from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


def read_csv_rows(path: Path, *, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    with path.open("r", encoding=encoding, newline="") as handle:
        return list(csv.DictReader(handle))


def read_csv_rows_if_exists(path: Path | None, *, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    return read_csv_rows(path, encoding=encoding)


def write_csv_rows(
    path: Path,
    fieldnames: Iterable[str],
    rows: Iterable[dict[str, Any]],
    *,
    encoding: str = "utf-8",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(fieldnames)
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json_file(path: Path, payload: dict[str, Any] | list[Any], *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
