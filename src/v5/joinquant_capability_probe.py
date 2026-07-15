from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def run_joinquant_capability_probe(
    out_dir: Path,
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> Path:
    jq = _load_authenticated_jqdata(username_env, password_env)
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = [
        _check("get_all_securities_stock", lambda: jq.get_all_securities(["stock"], date="2025-12-31").head(3).to_dict("records")),
        _check("get_price_stock_daily_raw", lambda: _records(jq.get_price("000001.XSHE", start_date="2025-01-02", end_date="2025-01-10", frequency="daily", fields=["open", "close", "high_limit", "low_limit", "paused"], fq=None, panel=False))),
        _check("get_price_stock_daily_pre", lambda: _records(jq.get_price("000001.XSHE", start_date="2025-01-02", end_date="2025-01-10", frequency="daily", fields=["open", "close"], fq="pre", panel=False))),
        _check("get_price_etf_daily_pre", lambda: _records(jq.get_price("512800.XSHG", start_date="2025-01-02", end_date="2025-01-10", frequency="daily", fields=["open", "close", "volume", "money"], fq="pre", panel=False))),
        _check("get_fundamentals_valuation_indicator", lambda: _records(jq.get_fundamentals(jq.query(jq.valuation.code, jq.valuation.pb_ratio, jq.valuation.market_cap, jq.indicator.roe).filter(jq.valuation.code == "000001.XSHE"), date="2025-05-15"))),
    ]
    payload = {
        "dataset": "joinquant_capability_probe",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "credential_policy": f"Credentials loaded only from {username_env}/{password_env} or an existing authenticated jqdatasdk session; credentials are not written.",
        "checks": [check() for check in checks],
        "notes": [
            "A passed check means the current account/session can access that interface in this environment.",
            "A failed check may indicate missing permission, quota exhaustion, package mismatch, network issue, or API change.",
            "Specialized bank_indicator is intentionally not probed because V5 treats it as unavailable for new workflows.",
        ],
    }
    path = out_dir / "joinquant_capability_probe.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
        handle.write("\n")
    return path


def _check(name: str, fn: Callable[[], Any]) -> Callable[[], dict[str, Any]]:
    def run() -> dict[str, Any]:
        try:
            sample = fn()
            return {"name": name, "status": "pass", "sample": sample}
        except Exception as exc:
            return {"name": name, "status": "fail", "error": repr(exc)}

    return run


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None or getattr(value, "empty", False):
        return []
    frame = value.reset_index()
    return frame.head(3).to_dict("records")


def _load_authenticated_jqdata(username_env: str, password_env: str):
    try:
        import jqdatasdk as jq
    except Exception as exc:
        raise RuntimeError("jqdatasdk is required for JoinQuant capability probing") from exc
    username = os.environ.get(username_env)
    password = os.environ.get(password_env)
    if username and password:
        jq.auth(username, password)
    if not jq.is_auth():
        raise RuntimeError(
            f"JoinQuant credentials are not available. Set {username_env} and {password_env}, "
            "or authenticate jqdatasdk in the current environment before running this probe."
        )
    return jq


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-joinquant-capability-probe")
    parser.add_argument("--out-dir", type=Path, default=Path("数据库/manifests"))
    args = parser.parse_args(argv)
    print(run_joinquant_capability_probe(args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
