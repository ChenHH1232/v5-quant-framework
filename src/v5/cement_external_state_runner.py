from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import compound, to_float
from v5.paths import DEFAULT_DATABASE_DIR
from v5.scoring import apply_value_trap_guard, score_rows


DEFAULT_PANEL = DEFAULT_DATABASE_DIR / "processed" / "low_volatility_factors_v5a5" / "building_materials_cement" / "building_materials_cement_v5a5" / "panel_with_low_vol.csv"
DEFAULT_OUT_DIR = DEFAULT_DATABASE_DIR / "processed" / "cement_external_state_v5a9"
DEFAULT_ENRICHED_OUT_DIR = DEFAULT_DATABASE_DIR / "processed" / "cement_state_enriched_panel_v5a9"
DEFAULT_STATE_VALIDATION_OUT = Path("validation_state_v5a9_cement")


@dataclass(frozen=True)
class CementStateResult:
    state_csv: Path
    manifest_path: Path
    rebalance_count: int
    warning_count: int


def collect_cement_external_state(
    panel_csv: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> CementStateResult:
    panel_rows = read_csv_rows(panel_csv)
    rebalance_dates = sorted({row["trade_date"] for row in panel_rows if row.get("trade_date")})
    if not rebalance_dates:
        raise RuntimeError("cement external state collection requires panel rows with trade_date")

    raw_sources = _load_akshare_sources()
    state_rows = []
    warnings = []
    for trade_text in rebalance_dates:
        trade_day = date.fromisoformat(trade_text[:10])
        row = {"trade_date": trade_text}
        row.update(_latest_daily_state(raw_sources.get("construction_price_index", []), trade_day, "cement_price_proxy"))
        row.update(_latest_monthly_state(raw_sources.get("real_estate", []), trade_day, "real_estate_prosperity"))
        row.update(_latest_monthly_state(raw_sources.get("fixed_asset_investment", []), trade_day, "fixed_asset_investment"))
        row.update(_latest_monthly_state(raw_sources.get("commodity_price", []), trade_day, "commodity_price"))
        row["cement_cycle_score"] = _cement_cycle_score(row)
        row["cement_cycle_guard_pass"] = "true" if (to_float(row["cement_cycle_score"]) or 0.0) >= 0 else "false"
        state_rows.append(row)

    for name, rows in raw_sources.items():
        if not rows:
            warnings.append(f"{name} source returned no rows")

    fields = [
        "trade_date",
        "cement_price_proxy_date",
        "cement_price_proxy_value",
        "cement_price_proxy_change_1y",
        "real_estate_prosperity_date",
        "real_estate_prosperity_value",
        "real_estate_prosperity_change_1y",
        "fixed_asset_investment_date",
        "fixed_asset_investment_yoy",
        "fixed_asset_investment_mom",
        "commodity_price_date",
        "energy_cost_yoy",
        "mineral_product_yoy",
        "cement_cycle_score",
        "cement_cycle_guard_pass",
    ]
    state_csv = out_dir / "cement_external_state.csv"
    write_csv_rows(state_csv, fields, state_rows)
    manifest = {
        "dataset": "cement_external_state_v5a9",
        "state_csv": str(state_csv),
        "panel": str(panel_csv),
        "rebalance_count": len(state_rows),
        "source_policy": "akshare public macro / Eastmoney proxy sources; diagnostic research state only until official cement-price/output series are reviewed.",
        "sources": {
            "cement_price_proxy": "akshare.macro_china_construction_price_index",
            "real_estate_prosperity": "akshare.macro_china_real_estate",
            "fixed_asset_investment": "akshare.macro_china_gdzctz",
            "energy_cost_and_minerals": "akshare.macro_china_qyspjg",
        },
        "warnings": warnings,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path = out_dir / "cement_external_state_manifest.json"
    write_json_file(manifest_path, manifest)
    return CementStateResult(state_csv, manifest_path, len(state_rows), len(warnings))


def build_cement_state_enriched_panel(
    panel_csv: Path = DEFAULT_PANEL,
    state_csv: Path = DEFAULT_OUT_DIR / "cement_external_state.csv",
    out_dir: Path = DEFAULT_ENRICHED_OUT_DIR,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    state_by_date = {row["trade_date"]: row for row in read_csv_rows(state_csv)}
    enriched = []
    state_fields = [
        "cement_price_proxy_date",
        "cement_price_proxy_value",
        "cement_price_proxy_change_1y",
        "real_estate_prosperity_date",
        "real_estate_prosperity_value",
        "real_estate_prosperity_change_1y",
        "fixed_asset_investment_date",
        "fixed_asset_investment_yoy",
        "fixed_asset_investment_mom",
        "commodity_price_date",
        "energy_cost_yoy",
        "mineral_product_yoy",
        "cement_cycle_score",
        "cement_cycle_guard_pass",
    ]
    for row in panel_rows:
        item = dict(row)
        state = state_by_date.get(row.get("trade_date"), {})
        for field in state_fields:
            item[field] = state.get(field, "")
        item["cement_state_source"] = "akshare_public_proxy_state_diagnostic"
        item["cement_state_visible_date"] = item.get("trade_date", "")
        enriched.append(item)
    if not enriched:
        raise RuntimeError("cement state enriched panel has no rows")
    out_panel = out_dir / "panel_with_cement_state.csv"
    write_csv_rows(out_panel, enriched[0].keys(), enriched)
    write_json_file(
        out_dir / "cement_state_enriched_panel_manifest.json",
        {
            "dataset": "cement_state_enriched_panel_v5a9",
            "panel": str(out_panel),
            "source_panel": str(panel_csv),
            "state_csv": str(state_csv),
            "row_count": len(enriched),
            "date_count": len({row["trade_date"] for row in enriched}),
            "coverage": _coverage(enriched, state_fields),
            "limitations": [
                "State rows are public macro proxies, not reviewed cement spot/output/inventory data.",
                "Use this panel for research diagnostics only; Engineering handoff requires official or reviewed state rows.",
            ],
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    return out_panel


def run_cement_state_bucket_validation(
    panel_csv: Path,
    spec_path: Path,
    out_dir: Path = DEFAULT_STATE_VALIDATION_OUT,
    strategy_id: str = "cement_cycle_aware_ocf_low_vol_v5a9",
) -> Path:
    from v5.engine import load_spec

    spec = load_spec(spec_path)
    rows = read_csv_rows(panel_csv)
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    bucket_rows = []
    for bucket in ["all", "cycle_guard_pass", "cycle_guard_fail"]:
        bucket_source = _filter_bucket(rows, bucket)
        bucket_rows.append(_strategy_case(bucket, bucket_source, spec.raw))
    write_csv_rows(out / "cement_state_bucket_validation.csv", bucket_rows[0].keys(), bucket_rows)
    summary = {
        "strategy_id": strategy_id,
        "status": "state_bucket_validation_completed_not_acceptance",
        "panel": str(panel_csv),
        "spec": str(spec_path),
        "bucket_validation": bucket_rows,
        "pm_interpretation": "Cement state buckets diagnose whether OCF/low-vol selection works only when ex-ante cycle proxies are not deteriorating. This is not Engineering handoff evidence.",
    }
    write_json_file(out / "cement_state_bucket_validation_summary.json", summary)
    _write_report(out / "cement_state_bucket_validation_report.md", summary)
    return out / "cement_state_bucket_validation_report.md"


def _load_akshare_sources() -> dict[str, list[dict[str, Any]]]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("cement external state collection requires akshare") from exc
    sources: dict[str, list[dict[str, Any]]] = {}
    sources["construction_price_index"] = _records(ak.macro_china_construction_price_index())
    sources["real_estate"] = _records(ak.macro_china_real_estate())
    sources["fixed_asset_investment"] = _records(ak.macro_china_gdzctz())
    sources["commodity_price"] = _records(ak.macro_china_qyspjg())
    return sources


def _records(df: Any) -> list[dict[str, Any]]:
    return json.loads(df.to_json(orient="records", force_ascii=False))


def _latest_daily_state(rows: list[dict[str, Any]], trade_day: date, prefix: str) -> dict[str, Any]:
    candidates = []
    for row in rows:
        current = _parse_date(row.get("日期"))
        if current and current <= trade_day:
            candidates.append((current, row))
    if not candidates:
        return {f"{prefix}_date": "", f"{prefix}_value": "", f"{prefix}_change_1y": ""}
    current, row = sorted(candidates, key=lambda item: item[0])[-1]
    return {
        f"{prefix}_date": current.isoformat(),
        f"{prefix}_value": _text(row.get("最新值")),
        f"{prefix}_change_1y": _text(row.get("近1年涨跌幅")),
    }


def _latest_monthly_state(rows: list[dict[str, Any]], trade_day: date, prefix: str) -> dict[str, Any]:
    candidates = []
    cutoff = trade_day - timedelta(days=21)
    for row in rows:
        current = _parse_date(row.get("日期") or row.get("月份"))
        if current and current <= cutoff:
            candidates.append((current, row))
    if not candidates:
        return _empty_monthly_state(prefix)
    current, row = sorted(candidates, key=lambda item: item[0])[-1]
    if prefix == "real_estate_prosperity":
        return {
            f"{prefix}_date": current.isoformat(),
            f"{prefix}_value": _text(row.get("最新值")),
            f"{prefix}_change_1y": _text(row.get("近1年涨跌幅")),
        }
    if prefix == "fixed_asset_investment":
        return {
            f"{prefix}_date": current.isoformat(),
            f"{prefix}_yoy": _text(row.get("同比增长")),
            f"{prefix}_mom": _text(row.get("环比增长")),
        }
    return {
        "commodity_price_date": current.isoformat(),
        "energy_cost_yoy": _text(row.get("煤油电-同比增长")),
        "mineral_product_yoy": _text(row.get("矿产品-同比增长")),
    }


def _empty_monthly_state(prefix: str) -> dict[str, Any]:
    if prefix == "real_estate_prosperity":
        return {f"{prefix}_date": "", f"{prefix}_value": "", f"{prefix}_change_1y": ""}
    if prefix == "fixed_asset_investment":
        return {f"{prefix}_date": "", f"{prefix}_yoy": "", f"{prefix}_mom": ""}
    return {"commodity_price_date": "", "energy_cost_yoy": "", "mineral_product_yoy": ""}


def _cement_cycle_score(row: dict[str, Any]) -> str:
    score = 0.0
    for field, weight in [
        ("cement_price_proxy_change_1y", 0.35),
        ("real_estate_prosperity_change_1y", 0.25),
        ("fixed_asset_investment_yoy", 0.25),
    ]:
        value = to_float(row.get(field))
        if value is not None:
            score += weight * _bounded(value / 10.0)
    energy = to_float(row.get("energy_cost_yoy"))
    if energy is not None:
        score -= 0.15 * _bounded(energy / 10.0)
    return f"{score:.6f}"


def _strategy_case(name: str, rows: list[dict[str, Any]], raw: dict[str, Any]) -> dict[str, Any]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_date.setdefault(row["trade_date"], []).append(row)
    returns = []
    selected_counts = []
    selected_count = int(raw["portfolio"]["selection_count"])
    for _, date_rows in sorted(by_date.items()):
        scored, _used = score_rows(raw, date_rows)
        selected = sorted(apply_value_trap_guard(raw, scored), key=lambda item: item["score"], reverse=True)[:selected_count]
        if selected:
            returns.append(mean(float(row["future_return"]) for row in selected))
            selected_counts.append(len(selected))
        else:
            returns.append(0.0)
            selected_counts.append(0)
    return {
        "bucket": name,
        "periods": len(returns),
        "cum_return": compound(returns),
        "mean_return": mean(returns) if returns else None,
        "positive_ratio": sum(1 for ret in returns if ret > 0) / len(returns) if returns else None,
        "mean_selected_count": mean(selected_counts) if selected_counts else None,
    }


def _filter_bucket(rows: list[dict[str, Any]], bucket: str) -> list[dict[str, Any]]:
    if bucket == "all":
        return rows
    expected = "true" if bucket == "cycle_guard_pass" else "false"
    return [row for row in rows if str(row.get("cement_cycle_guard_pass", "")).lower() == expected]


def _coverage(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, float]:
    return {
        field: sum(1 for row in rows if row.get(field) not in (None, "")) / len(rows)
        for field in fields
    }


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value)
    if "年" in text:
        text = text.replace("月份", "").replace("月", "").replace("年", "-")
        if text.count("-") == 1:
            text = f"{text}-01"
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _bounded(value: float) -> float:
    return max(-2.0, min(2.0, value))


def _text(value: Any) -> str:
    if value in (None, ""):
        return ""
    return str(value)


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    rows = summary["bucket_validation"]
    lines = [
        f"# {summary['strategy_id']} Cement State Bucket Validation",
        "",
        f"Status: `{summary['status']}`",
        "",
        "| Bucket | Periods | Cumulative Return | Positive Ratio | Mean Selected |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['bucket']}` | {row['periods']} | {_pct(row['cum_return'])} | {_pct(row['positive_ratio'])} | {row['mean_selected_count']} |"
        )
    lines.extend(["", summary["pm_interpretation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _pct(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return ""
    return f"{number * 100:.2f}%"
