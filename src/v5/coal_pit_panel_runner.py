from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from v5.coal_external_state_runner import latest_visible_state_values
from v5.credential_loader import load_joinquant_credentials


DEFAULT_DATABASE_DIR = Path("数据库")
DEFAULT_OUT_DIR = DEFAULT_DATABASE_DIR / "processed" / "coal_pit_panel"
DEFAULT_STATE_PANEL = DEFAULT_DATABASE_DIR / "processed" / "coal_external_state" / "coal_external_state.csv"

COAL_INDUSTRIES = {
    "HY01107": "jq_l2_coal",
    "801951": "sw_l2_coal_mining",
    "B06": "csrc_coal_mining_washing",
}

EXCLUDED_INDUSTRIES = {
    "C25": "coal_chemical_processing_exclusion_review",
    "HY03129": "mining_metallurgy_machinery_exclusion_review",
}

MANUAL_BUSINESS_TAGS = {
    "000552.XSHE": "core_coal",
    "000571.XSHE": "mixed_or_special_review",
    "000937.XSHE": "core_coal",
    "000983.XSHE": "core_coal",
    "002128.XSHE": "mixed_power_coal",
    "600121.XSHG": "core_coal",
    "600123.XSHG": "core_coal",
    "600188.XSHG": "core_coal",
    "600256.XSHG": "mixed_energy",
    "600348.XSHG": "core_coal",
    "600395.XSHG": "core_coal",
    "600403.XSHG": "core_coal",
    "600508.XSHG": "core_coal",
    "600546.XSHG": "core_coal",
    "600726.XSHG": "mixed_power_coal",
    "600758.XSHG": "mixed_power_coal",
    "600925.XSHG": "core_coal",
    "600971.XSHG": "core_coal",
    "600985.XSHG": "core_coal",
    "600997.XSHG": "mixed_coal_chemical",
    "601001.XSHG": "core_coal",
    "601088.XSHG": "integrated_coal_power_transport",
    "601101.XSHG": "core_coal",
    "601225.XSHG": "core_coal",
    "601666.XSHG": "core_coal",
    "601699.XSHG": "core_coal",
    "601898.XSHG": "core_coal",
    "601918.XSHG": "core_coal",
}

PANEL_FIELDS = [
    "trade_date",
    "code",
    "company_name",
    "sub_industry",
    "coal_business_tag",
    "is_core_coal_numeric",
    "close",
    "price_adjustment",
    "next_trade_date",
    "price_return",
    "dividend_return",
    "total_return",
    "future_return",
    "return_source",
    "low_price_to_book",
    "low_price_to_earnings",
    "price_to_earnings",
    "market_cap",
    "dividend_yield",
    "payout_ratio",
    "operating_cash_flow_yield",
    "free_cash_flow_yield",
    "profit_growth_yoy",
    "return_on_equity_ttm",
    "gross_profit_margin",
    "net_profit_margin",
    "operating_cash_flow_to_net_profit",
    "interest_coverage",
    "capex_burden",
    "asset_liability_ratio",
    "thermal_coal_price_state",
    "coking_coal_price_state",
    "coal_inventory_or_output_state",
    "coal_power_spread_state",
    "coal_oil_power_price_index_state",
    "coal_oil_power_price_yoy_state",
    "factor_visible_date",
    "factor_visibility_source",
    "universe_visible_date",
    "universe_source",
    "business_tag_visible_date",
    "business_tag_source",
    "external_state_visible_date",
    "external_state_source",
    "dividend_visible_policy",
]


@dataclass(frozen=True)
class CoalPitPanelResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    date_count: int
    code_count: int
    warning_count: int


def collect_coal_pit_panel(
    out_dir: Path = DEFAULT_OUT_DIR,
    state_panel: Path | None = DEFAULT_STATE_PANEL,
    start_date: str = "2015-07-01",
    end_date: str = "2026-05-31",
    listing_age_days: int = 180,
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> CoalPitPanelResult:
    jq = _load_authenticated_jqdata(username_env, password_env)
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    rebalance_dates = _quarterly_rebalance_dates(jq, start, end)
    if len(rebalance_dates) < 2:
        raise RuntimeError("not enough rebalance dates for V5.2 coal validation")

    warnings: list[str] = []
    universe_by_date: dict[date, dict[str, dict[str, str]]] = {}
    for trade_day in rebalance_dates:
        universe_by_date[trade_day] = _coal_universe_for_date(jq, trade_day, listing_age_days, warnings)

    all_codes = sorted({code for universe in universe_by_date.values() for code in universe})
    if not all_codes:
        raise RuntimeError("coal universe is empty")

    price_end = _next_quarter_rebalance_date(jq, rebalance_dates[-1])
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

    state_by_trade_date = {}
    if state_panel is not None and state_panel.exists():
        state_by_trade_date = latest_visible_state_values(state_panel, [day.isoformat() for day in rebalance_dates])
    else:
        warnings.append("coal external state panel missing; external state fields will be empty")

    rows: list[dict[str, Any]] = []
    for index, trade_day in enumerate(rebalance_dates):
        next_day = rebalance_dates[index + 1] if index + 1 < len(rebalance_dates) else price_end
        state_values = state_by_trade_date.get(trade_day.isoformat(), {})
        for code, membership in sorted(universe_by_date[trade_day].items()):
            close = _value_as_of(price_by_code.get(code, {}), trade_day)
            next_close = _value_as_of(price_by_code.get(code, {}), next_day)
            if close is None or next_close is None or close <= 0:
                continue
            price_return = next_close / close - 1.0
            fundamentals = fundamentals_by_date.get(trade_day, {}).get(code, {})
            market_cap_cny = _market_cap_cny(fundamentals.get("market_cap"))
            operating_cash_flow = _to_float(fundamentals.get("net_operate_cash_flow"))
            capex = abs(_to_float(fundamentals.get("fix_intan_other_asset_acqui_cash")) or 0.0)
            free_cash_flow = None if operating_cash_flow is None else operating_cash_flow - capex
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
                    "company_name": membership.get("company_name", ""),
                    "sub_industry": membership.get("sub_industry", ""),
                    "coal_business_tag": membership.get("coal_business_tag", ""),
                    "is_core_coal_numeric": "1" if membership.get("coal_business_tag") == "core_coal" else "0",
                    "close": _fmt_float(close),
                    "price_adjustment": "pre_adjusted_price",
                    "next_trade_date": next_day.isoformat(),
                    "price_return": _fmt_float(price_return),
                    "dividend_return": "",
                    "total_return": _fmt_float(price_return),
                    "future_return": _fmt_float(price_return),
                    "return_source": "jqdata_pre_adjusted_total_return",
                    "low_price_to_book": _fmt_float(fundamentals.get("pb_ratio")),
                    "low_price_to_earnings": _fmt_float(fundamentals.get("pe_ratio")),
                    "price_to_earnings": _fmt_float(fundamentals.get("pe_ratio")),
                    "market_cap": _fmt_float(fundamentals.get("market_cap")),
                    "dividend_yield": _fmt_float(fundamentals.get("dividend_ratio")),
                    "payout_ratio": _fmt_float(_ratio(_to_float(fundamentals.get("dividend_ratio")), _to_float(fundamentals.get("pe_ratio")))),
                    "operating_cash_flow_yield": _fmt_float(_ratio(operating_cash_flow, market_cap_cny)),
                    "free_cash_flow_yield": _fmt_float(_ratio(free_cash_flow, market_cap_cny)),
                    "profit_growth_yoy": _fmt_float(fundamentals.get("inc_net_profit_year_on_year")),
                    "return_on_equity_ttm": _fmt_float(fundamentals.get("roe")),
                    "gross_profit_margin": _fmt_float(fundamentals.get("gross_profit_margin")),
                    "net_profit_margin": _fmt_float(fundamentals.get("net_profit_margin")),
                    "operating_cash_flow_to_net_profit": _fmt_float(_ratio(operating_cash_flow, net_profit)),
                    "interest_coverage": _fmt_float(_interest_coverage(operating_profit, operating_cash_flow, interest_expense, financial_expense)),
                    "capex_burden": _fmt_float(_ratio(capex, operating_cash_flow)),
                    "asset_liability_ratio": _fmt_float(_ratio(total_liability, total_assets)),
                    "thermal_coal_price_state": state_values.get("thermal_coal_price_state", ""),
                    "coking_coal_price_state": state_values.get("coking_coal_price_state", ""),
                    "coal_inventory_or_output_state": state_values.get("coal_inventory_or_output_state", ""),
                    "coal_power_spread_state": state_values.get("coal_power_spread_state", ""),
                    "coal_oil_power_price_index_state": state_values.get("coal_oil_power_price_index_state", ""),
                    "coal_oil_power_price_yoy_state": state_values.get("coal_oil_power_price_yoy_state", ""),
                    "factor_visible_date": trade_day.isoformat(),
                    "factor_visibility_source": "jqdatasdk.get_fundamentals(date=trade_date)",
                    "universe_visible_date": trade_day.isoformat(),
                    "universe_source": membership.get("universe_source", ""),
                    "business_tag_visible_date": trade_day.isoformat(),
                    "business_tag_source": "manual_v52_initial_classification_requires_company_report_audit",
                    "external_state_visible_date": _state_visible_dates(state_values),
                    "external_state_source": _state_sources(state_values),
                    "dividend_visible_policy": "valuation.dividend_ratio_as_of_trade_date",
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel.csv"
    manifest_path = out_dir / "collection_manifest.json"
    _write_csv(panel_path, PANEL_FIELDS, rows)
    manifest = {
        "dataset": "coal_pit_panel",
        "panel": str(panel_path),
        "state_panel": str(state_panel) if state_panel else None,
        "start_date": start_date,
        "end_date": end_date,
        "listing_age_days": listing_age_days,
        "included_industries": COAL_INDUSTRIES,
        "excluded_industries": EXCLUDED_INDUSTRIES,
        "manual_business_tags": MANUAL_BUSINESS_TAGS,
        "row_count": len(rows),
        "date_count": len({row["trade_date"] for row in rows}),
        "code_count": len({row["code"] for row in rows}),
        "rebalance_dates": [day.isoformat() for day in rebalance_dates],
        "fields": PANEL_FIELDS,
        "warnings": warnings,
        "limitations": [
            "Industry membership uses JoinQuant/DataJQ industry membership as of each rebalance date, but manual coal_business_tag values still require company-report visible-date audit before formal acceptance.",
            "Financial fields use jqdatasdk.get_fundamentals(date=trade_date) as PIT visibility. Original field-level announcement dates are not exported in this first V5.2 panel.",
            "Stock returns use pre-adjusted close-to-close returns. Dividend cash attribution is not separately decomposed in this research panel.",
            "External coal state is preliminary proxy data unless the source review status says otherwise.",
        ],
        "credential_policy": f"Credentials loaded from {username_env}/{password_env} or the configured local credential file. Credentials are never written.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "agent_access": ["Research Agent", "Quant Validation Agent"],
    }
    _write_json(manifest_path, manifest)
    return CoalPitPanelResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        date_count=len({row["trade_date"] for row in rows}),
        code_count=len({row["code"] for row in rows}),
        warning_count=len(warnings),
    )


def _coal_universe_for_date(jq: Any, trade_day: date, listing_age_days: int, warnings: list[str]) -> dict[str, dict[str, str]]:
    securities = jq.get_all_securities(types=["stock"], date=trade_day)
    exclusion_codes = _exclusion_codes_for_date(jq, trade_day, warnings)
    universe: dict[str, dict[str, str]] = {}
    for industry_code, source_name in COAL_INDUSTRIES.items():
        try:
            codes = jq.get_industry_stocks(industry_code, date=trade_day)
        except Exception as exc:
            warnings.append(f"{trade_day}:{industry_code}: industry membership failed: {repr(exc)}")
            continue
        for code in codes:
            if code in exclusion_codes and code not in MANUAL_BUSINESS_TAGS:
                continue
            if not _is_listed_and_mature(securities, code, trade_day, listing_age_days):
                continue
            row = securities.loc[code]
            universe[code] = {
                "company_name": str(row.get("display_name") or row.get("name") or ""),
                "sub_industry": source_name,
                "coal_business_tag": MANUAL_BUSINESS_TAGS.get(code, "manual_review_required"),
                "universe_source": "union:" + ";".join(sorted({source_name, universe.get(code, {}).get("universe_source", "")} - {""})),
            }
    return universe


def _exclusion_codes_for_date(jq: Any, trade_day: date, warnings: list[str]) -> set[str]:
    result: set[str] = set()
    for industry_code in EXCLUDED_INDUSTRIES:
        try:
            result.update(jq.get_industry_stocks(industry_code, date=trade_day))
        except Exception as exc:
            warnings.append(f"{trade_day}:{industry_code}: exclusion industry failed: {repr(exc)}")
    return result


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
            jq.indicator.inc_net_profit_year_on_year,
            jq.cash_flow.net_operate_cash_flow,
            jq.cash_flow.fix_intan_other_asset_acqui_cash,
            jq.income.net_profit,
            jq.income.operating_profit,
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
        raise RuntimeError("jqdatasdk is required for coal PIT panel collection") from exc
    username, password = load_joinquant_credentials(username_env, password_env)
    if username and password:
        jq.auth(username, password)
    if not jq.is_auth():
        raise RuntimeError("JoinQuant credentials are not available for coal PIT panel collection")
    return jq


def _value_as_of(values: dict[str, float], day: date) -> float | None:
    key = day.isoformat()
    if key in values:
        return values[key]
    candidates = [item for item in values if item <= key]
    if not candidates:
        return None
    return values[max(candidates)]


def _state_visible_dates(state_values: dict[str, str]) -> str:
    return ";".join(sorted(value for key, value in state_values.items() if key.endswith("_visible_date") and value))


def _state_sources(state_values: dict[str, str]) -> str:
    return ";".join(sorted(set(value for key, value in state_values.items() if key.endswith("_source") and value)))


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
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


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
    parser = argparse.ArgumentParser(prog="v5-coal-pit-panel")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--state-panel", type=Path, default=DEFAULT_STATE_PANEL)
    parser.add_argument("--start-date", default="2015-07-01")
    parser.add_argument("--end-date", default="2026-05-31")
    parser.add_argument("--listing-age-days", type=int, default=180)
    args = parser.parse_args(argv)
    result = collect_coal_pit_panel(
        out_dir=args.out_dir,
        state_panel=args.state_panel,
        start_date=args.start_date,
        end_date=args.end_date,
        listing_age_days=args.listing_age_days,
    )
    print(result.panel_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
