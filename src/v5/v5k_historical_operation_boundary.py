from __future__ import annotations

import json
from pathlib import Path
from typing import Any


POLICY = Path("config") / "v5_historical_operation_boundary.json"


def load_boundary(root: Path = Path(".")) -> dict[str, Any]:
    return json.loads((root / POLICY).read_text(encoding="utf-8"))


def date_is_allowed(date: str, root: Path = Path(".")) -> bool:
    return str(date) <= str(load_boundary(root)["market_data_max_date"])


def historical_operation_audit(operation: str, requested_market_date: str, root: Path = Path(".")) -> dict[str, Any]:
    boundary = load_boundary(root)
    allowed = date_is_allowed(requested_market_date, root) or operation in boundary["allowed_operations"]
    return {
        "operation": operation,
        "requested_market_date": requested_market_date,
        "market_data_max_date": boundary["market_data_max_date"],
        "allowed": allowed,
        "reason": "within_historical_boundary" if allowed else "post_boundary_market_operation_blocked",
    }
