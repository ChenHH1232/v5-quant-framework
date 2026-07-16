from __future__ import annotations

from datetime import date
from typing import Any


def parse_iso_date(value: Any) -> date:
    return date.fromisoformat(str(value)[:10])


def parse_iso_date_or_none(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return parse_iso_date(value)
    except ValueError:
        return None


def date_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    return str(value)[:10]
