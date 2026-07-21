from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from v5.credential_loader import load_joinquant_credentials
from v5.paths import DEFAULT_DATABASE_DIR


DEFAULT_OUT_ROOT = DEFAULT_DATABASE_DIR / "processed" / "similar_sector_pit_panel_v55"


SECTOR_CONFIGS: dict[str, dict[str, Any]] = {
    "telecom_operators": {
        "description": "A-share telecom network operators. Equipment and theme companies are excluded.",
        "explicit_codes": {
            "600050.XSHG": "china_unicom",
            "601728.XSHG": "china_telecom",
            "600941.XSHG": "china_mobile",
        },
        "industry_codes": {},
        "benchmark_policy": "equal_weight_core_operator_pool",
        "limitations": [
            "Only three A-share core operators are included, so IC / RankIC is sample-size constrained.",
            "Formal validation should be interpreted as basket evidence, not broad cross-sectional factor evidence.",
        ],
    },
    "gas_water_operators": {
        "description": "A-share gas and water utility operators. Engineering, equipment and project-contracting names require later purity review.",
        "explicit_codes": {},
        "industry_codes": {
            "HY10005": "gas_legacy",
            "HY10007": "water_legacy",
            "HY10108": "gas",
            "HY10109": "water",
        },
        "benchmark_policy": "equal_weight_same_pool_until_pure_index_confirmed",
        "limitations": [
            "JoinQuant industry membership is used as first-layer PIT universe evidence.",
            "Operating-purity review is still required before Engineering Agent can receive a frozen candidate.",
        ],
    },
    "port_rail_infrastructure": {
        "description": "A-share port and railway infrastructure operators. Airlines, shipping carriers, logistics and highway names are excluded.",
        "explicit_codes": {},
        "industry_codes": {
            "HY03155": "railway_transport",
            "HY03159": "port",
        },
        "benchmark_policy": "equal_weight_same_pool_until_transport_subindex_confirmed",
        "limitations": [
            "Port and railway operators have freight / trade-cycle exposure; operating-state data is required before formal candidacy.",
            "This first panel does not yet join cargo throughput, freight volume or regional trade state.",
        ],
    },
    "airport_transport_operators": {
        "description": "A-share airport infrastructure operators. Airlines, logistics, shipping and aircraft/airport equipment names are excluded.",
        "explicit_codes": {
            "600009.XSHG": "shanghai_airport",
            "600004.XSHG": "baiyun_airport",
            "000089.XSHE": "shenzhen_airport",
            "600897.XSHG": "xiamen_airport",
            "600515.XSHG": "hainan_airport",
        },
        "industry_codes": {
            "HY03158": "airport",
        },
        "benchmark_policy": "equal_weight_core_airport_operator_pool_until_pure_index_confirmed",
        "limitations": [
            "Airport operators are recovery-cycle assets; passenger throughput, international-route recovery, duty-free/rental exposure and policy state are required before formal modeling.",
            "The explicit airport list is a research starting point and must be PIT-audited against annual-report business exposure before Engineering handoff.",
            "Airlines and aviation fuel / FX-cycle exposures are intentionally excluded from this operator panel.",
        ],
    },
    "oil_gas_pipeline_integrated": {
        "description": "A-share oil / gas upstream, integrated, refining and oil / gas distribution candidates. Oilfield services are excluded from the first dividend cash-flow universe.",
        "explicit_codes": {},
        "industry_codes": {
            "HY01103": "integrated_oil_gas",
            "HY01104": "fuel_refining",
            "HY01105": "natural_gas_processing",
            "HY01106": "oil_gas_distribution_other",
        },
        "benchmark_policy": "equal_weight_same_pool_until_oil_gas_subindex_confirmed",
        "limitations": [
            "This is a first-layer cycle-aware candidate universe, not a formal strategy universe.",
            "Oilfield services are intentionally excluded because their economics are mostly oil-company capex beta rather than dividend low-volatility cash-flow evidence.",
            "Natural-gas processing may overlap with gas / water operators and must be split later by PIT business-exposure tags.",
            "Formal validation is blocked until oil price, gas price, refining spread, pipeline tariff / policy state and PIT business-exposure tags are joined.",
        ],
    },
    "building_materials_cement": {
        "description": "A-share cement manufacturing companies. Glass and other building-material names are excluded from the first cycle-aware cash-flow universe.",
        "explicit_codes": {},
        "industry_codes": {
            "801711": "sw_cement_manufacturing",
        },
        "benchmark_policy": "equal_weight_cement_manufacturing_pool_until_pure_index_confirmed",
        "limitations": [
            "This is a first-layer cement universe, not a formal strategy universe.",
            "Formal validation is blocked until cement price, output, demand, energy-cost and capex-policy states are joined.",
            "Glass and other building-material companies are intentionally excluded from this first cement-specific panel.",
        ],
    },
    "food_beverage": {
        "description": "A-share food and beverage companies. Liquor, dairy, condiments and packaged food must be separated before formal validation.",
        "explicit_codes": {},
        "industry_codes": {
            "801125": "sw_liquor",
            "801126": "sw_non_liquor_alcohol",
            "801127": "sw_beverage_dairy",
            "801124": "sw_food_processing",
            "801128": "sw_snack_food",
            "801129": "sw_condiments",
        },
        "benchmark_policy": "equal_weight_food_beverage_pool_with_subsector_split",
        "limitations": [
            "Subsector concentration can dominate broad food/beverage IC results.",
            "Formal validation requires working-capital, inventory, channel and reinvestment-quality gates.",
        ],
    },
    "home_appliances": {
        "description": "A-share home-appliance companies. White goods, kitchen appliances, small appliances and appliance components are tagged separately.",
        "explicit_codes": {},
        "industry_codes": {
            "801111": "sw_white_goods",
            "801112": "sw_audio_visual_equipment",
            "801113": "sw_small_appliances",
            "801114": "sw_kitchen_bath_appliances",
            "801115": "sw_lighting_equipment",
            "801116": "sw_appliance_components",
            "801117": "sw_other_appliances",
        },
        "benchmark_policy": "equal_weight_home_appliances_pool_with_subsector_split",
        "limitations": [
            "Formal validation requires property-cycle, export-cycle, inventory and raw-material-cost state checks.",
            "Component suppliers and brand operators should be audited separately before Engineering handoff.",
        ],
    },
    "consumer_staples_cashflow": {
        "description": "A-share broad consumer-staples cash-flow universe using JoinQuant primary-consumption industry as a first-layer parent pool.",
        "explicit_codes": {},
        "industry_codes": {
            "HY005": "jq_primary_consumption",
        },
        "benchmark_policy": "equal_weight_primary_consumption_pool_until_quality_subset_confirmed",
        "limitations": [
            "This broad parent pool can mix food, beverage, agriculture and consumer-product names.",
            "Formal validation requires a business-quality screen and working-capital/capex gate before broad IC conclusions.",
        ],
    },
    "pharma_medical_services": {
        "description": "A-share pharma and medical-services candidates. Chemical drugs, biological products, devices, services, TCM and distribution are tagged separately.",
        "explicit_codes": {},
        "industry_codes": {
            "801151": "sw_chemical_pharma",
            "801152": "sw_biologics",
            "801153": "sw_medical_devices",
            "801154": "sw_pharma_distribution",
            "801155": "sw_traditional_chinese_medicine",
            "801156": "sw_medical_services",
        },
        "benchmark_policy": "equal_weight_pharma_medical_pool_with_subsector_split",
        "limitations": [
            "Formal validation requires policy, procurement, R&D and subsector gates.",
            "Raw FCF is diagnostic only until R&D and capex treatment is reviewed.",
        ],
    },
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
    "benchmark_return",
    "benchmark_source",
    "low_price_to_book",
    "pe_ratio",
    "market_cap",
    "dividend_yield",
    "revenue_growth_yoy",
    "total_revenue_growth_yoy",
    "ocf_to_revenue",
    "cash_collection_quality",
    "operating_cash_flow_yield",
    "free_cash_flow_yield",
    "return_on_equity_ttm",
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
class SimilarSectorPitPanelResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    date_count: int
    code_count: int
    warning_count: int


def collect_similar_sector_pit_panel(
    sector: str,
    out_root: Path = DEFAULT_OUT_ROOT,
    start_date: str = "2021-05-01",
    end_date: str = "2026-05-31",
    listing_age_days: int = 180,
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> SimilarSectorPitPanelResult:
    if sector not in SECTOR_CONFIGS:
        supported = ", ".join(sorted(SECTOR_CONFIGS))
        raise ValueError(f"unsupported similar sector '{sector}'. Supported: {supported}")
    config = SECTOR_CONFIGS[sector]
    jq = _load_authenticated_jqdata(username_env, password_env)
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    rebalance_dates = _quarterly_rebalance_dates(jq, start, end)
    if len(rebalance_dates) < 2:
        raise RuntimeError(f"not enough rebalance dates for {sector}")

    securities = jq.get_all_securities(types=["stock"], date=end)
    warnings: list[str] = []
    universe_by_date: dict[date, dict[str, str]] = {}
    for trade_day in rebalance_dates:
        universe_by_date[trade_day] = _universe_for_date(jq, securities, config, trade_day, listing_age_days, warnings)

    all_codes = sorted({code for universe in universe_by_date.values() for code in universe})
    if not all_codes:
        raise RuntimeError(f"{sector} universe is empty")

    price_start = rebalance_dates[0].isoformat()
    price_end = _next_quarter_rebalance_date(jq, rebalance_dates[-1])
    price_by_code: dict[str, dict[str, float]] = {}
    for code in all_codes:
        try:
            price_by_code[code] = _fetch_close_series(jq, code, price_start, price_end.isoformat(), fq="pre")
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
        date_pool = universe_by_date[trade_day]
        equal_weight_return_parts: list[float] = []
        staged_rows: list[dict[str, Any]] = []
        for code, sub_industry in sorted(date_pool.items()):
            close = _value_as_of(price_by_code.get(code, {}), trade_day)
            next_close = _value_as_of(price_by_code.get(code, {}), next_day)
            if close is None or next_close is None or close <= 0:
                continue
            price_return = next_close / close - 1.0
            equal_weight_return_parts.append(price_return)
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
            staged_rows.append(
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
                    "benchmark_return": "",
                    "benchmark_source": config["benchmark_policy"],
                    "low_price_to_book": _fmt_float(fundamentals.get("pb_ratio")),
                    "pe_ratio": _fmt_float(fundamentals.get("pe_ratio")),
                    "market_cap": _fmt_float(fundamentals.get("market_cap")),
                    "dividend_yield": _fmt_float(fundamentals.get("dividend_ratio")),
                    "revenue_growth_yoy": _fmt_float(fundamentals.get("inc_revenue_year_on_year")),
                    "total_revenue_growth_yoy": _fmt_float(fundamentals.get("inc_total_revenue_year_on_year")),
                    "ocf_to_revenue": _fmt_float(fundamentals.get("ocf_to_revenue")),
                    "cash_collection_quality": _fmt_float(fundamentals.get("goods_sale_and_service_to_revenue")),
                    "operating_cash_flow_yield": _fmt_float(_ratio(operating_cash_flow, market_cap_cny)),
                    "free_cash_flow_yield": _fmt_float(_ratio(free_cash_flow, market_cap_cny)),
                    "return_on_equity_ttm": _fmt_float(fundamentals.get("roe")),
                    "operating_cash_flow_to_net_profit": _fmt_float(_ratio(operating_cash_flow, net_profit)),
                    "interest_coverage": _fmt_float(_interest_coverage(operating_profit, operating_cash_flow, interest_expense, financial_expense)),
                    "capex_burden": _fmt_float(_ratio(capex, operating_cash_flow)),
                    "asset_liability_ratio": _fmt_float(_ratio(total_liability, total_assets)),
                    "factor_visible_date": trade_day.isoformat(),
                    "factor_visibility_source": "jqdatasdk.get_fundamentals(date=trade_date)",
                    "universe_visible_date": trade_day.isoformat(),
                    "universe_source": _universe_source(config),
                    "dividend_visible_policy": "valuation.dividend_ratio_as_of_trade_date",
                }
            )
        equal_weight_return = sum(equal_weight_return_parts) / len(equal_weight_return_parts) if equal_weight_return_parts else None
        for row in staged_rows:
            row["benchmark_return"] = _fmt_float(equal_weight_return)
            rows.append(row)

    out_dir = out_root / sector
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel.csv"
    manifest_path = out_dir / "collection_manifest.json"
    _write_csv(panel_path, PANEL_FIELDS, rows)
    manifest = {
        "dataset": f"{sector}_initial_pit_panel_v55",
        "sector": sector,
        "description": config["description"],
        "panel": str(panel_path),
        "start_date": start_date,
        "end_date": end_date,
        "listing_age_days": listing_age_days,
        "explicit_codes": config["explicit_codes"],
        "industry_codes": config["industry_codes"],
        "row_count": len(rows),
        "date_count": len({row["trade_date"] for row in rows}),
        "code_count": len({row["code"] for row in rows}),
        "rebalance_dates": [day.isoformat() for day in rebalance_dates],
        "fields": PANEL_FIELDS,
        "warnings": warnings,
        "limitations": [
            "This is a V5.5 prelaunch initial-model panel, not final platform replication data.",
            "Financial fields use jqdatasdk.get_fundamentals(date=trade_date) as PIT visibility; field-level original announcement dates are not exported yet.",
            "Stock returns use pre-adjusted close-to-close returns. Cash dividend attribution is not separately decomposed in this first panel.",
            *config["limitations"],
        ],
        "credential_policy": f"Credentials loaded from {username_env}/{password_env} or local credential file. Credentials are never written.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "agent_access": ["Project Manager Agent", "Research Agent", "Quant Validation Agent"],
    }
    _write_json(manifest_path, manifest)
    return SimilarSectorPitPanelResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        date_count=len({row["trade_date"] for row in rows}),
        code_count=len({row["code"] for row in rows}),
        warning_count=len(warnings),
    )


def _universe_for_date(jq: Any, securities: Any, config: dict[str, Any], trade_day: date, listing_age_days: int, warnings: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for code, label in config["explicit_codes"].items():
        if _is_listed_and_old_enough(securities, code, trade_day, listing_age_days):
            result[code] = str(label)
    for industry_code, label in config["industry_codes"].items():
        try:
            codes = jq.get_industry_stocks(industry_code, date=trade_day)
        except Exception as exc:
            warnings.append(f"{trade_day}:{industry_code}: industry membership failed: {repr(exc)}")
            continue
        for code in codes:
            if _is_listed_and_old_enough(securities, code, trade_day, listing_age_days):
                result[str(code)] = str(label)
    return result


def _is_listed_and_old_enough(securities: Any, code: str, trade_day: date, listing_age_days: int) -> bool:
    if code not in securities.index:
        return False
    row = securities.loc[code]
    start_date = _to_date(row.get("start_date"))
    end_date = _to_date(row.get("end_date"))
    if start_date is None:
        return False
    if (trade_day - start_date).days < listing_age_days:
        return False
    if end_date is not None and end_date < trade_day:
        return False
    return True


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
            jq.indicator.inc_revenue_year_on_year,
            jq.indicator.inc_total_revenue_year_on_year,
            jq.indicator.ocf_to_revenue,
            jq.indicator.goods_sale_and_service_to_revenue,
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
        raise RuntimeError("jqdatasdk is required for similar-sector PIT panel collection") from exc
    username, password = load_joinquant_credentials(username_env, password_env)
    if username and password:
        jq.auth(username, password)
    if not jq.is_auth():
        raise RuntimeError("JoinQuant credentials are not available for similar-sector PIT panel collection")
    return jq


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
    return trade_days[0] if trade_days else current


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


def _universe_source(config: dict[str, Any]) -> str:
    parts = []
    if config["explicit_codes"]:
        parts.append("explicit_core_operator_codes")
    if config["industry_codes"]:
        parts.append("jqdatasdk.get_industry_stocks")
    return "+".join(parts)


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


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sector", choices=sorted(SECTOR_CONFIGS))
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--start-date", default="2021-05-01")
    parser.add_argument("--end-date", default="2026-05-31")
    parser.add_argument("--listing-age-days", type=int, default=180)
    args = parser.parse_args(argv)
    result = collect_similar_sector_pit_panel(
        args.sector,
        out_root=args.out_root,
        start_date=args.start_date,
        end_date=args.end_date,
        listing_age_days=args.listing_age_days,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
