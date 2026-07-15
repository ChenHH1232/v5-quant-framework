from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from v5.credential_loader import load_joinquant_credentials


DEFAULT_DATABASE_DIR = Path("数据库")
DEFAULT_OUT_DIR = DEFAULT_DATABASE_DIR / "processed" / "utilities_pit_panel"

UTILITY_INDUSTRIES = {
    "HY10001": "thermal_power",
    "HY10002": "hydropower",
    "HY10003": "nuclear_power",
    "HY10005": "gas",
    "HY10006": "heating_or_other_utility",
    "HY10007": "water",
    "HY10008": "grid",
    "HY10101": "thermal_power",
    "HY10102": "hydropower",
    "HY10103": "nuclear_power",
    "HY10107": "grid",
    "HY10108": "gas",
    "HY10109": "water",
    "HY10111": "heating_or_other_utility",
}

EXCLUDED_INDUSTRIES = {
    "HY10004": "new_energy_generation_excluded_in_test1",
    "HY10104": "wind_power_excluded_in_test1",
    "HY10105": "solar_power_excluded_in_test1",
    "HY10106": "other_energy_generation_excluded_in_test1",
    "HY10110": "municipal_sanitation_excluded_in_test1",
}

PANEL_FIELDS = [
    "trade_date",
    "code",
    "sub_industry",
    "close",
    "price_adjustment",
    "next_trade_date",
    "price_return",
    "dividend_return",
    "total_return",
    "future_return",
    "return_source",
    "low_price_to_book",
    "pe_ratio",
    "market_cap",
    "dividend_yield",
    "operating_cash_flow_yield",
    "return_on_equity_ttm",
    "gross_profit_margin",
    "net_profit_margin",
    "operating_cash_flow_to_net_profit",
    "interest_coverage",
    "capex_burden",
    "asset_liability_ratio",
    "factor_visible_date",
    "factor_visibility_source",
    "universe_visible_date",
    "universe_source",
    "dividend_visible_policy",
]


@dataclass(frozen=True)
class UtilitiesPitPanelResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    date_count: int
    code_count: int
    warning_count: int


def collect_utilities_pit_panel(
    out_dir: Path = DEFAULT_OUT_DIR,
    start_date: str = "2017-01-01",
    end_date: str = "2026-05-31",
    listing_age_days: int = 180,
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> UtilitiesPitPanelResult:
    jq = _load_authenticated_jqdata(username_env, password_env)
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    rebalance_dates = _quarterly_rebalance_dates(jq, start, end)
    if len(rebalance_dates) < 2:
        raise RuntimeError("not enough rebalance dates for V5.1 utilities validation")

    securities = jq.get_all_securities(types=["stock"], date=end)
    warnings: list[str] = []
    universe_by_date: dict[date, dict[str, str]] = {}
    for trade_day in rebalance_dates:
        universe_by_date[trade_day] = _utilities_universe_for_date(jq, securities, trade_day, listing_age_days, warnings)

    all_codes = sorted({code for universe in universe_by_date.values() for code in universe})
    if not all_codes:
        raise RuntimeError("utilities universe is empty")

    max_next_day = rebalance_dates[-1]
    price_end = _next_quarter_rebalance_date(jq, max_next_day)
    price_by_code: dict[str, dict[str, float]] = {}
    for code in all_codes:
        try:
            price_by_code[code] = _fetch_close_series(jq, code, rebalance_dates[0].isoformat(), price_end.isoformat(), fq="pre")
        except Exception as exc:
            warnings.append(f"{code}: price collection failed: {repr(exc)}")
            price_by_code[code] = {}

    fundamentals_by_date: dict[date, dict[str, dict[str, Any]]] = {}
    for trade_day in rebalance_dates:
        codes = sorted(universe_by_date[trade_day])
        try:
            fundamentals_by_date[trade_day] = _fetch_fundamentals(jq, codes, trade_day)
        except Exception as exc:
            warnings.append(f"{trade_day}: fundamentals collection failed: {repr(exc)}")
            fundamentals_by_date[trade_day] = {}

    rows: list[dict[str, Any]] = []
    for index, trade_day in enumerate(rebalance_dates):
        next_day = rebalance_dates[index + 1] if index + 1 < len(rebalance_dates) else price_end
        for code, sub_industry in sorted(universe_by_date[trade_day].items()):
            close = _value_as_of(price_by_code.get(code, {}), trade_day)
            next_close = _value_as_of(price_by_code.get(code, {}), next_day)
            if close is None or next_close is None or close <= 0:
                continue
            price_return = next_close / close - 1.0
            fundamentals = fundamentals_by_date.get(trade_day, {}).get(code, {})
            market_cap_cny = _market_cap_cny(fundamentals.get("market_cap"))
            operating_cash_flow = _to_float(fundamentals.get("net_operate_cash_flow"))
            capex = abs(_to_float(fundamentals.get("fix_intan_other_asset_acqui_cash")) or 0.0)
            net_profit = _to_float(fundamentals.get("net_profit"))
            operating_profit = _to_float(fundamentals.get("operating_profit"))
            interest_expense = _to_float(fundamentals.get("interest_expense"))
            financial_expense = _to_float(fundamentals.get("financial_expense"))
            total_assets = _to_float(fundamentals.get("total_assets"))
            total_liability = _to_float(fundamentals.get("total_liability"))
            rows.append(
                {
                    "trade_date": trade_day.isoformat(),
                    "code": code,
                    "sub_industry": sub_industry,
                    "close": _fmt_float(close),
                    "price_adjustment": "pre_adjusted_price",
                    "next_trade_date": next_day.isoformat(),
                    "price_return": _fmt_float(price_return),
                    "dividend_return": "",
                    "total_return": _fmt_float(price_return),
                    "future_return": _fmt_float(price_return),
                    "return_source": "jqdata_pre_adjusted_total_return",
                    "low_price_to_book": _fmt_float(fundamentals.get("pb_ratio")),
                    "pe_ratio": _fmt_float(fundamentals.get("pe_ratio")),
                    "market_cap": _fmt_float(fundamentals.get("market_cap")),
                    "dividend_yield": _fmt_float(fundamentals.get("dividend_ratio")),
                    "operating_cash_flow_yield": _fmt_float(_ratio(operating_cash_flow, market_cap_cny)),
                    "return_on_equity_ttm": _fmt_float(fundamentals.get("roe")),
                    "gross_profit_margin": _fmt_float(fundamentals.get("gross_profit_margin")),
                    "net_profit_margin": _fmt_float(fundamentals.get("net_profit_margin")),
                    "operating_cash_flow_to_net_profit": _fmt_float(_ratio(operating_cash_flow, net_profit)),
                    "interest_coverage": _fmt_float(_interest_coverage(operating_profit, operating_cash_flow, interest_expense, financial_expense)),
                    "capex_burden": _fmt_float(_ratio(capex, operating_cash_flow)),
                    "asset_liability_ratio": _fmt_float(_ratio(total_liability, total_assets)),
                    "factor_visible_date": trade_day.isoformat(),
                    "factor_visibility_source": "jqdatasdk.get_fundamentals(date=trade_date)",
                    "universe_visible_date": trade_day.isoformat(),
                    "universe_source": "jqdatasdk.get_industry_stocks(jq_l2_core_utilities)",
                    "dividend_visible_policy": "valuation.dividend_ratio_as_of_trade_date",
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel.csv"
    manifest_path = out_dir / "collection_manifest.json"
    _write_csv(panel_path, PANEL_FIELDS, rows)
    manifest = {
        "dataset": "utilities_pit_panel",
        "panel": str(panel_path),
        "start_date": start_date,
        "end_date": end_date,
        "listing_age_days": listing_age_days,
        "included_industries": UTILITY_INDUSTRIES,
        "excluded_industries": EXCLUDED_INDUSTRIES,
        "row_count": len(rows),
        "date_count": len({row["trade_date"] for row in rows}),
        "code_count": len({row["code"] for row in rows}),
        "rebalance_dates": [day.isoformat() for day in rebalance_dates],
        "fields": PANEL_FIELDS,
        "warnings": warnings,
        "limitations": [
            "JoinQuant jq_l2 industry membership starts in 2016 and changes classification codes around 2021; this runner accepts both legacy HY100xx and newer HY101xx core utility operating industries.",
            "Wind, solar, other new-energy generation, and municipal sanitation are excluded from Test-1 to keep the first utilities test economically narrow.",
            "Financial fields use jqdatasdk.get_fundamentals(date=trade_date) as PIT visibility. Original field-level announcement dates are not yet exported in this panel.",
            "Stock returns use pre-adjusted close-to-close returns. dividend_ratio is used as a visible factor, while dividend cash attribution is not separately decomposed in this first research panel.",
        ],
        "credential_policy": f"Credentials loaded from {username_env}/{password_env} or the configured local credential file. Credentials are never written.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "agent_access": ["Research Agent", "Quant Validation Agent"],
    }
    _write_json(manifest_path, manifest)
    return UtilitiesPitPanelResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        date_count=len({row["trade_date"] for row in rows}),
        code_count=len({row["code"] for row in rows}),
        warning_count=len(warnings),
    )


def _utilities_universe_for_date(jq: Any, securities: Any, trade_day: date, listing_age_days: int, warnings: list[str]) -> dict[str, str]:
    universe: dict[str, str] = {}
    for industry_code, sub_industry in UTILITY_INDUSTRIES.items():
        try:
            codes = jq.get_industry_stocks(industry_code, date=trade_day)
        except Exception as exc:
            warnings.append(f"{trade_day}:{industry_code}: industry membership failed: {repr(exc)}")
            continue
        for code in codes:
            if _is_listed_and_mature(securities, code, trade_day, listing_age_days):
                universe[code] = sub_industry
    return universe


def _is_listed_and_mature(securities: Any, code: str, trade_day: date, listing_age_days: int) -> bool:
    if code not in securities.index:
        return False
    row = securities.loc[code]
    start_date = _to_date(row.get("start_date"))
    end_date = _to_date(row.get("end_date"))
    if start_date is None:
        return False
    if start_date + timedelta(days=listing_age_days) > trade_day:
        return False
    if end_date is not None and end_date < trade_day:
        return False
    return True


def _quarterly_rebalance_dates(jq: Any, start: date, end: date) -> list[date]:
    anchors: list[date] = []
    for year in range(start.year, end.year + 1):
        for month in [1, 4, 7, 10]:
            anchor = date(year, month, 1)
            if start <= anchor <= end:
                anchors.append(anchor)
    trade_days = [_to_date(day) for day in jq.get_trade_days(start_date=start.isoformat(), end_date=end.isoformat())]
    trade_days = [day for day in trade_days if day is not None]
    result = []
    for anchor in anchors:
        next_days = [day for day in trade_days if day >= anchor]
        if next_days:
            result.append(next_days[0])
    return sorted(set(result))


def _next_quarter_rebalance_date(jq: Any, current: date) -> date:
    month = ((current.month - 1) // 3 + 1) * 3 + 1
    year = current.year
    if month > 12:
        month = 1
        year += 1
    anchor = date(year, month, 1)
    trade_days = [_to_date(day) for day in jq.get_trade_days(start_date=anchor.isoformat(), end_date=(anchor + timedelta(days=20)).isoformat())]
    trade_days = [day for day in trade_days if day is not None and day >= anchor]
    if not trade_days:
        return current
    return trade_days[0]


def _fetch_fundamentals(jq: Any, codes: list[str], trade_day: date) -> dict[str, dict[str, Any]]:
    if not codes:
        return {}
    df = jq.get_fundamentals(
        jq.query(
            jq.valuation.code,
            jq.valuation.pb_ratio,
            jq.valuation.pe_ratio,
            jq.valuation.market_cap,
            jq.valuation.dividend_ratio,
            jq.indicator.roe,
            jq.indicator.gross_profit_margin,
            jq.indicator.net_profit_margin,
            jq.indicator.ocf_to_operating_profit,
            jq.cash_flow.net_operate_cash_flow,
            jq.cash_flow.fix_intan_other_asset_acqui_cash,
            jq.income.net_profit,
            jq.income.operating_profit,
            jq.income.operating_revenue,
            jq.income.interest_expense,
            jq.income.financial_expense,
            jq.balance.total_assets,
            jq.balance.total_liability,
        ).filter(jq.valuation.code.in_(codes)),
        date=trade_day,
    )
    if df is None or getattr(df, "empty", True):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in df.to_dict("records"):
        code = str(row.get("code") or "")
        if code:
            result[code] = row
    return result


def _fetch_close_series(jq: Any, code: str, start_date: str, end_date: str, fq: str | None) -> dict[str, float]:
    df = jq.get_price(
        code,
        start_date=start_date,
        end_date=end_date,
        frequency="daily",
        fields=["close"],
        fq=fq,
        skip_paused=False,
        fill_paused=True,
        panel=False,
    )
    if df is None or getattr(df, "empty", True):
        return {}
    result: dict[str, float] = {}
    for index, row in df.iterrows():
        value = _to_float(row.get("close"))
        if value is not None:
            result[str(index)[:10]] = value
    return result


def _load_authenticated_jqdata(username_env: str, password_env: str):
    try:
        import jqdatasdk as jq
    except Exception as exc:
        raise RuntimeError("jqdatasdk is required for utilities PIT panel collection") from exc
    username, password = load_joinquant_credentials(username_env, password_env)
    if username and password:
        jq.auth(username, password)
    if not jq.is_auth():
        raise RuntimeError("JoinQuant credentials are not available for utilities PIT panel collection")
    return jq


def _value_as_of(values: dict[str, float], day: date) -> float | None:
    key = day.isoformat()
    if key in values:
        return values[key]
    candidates = [item for item in values if item <= key]
    if not candidates:
        return None
    return values[max(candidates)]


def _interest_coverage(operating_profit: float | None, operating_cash_flow: float | None, interest_expense: float | None, financial_expense: float | None) -> float | None:
    denominator = abs(interest_expense) if interest_expense not in (None, 0) else abs(financial_expense or 0.0)
    if denominator <= 0:
        return None
    numerator = operating_profit if operating_profit is not None else operating_cash_flow
    return _ratio(numerator, denominator)


def _market_cap_cny(market_cap: Any) -> float | None:
    value = _to_float(market_cap)
    if value is None:
        return None
    return value * 100_000_000.0


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _to_date(value: Any) -> date | None:
    if value in {None, ""}:
        return None
    if hasattr(value, "date"):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _parse_date(value: str) -> date:
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_float(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return ""
    return f"{numeric:.10g}"


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-utilities-pit-panel")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start-date", default="2017-01-01")
    parser.add_argument("--end-date", default="2026-05-31")
    parser.add_argument("--listing-age-days", type=int, default=180)
    args = parser.parse_args(argv)
    result = collect_utilities_pit_panel(
        out_dir=args.out_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        listing_age_days=args.listing_age_days,
    )
    print(result.panel_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
