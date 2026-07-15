from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any


FACTOR_ALIASES = {
    "roe_quality": ["return_on_equity_ttm", "roe"],
    "capital_resilience": ["core_tier_1_capital_adequacy_ratio"],
    "provision_buffer": ["provision_coverage_ratio"],
}
EASTMONEY_QUALITY_FIELDS = {"asset_quality_trend", "provision_buffer", "capital_resilience"}


def score_rows(raw_spec: dict[str, Any], date_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    scoring = raw_spec.get("signals", {}).get("scoring", {})
    if scoring.get("method") == "two_layer_score":
        return score_two_layer(raw_spec, date_rows)
    return score_weighted_composite(raw_spec, date_rows)


def score_weighted_composite(raw_spec: dict[str, Any], date_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    factors = raw_spec["signals"]["factors"]
    scoring = raw_spec["signals"]["scoring"]
    weights = scoring.get("weights", {})
    min_factor_count = int(scoring.get("min_factor_count", 1))
    factor_scores: dict[str, dict[str, float]] = {}
    used_factors: list[str] = []
    for factor in factors:
        name = factor["name"]
        values = []
        keyed = []
        for row in date_rows:
            raw_value = _factor_value(row, name)
            if raw_value is None:
                continue
            value = -raw_value if factor["direction"] == "lower_is_better" else raw_value
            values.append(value)
            keyed.append((row["code"], value))
        zscores = _zscores(_winsorized(values))
        if len(zscores) >= 3:
            used_factors.append(name)
            factor_scores[name] = {code: zscores[index] for index, (code, _value) in enumerate(keyed)}
        else:
            factor_scores[name] = {}

    scored = []
    for row in date_rows:
        score = 0.0
        used_weight = 0.0
        factor_count = 0
        for factor in factors:
            name = factor["name"]
            factor_weight = float(weights.get(name, 1.0))
            value = factor_scores.get(name, {}).get(row["code"])
            if value is None:
                continue
            score += factor_weight * value
            used_weight += abs(factor_weight)
            factor_count += 1
        if used_weight <= 0:
            continue
        if factor_count < min_factor_count:
            continue
        enriched = dict(row)
        enriched["score"] = score / used_weight
        enriched["final_score"] = enriched["score"]
        enriched["factor_count"] = factor_count
        scored.append(enriched)
    return scored, used_factors


def score_two_layer(raw_spec: dict[str, Any], date_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    scoring = raw_spec["signals"]["scoring"]
    factor_by_name = {factor["name"]: factor for factor in raw_spec["signals"]["factors"]}
    value_parts, value_used = _score_group(date_rows, factor_by_name, scoring.get("value_score", {}))
    quality_parts, quality_used = _score_group(date_rows, factor_by_name, scoring.get("quality_score", {}))
    if not value_parts:
        return [], []

    value_score = _weighted_average_common_sample(value_parts)
    quality_score = _weighted_average_common_sample(quality_parts) if quality_parts else {}
    scored = []
    for row in date_rows:
        code = row["code"]
        if code not in value_score:
            continue
        enriched = dict(row)
        enriched["value_score"] = value_score[code]
        enriched["quality_score"] = quality_score.get(code)
        if code in quality_score:
            enriched["score"] = 0.55 * value_score[code] + 0.45 * quality_score[code]
        elif quality_parts:
            continue
        else:
            enriched["score"] = value_score[code]
        enriched["final_score"] = enriched["score"]
        enriched["factor_count"] = sum(
            1
            for name in value_used + quality_used
            if _factor_value(enriched, name) is not None
        )
        scored.append(enriched)
    return scored, value_used + quality_used


def apply_value_trap_guard(raw_spec: dict[str, Any], scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scoring = raw_spec.get("signals", {}).get("scoring", {})
    if scoring.get("method") == "two_layer_score":
        return _apply_v2_value_trap_guard(scored)
    return _apply_legacy_value_trap_guard(scored)


def merge_eastmoney_quality(
    panel_rows: list[dict[str, Any]],
    quality_csv: Path | None,
    min_review_status: str = "needs_check",
    visibility_mode: str = "notice_date",
) -> list[dict[str, Any]]:
    if quality_csv is None or not quality_csv.exists():
        return panel_rows
    quality_by_code = _load_quality_snapshots(quality_csv, min_review_status)
    merged = []
    for row in panel_rows:
        enriched = dict(row)
        trade_day = _parse_date(str(row.get("trade_date") or ""))
        snapshots = quality_by_code.get(str(row.get("code")), [])
        if visibility_mode == "notice_date":
            snapshot = _latest_visible_snapshot(snapshots, trade_day)
        elif visibility_mode == "joinquant_source_year":
            snapshot = _source_year_snapshot(snapshots, trade_day)
        else:
            raise ValueError("visibility_mode must be notice_date or joinquant_source_year")
        enriched["eastmoney_quality_notice_date"] = ""
        enriched["eastmoney_quality_review_status"] = ""
        if snapshot:
            for key in ["asset_quality_trend", "provision_buffer", "capital_resilience"]:
                if snapshot.get(key) not in (None, ""):
                    enriched[key] = snapshot[key]
            enriched["eastmoney_quality_notice_date"] = snapshot.get("notice_date", "")
            enriched["eastmoney_quality_review_status"] = snapshot.get("review_status", "")
        merged.append(enriched)
    return merged


def _score_group(
    date_rows: list[dict[str, Any]],
    factor_by_name: dict[str, dict[str, Any]],
    weights: dict[str, Any],
) -> tuple[list[tuple[dict[str, float], float]], list[str]]:
    parts = []
    used = []
    for name, weight_value in weights.items():
        factor = factor_by_name.get(name, {"direction": "higher_is_better"})
        keyed = []
        values = []
        for row in date_rows:
            raw_value = _factor_value(row, name)
            if raw_value is None:
                continue
            value = -raw_value if factor.get("direction") == "lower_is_better" else raw_value
            keyed.append((row["code"], value))
            values.append(value)
        zscores = _zscores(_winsorized(values))
        if len(zscores) < 3:
            continue
        used.append(name)
        parts.append(({code: zscores[index] for index, (code, _value) in enumerate(keyed)}, float(weight_value)))
    return parts, used


def _weighted_average(parts: list[tuple[dict[str, float], float]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    weights: dict[str, float] = defaultdict(float)
    for scores, weight in parts:
        for code, score in scores.items():
            totals[code] += score * weight
            weights[code] += abs(weight)
    return {code: totals[code] / weights[code] for code in totals if weights[code] > 0}


def _weighted_average_common_sample(parts: list[tuple[dict[str, float], float]]) -> dict[str, float]:
    if not parts:
        return {}
    common_codes = set(parts[0][0])
    for scores, _weight in parts[1:]:
        common_codes &= set(scores)
    total_weight = sum(weight for _scores, weight in parts)
    if total_weight <= 0:
        return {}
    result = {}
    for code in common_codes:
        result[code] = sum(scores[code] * weight for scores, weight in parts) / total_weight
    return result


def _apply_v2_value_trap_guard(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quality_values = [_to_float(row.get("quality_score")) for row in scored]
    quality_values = [value for value in quality_values if value is not None]
    if len(quality_values) < 3:
        return scored
    threshold = median(quality_values)
    guarded = [row for row in scored if (_to_float(row.get("quality_score")) is not None and _to_float(row.get("quality_score")) >= threshold)]
    asset_values = [_to_float(row.get("asset_quality_trend")) for row in guarded]
    asset_values = [value for value in asset_values if value is not None]
    if len(asset_values) >= 4:
        bottom_quartile = sorted(asset_values)[max(0, int(len(asset_values) * 0.25) - 1)]
        guarded = [
            row
            for row in guarded
            if _to_float(row.get("asset_quality_trend")) is None
            or _to_float(row.get("asset_quality_trend")) > bottom_quartile
        ]
    return guarded


def _apply_legacy_value_trap_guard(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quality_values = []
    enriched = []
    for row in scored:
        npl = _to_float(row.get("non_performing_loan_ratio"))
        provision = _to_float(row.get("provision_coverage_ratio"))
        capital = _to_float(row.get("core_tier_1_capital_adequacy_ratio"))
        if npl is None or provision is None or capital is None:
            continue
        quality = (-npl) + provision + capital
        item = dict(row)
        item["quality_guard_score"] = quality
        quality_values.append(quality)
        enriched.append(item)
    if not enriched:
        return scored
    threshold = median(quality_values)
    return [row for row in enriched if row["quality_guard_score"] >= threshold]


def _load_quality_snapshots(path: Path, min_review_status: str) -> dict[str, list[dict[str, Any]]]:
    allowed = _allowed_review_statuses(min_review_status)
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("review_status") or "") not in allowed:
                continue
            if not row.get("code") or not row.get("notice_date"):
                continue
            by_code[row["code"]].append(row)
    for snapshots in by_code.values():
        snapshots.sort(key=lambda item: (str(item.get("notice_date")), int(float(item.get("source_year") or 0))))
    return dict(by_code)


def _latest_visible_snapshot(snapshots: list[dict[str, Any]], trade_day: date) -> dict[str, Any] | None:
    visible = None
    for snapshot in snapshots:
        notice = _parse_date(str(snapshot.get("notice_date") or ""))
        if notice < trade_day:
            visible = snapshot
        else:
            break
    return visible


def _source_year_snapshot(snapshots: list[dict[str, Any]], trade_day: date) -> dict[str, Any] | None:
    source_year = trade_day.year - 1 if trade_day.month >= 5 else trade_day.year - 2
    for snapshot in snapshots:
        try:
            if int(float(snapshot.get("source_year") or 0)) == source_year:
                return snapshot
        except (TypeError, ValueError):
            continue
    return None


def _allowed_review_statuses(min_review_status: str) -> set[str]:
    if min_review_status == "reviewed":
        return {"reviewed"}
    if min_review_status == "needs_check":
        return {"reviewed", "needs_check"}
    if min_review_status == "unreviewed":
        return {"reviewed", "needs_check", "unreviewed"}
    raise ValueError("min_review_status must be reviewed, needs_check, or unreviewed")


def _zscores(values: list[float]) -> list[float]:
    if len(values) < 3:
        return []
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    std = variance ** 0.5
    if std == 0:
        return []
    return [(value - avg) / std for value in values]


def _winsorized(values: list[float], lower: float = 0.05, upper: float = 0.95) -> list[float]:
    if len(values) < 5:
        return values
    sorted_values = sorted(values)
    low = _quantile(sorted_values, lower)
    high = _quantile(sorted_values, upper)
    return [min(max(value, low), high) for value in values]


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    pos = (len(sorted_values) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = pos - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _factor_value(row: dict[str, Any], name: str) -> float | None:
    value = _to_float(row.get(name))
    if value is not None:
        return value
    if name in EASTMONEY_QUALITY_FIELDS and "eastmoney_quality_review_status" in row:
        return None
    for alias in FACTOR_ALIASES.get(name, []):
        value = _to_float(row.get(alias))
        if value is not None:
            return value
    return None


def _parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])
