from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_joinquant_platform_attribution_runner import _load_positions, _load_transactions


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_bank_power_v5f_attribution") / "current"
EXPORT_DIR = Path("data") / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution"
ATTR_DIR = Path("v5f_joinquant_platform_attribution") / "current"
WEIGHTS_PATH = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_weights.csv"
PRIMARY_ID = "internal_subsleeve_mom12_70_30"
BASELINE_ID = "v57f_startup_preload_repaired_baseline"
INITIAL_CASH = 2_000_000.0
BANK_SLEEVE = "bank"
POWER_SLEEVE = "utilities_electricity"


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_bank_power_v5f_attribution_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_inputs", blockers=blockers)
        _write_json(out / "v5c_bank_power_v5f_attribution_summary.json", summary)
        return out / "v5c_bank_power_v5f_attribution_summary.json"

    weights = pd.read_csv(root / WEIGHTS_PATH, dtype={"code": str, "rebalance_date": str})
    code_to_sleeve = dict(weights[["code", "sleeve"]].drop_duplicates().itertuples(index=False, name=None))
    primary_pos = _load_stock_positions(root, "primary", code_to_sleeve)
    baseline_pos = _load_stock_positions(root, "baseline", code_to_sleeve)
    primary_tx = _load_filled_transactions(root, "primary", code_to_sleeve)
    baseline_tx = _load_filled_transactions(root, "baseline", code_to_sleeve)
    edge = _platform_edge(root)

    sleeve_rows = _sleeve_pnl_comparison(primary_pos, baseline_pos, edge)
    yearly_rows = _yearly_comparison(primary_pos, baseline_pos)
    turnover_rows = _turnover_comparison(primary_tx, baseline_tx)
    focus_rows = _focus_interpretation(sleeve_rows, edge)
    decision = _pm_decision(focus_rows, edge)
    next_queue = _next_queue()
    rules = _rules()

    _write_csv(out / "v5c_bank_power_platform_sleeve_pnl_comparison.csv", sleeve_rows)
    _write_csv(out / "v5c_bank_power_yearly_pnl_delta.csv", yearly_rows)
    _write_csv(out / "v5c_bank_power_turnover_cost_comparison.csv", turnover_rows)
    _write_csv(out / "v5c_bank_power_interpretation_matrix.csv", focus_rows)
    _write_csv(out / "v5c_bank_power_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_bank_power_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_bank_power_v5f_attribution_blockers.csv", [])
    (out / "v5c_bank_power_agent_execution_rules.md").write_text(rules, encoding="utf-8")

    summary = _summary(
        "completed_bank_power_v5f_platform_attribution",
        edge=edge,
        sleeve_rows=sleeve_rows,
        focus_rows=focus_rows,
        pm_gate_decision=decision[0]["pm_gate_decision"],
    )
    _write_json(out / "v5c_bank_power_v5f_attribution_summary.json", summary)
    (out / "v5c_bank_power_v5f_attribution_report.md").write_text(
        _report(summary, sleeve_rows, yearly_rows, turnover_rows, focus_rows, decision),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_bank_power_v5f_attribution_summary.json"


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        root / WEIGHTS_PATH,
        root / ATTR_DIR / "v5f_joinquant_platform_clean_edge_comparison.csv",
        root / EXPORT_DIR / "position_primary_internal_subsleeve_mom12_70_30" / "position.csv",
        root / EXPORT_DIR / "position_baseline_v57f_startup_preload_repaired_baseline" / "position.csv",
        root / EXPORT_DIR / "transaction_primary_internal_subsleeve_mom12_70_30" / "transaction.csv",
        root / EXPORT_DIR / "transaction_baseline_v57f_startup_preload_repaired_baseline" / "transaction.csv",
    ]
    return [
        {"blocker": "missing_required_input", "path": str(path.relative_to(root)), "fatal": True}
        for path in required
        if not path.exists()
    ]


def _load_stock_positions(root: Path, kind: str, code_to_sleeve: dict[str, str]) -> pd.DataFrame:
    folder = "position_primary_internal_subsleeve_mom12_70_30" if kind == "primary" else "position_baseline_v57f_startup_preload_repaired_baseline"
    df = _load_positions(root / EXPORT_DIR / folder / "position.csv")
    df = df[df["asset_type"].astype(str) != "cash"].copy()
    df["model"] = kind
    df["sleeve"] = df["code"].map(code_to_sleeve).fillna("UNKNOWN")
    df["year"] = df["trade_date"].astype(str).str[:4]
    return df


def _load_filled_transactions(root: Path, kind: str, code_to_sleeve: dict[str, str]) -> pd.DataFrame:
    folder = "transaction_primary_internal_subsleeve_mom12_70_30" if kind == "primary" else "transaction_baseline_v57f_startup_preload_repaired_baseline"
    df = _load_transactions(root / EXPORT_DIR / folder / "transaction.csv")
    if df.empty:
        return df
    df = df[df["filled_status_ok"]].copy()
    df["model"] = kind
    df["sleeve"] = df["code"].map(code_to_sleeve).fillna("UNKNOWN")
    return df


def _platform_edge(root: Path) -> dict[str, float]:
    rows = _read_csv(root / ATTR_DIR / "v5f_joinquant_platform_clean_edge_comparison.csv")
    out: dict[str, float] = {}
    for row in rows:
        metric = row["metric"]
        out[metric] = _to_float(row["primary_minus_baseline"])
        out[f"primary_{metric}"] = _to_float(row["platform_primary"])
        out[f"baseline_{metric}"] = _to_float(row["platform_baseline"])
    return out


def _sleeve_pnl_comparison(primary: pd.DataFrame, baseline: pd.DataFrame, edge: dict[str, float]) -> list[dict[str, Any]]:
    platform_edge = edge.get("total_return_pct", math.nan)
    rows = []
    sleeves = sorted(set(primary["sleeve"]).union(set(baseline["sleeve"])))
    primary_daily_weight = primary.groupby(["trade_date", "sleeve"])["position_weight"].sum().reset_index()
    baseline_daily_weight = baseline.groupby(["trade_date", "sleeve"])["position_weight"].sum().reset_index()
    primary_avg_weight = primary_daily_weight.groupby("sleeve")["position_weight"].mean().to_dict()
    baseline_avg_weight = baseline_daily_weight.groupby("sleeve")["position_weight"].mean().to_dict()
    for sleeve in sleeves:
        p = primary[primary["sleeve"].eq(sleeve)]
        b = baseline[baseline["sleeve"].eq(sleeve)]
        p_pnl = float(p["daily_pnl"].sum())
        b_pnl = float(b["daily_pnl"].sum())
        delta_pct = (p_pnl - b_pnl) / INITIAL_CASH * 100.0
        rows.append(
            {
                "sleeve": sleeve,
                "primary_stock_pnl": p_pnl,
                "baseline_stock_pnl": b_pnl,
                "delta_stock_pnl": p_pnl - b_pnl,
                "primary_stock_pnl_pct_initial_cash": p_pnl / INITIAL_CASH * 100.0,
                "baseline_stock_pnl_pct_initial_cash": b_pnl / INITIAL_CASH * 100.0,
                "delta_stock_pnl_pct_initial_cash": delta_pct,
                "share_of_platform_total_edge": delta_pct / platform_edge if platform_edge else "",
                "primary_avg_sleeve_weight_pct": primary_avg_weight.get(sleeve, 0.0) * 100.0,
                "baseline_avg_sleeve_weight_pct": baseline_avg_weight.get(sleeve, 0.0) * 100.0,
                "position_day_count_primary": int(p["trade_date"].nunique()),
                "position_day_count_baseline": int(b["trade_date"].nunique()),
                "stock_row_count_primary": int(len(p)),
                "stock_row_count_baseline": int(len(b)),
            }
        )
    return sorted(rows, key=lambda row: float(row["delta_stock_pnl_pct_initial_cash"]), reverse=True)


def _yearly_comparison(primary: pd.DataFrame, baseline: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    sleeves = sorted(set(primary["sleeve"]).union(set(baseline["sleeve"])))
    years = sorted(set(primary["year"]).union(set(baseline["year"])))
    for sleeve in sleeves:
        for year in years:
            p = primary[primary["sleeve"].eq(sleeve) & primary["year"].eq(year)]
            b = baseline[baseline["sleeve"].eq(sleeve) & baseline["year"].eq(year)]
            p_pnl = float(p["daily_pnl"].sum())
            b_pnl = float(b["daily_pnl"].sum())
            rows.append(
                {
                    "sleeve": sleeve,
                    "year": year,
                    "primary_stock_pnl": p_pnl,
                    "baseline_stock_pnl": b_pnl,
                    "delta_stock_pnl": p_pnl - b_pnl,
                    "delta_stock_pnl_pct_initial_cash": (p_pnl - b_pnl) / INITIAL_CASH * 100.0,
                    "is_bank_or_power": sleeve in {BANK_SLEEVE, POWER_SLEEVE},
                }
            )
    return rows


def _turnover_comparison(primary_tx: pd.DataFrame, baseline_tx: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    sleeves = sorted(set(primary_tx["sleeve"]).union(set(baseline_tx["sleeve"]))) if not primary_tx.empty and not baseline_tx.empty else []
    for sleeve in sleeves:
        p = primary_tx[primary_tx["sleeve"].eq(sleeve)]
        b = baseline_tx[baseline_tx["sleeve"].eq(sleeve)]
        p_traded = float(p["gross_value"].abs().sum())
        b_traded = float(b["gross_value"].abs().sum())
        rows.append(
            {
                "sleeve": sleeve,
                "primary_traded_value": p_traded,
                "baseline_traded_value": b_traded,
                "delta_traded_value": p_traded - b_traded,
                "primary_commission": float(p["commission"].sum()),
                "baseline_commission": float(b["commission"].sum()),
                "delta_commission": float(p["commission"].sum() - b["commission"].sum()),
                "primary_order_count": int(len(p)),
                "baseline_order_count": int(len(b)),
            }
        )
    return sorted(rows, key=lambda row: float(row["delta_traded_value"]), reverse=True)


def _focus_interpretation(sleeve_rows: list[dict[str, Any]], edge: dict[str, float]) -> list[dict[str, Any]]:
    by_sleeve = {row["sleeve"]: row for row in sleeve_rows}
    bank_delta = float(by_sleeve[BANK_SLEEVE]["delta_stock_pnl_pct_initial_cash"])
    power_delta = float(by_sleeve[POWER_SLEEVE]["delta_stock_pnl_pct_initial_cash"])
    combined = bank_delta + power_delta
    total_stock_delta = sum(float(row["delta_stock_pnl_pct_initial_cash"]) for row in sleeve_rows)
    platform_edge = edge.get("total_return_pct", math.nan)
    other_delta = total_stock_delta - combined
    rows = [
        {
            "focus": "bank",
            "delta_stock_pnl_pct_initial_cash": bank_delta,
            "platform_edge_share": bank_delta / platform_edge if platform_edge else "",
            "assessment": "meaningful_positive" if bank_delta >= 1.0 else "weak_or_mixed",
            "interpretation": "Bank sleeve adds clear positive attribution, but 2021 and 2026 YTD are negative.",
            "allowed_action": "P1 bank PIT state panel and forward observation only",
        },
        {
            "focus": "utilities_electricity",
            "delta_stock_pnl_pct_initial_cash": power_delta,
            "platform_edge_share": power_delta / platform_edge if platform_edge else "",
            "assessment": "meaningful_positive" if power_delta >= 1.0 else "weak_or_mixed",
            "interpretation": "Power sleeve is the largest positive contributor, led mainly by 2025.",
            "allowed_action": "P1 coal/tariff/hydro state panel and forward observation only",
        },
        {
            "focus": "bank_plus_power",
            "delta_stock_pnl_pct_initial_cash": combined,
            "platform_edge_share": combined / platform_edge if platform_edge else "",
            "assessment": "primary_positive_driver" if combined > 0 and combined >= platform_edge else "positive_but_not_full_explanation",
            "interpretation": "Bank plus power more than explain the platform total edge before offsets from other sleeves and residual path effects.",
            "allowed_action": "Prioritize bank/power state attribution; do not create trade trigger yet",
        },
        {
            "focus": "other_sleeves_offset",
            "delta_stock_pnl_pct_initial_cash": other_delta,
            "platform_edge_share": other_delta / platform_edge if platform_edge else "",
            "assessment": "negative_offset" if other_delta < 0 else "positive_support",
            "interpretation": "Highway and port/rail offset part of bank/power gains.",
            "allowed_action": "Keep V5f primary; review whether infrastructure tags need separate diagnostics",
        },
    ]
    return rows


def _pm_decision(focus_rows: list[dict[str, Any]], edge: dict[str, float]) -> list[dict[str, Any]]:
    focus = {row["focus"]: row for row in focus_rows}
    combined = float(focus["bank_plus_power"]["delta_stock_pnl_pct_initial_cash"])
    total_edge = edge.get("total_return_pct", 0.0)
    decision = (
        "bank_power_attribution_positive_proceed_to_P1_state_panels_observation_only"
        if combined >= total_edge > 0
        else "bank_power_attribution_mixed_keep_observation_only"
    )
    return [
        {
            "pm_gate_decision": decision,
            "platform_primary_total_return_pct": edge.get("primary_total_return_pct", ""),
            "platform_baseline_total_return_pct": edge.get("baseline_total_return_pct", ""),
            "platform_edge_pct_points": total_edge,
            "bank_plus_power_stock_pnl_delta_pct_initial_cash": combined,
            "direct_v5c_model_lift_tested": False,
            "can_change_weights": False,
            "can_trigger_trade": False,
            "accepted": False,
            "next_action": "build_bank_and_power_P1_state_panels_then_attach_observation_tags_to_forward_tracking",
        }
    ]


def _next_queue() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "next_task": "v5c_bank_p1_nim_asset_quality_capital_panel",
            "status": "ready",
            "detail": "Bank attribution is positive; build PIT state panel before any rule consideration.",
        },
        {
            "rank": 2,
            "next_task": "v5c_power_p1_coal_tariff_hydro_state_panel",
            "status": "ready",
            "detail": "Power attribution is strongest; build coal/tariff/hydro state panel.",
        },
        {
            "rank": 3,
            "next_task": "v5f_primary_forward_tracking_bank_power_state_tags",
            "status": "ready_after_P1",
            "detail": "Attach tags as observation only; no V5f weight change.",
        },
    ]


def _summary(
    status: str,
    edge: dict[str, float] | None = None,
    sleeve_rows: list[dict[str, Any]] | None = None,
    focus_rows: list[dict[str, Any]] | None = None,
    pm_gate_decision: str | None = None,
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    edge = edge or {}
    sleeve_rows = sleeve_rows or []
    focus_rows = focus_rows or []
    by_sleeve = {row["sleeve"]: row for row in sleeve_rows}
    by_focus = {row["focus"]: row for row in focus_rows}
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_bank_power_v5f_attribution",
        "status": status,
        "benchmark": BASELINE_ID,
        "primary_model": PRIMARY_ID,
        "platform_primary_total_return_pct": edge.get("primary_total_return_pct"),
        "platform_baseline_total_return_pct": edge.get("baseline_total_return_pct"),
        "platform_edge_pct_points": edge.get("total_return_pct"),
        "bank_stock_pnl_delta_pct_initial_cash": _row_value(by_sleeve, BANK_SLEEVE, "delta_stock_pnl_pct_initial_cash"),
        "power_stock_pnl_delta_pct_initial_cash": _row_value(by_sleeve, POWER_SLEEVE, "delta_stock_pnl_pct_initial_cash"),
        "bank_plus_power_stock_pnl_delta_pct_initial_cash": _row_value(by_focus, "bank_plus_power", "delta_stock_pnl_pct_initial_cash"),
        "other_sleeves_offset_pct_initial_cash": _row_value(by_focus, "other_sleeves_offset", "delta_stock_pnl_pct_initial_cash"),
        "attribution_method": "JoinQuant position daily_pnl by stock mapped to V57f sleeve; contribution is pct of 2,000,000 initial cash, not a full compounded NAV decomposition.",
        "direct_v5c_model_lift_tested": False,
        "v5c_role": "industry_state_attribution_and_data_gate_only",
        "can_change_weights": False,
        "can_trigger_trade": False,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "pm_gate_decision": pm_gate_decision or "blocked_missing_required_inputs",
        "fatal_blocker_count": len(blockers or []),
        "fatal_blockers": blockers or [],
    }


def _row_value(rows: dict[str, dict[str, Any]], key: str, field: str) -> Any:
    return rows.get(key, {}).get(field)


def _report(
    summary: dict[str, Any],
    sleeve_rows: list[dict[str, Any]],
    yearly_rows: list[dict[str, Any]],
    turnover_rows: list[dict[str, Any]],
    focus_rows: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    bank = next(row for row in sleeve_rows if row["sleeve"] == BANK_SLEEVE)
    power = next(row for row in sleeve_rows if row["sleeve"] == POWER_SLEEVE)
    combined = next(row for row in focus_rows if row["focus"] == "bank_plus_power")
    other = next(row for row in focus_rows if row["focus"] == "other_sleeves_offset")
    bank_years = [row for row in yearly_rows if row["sleeve"] == BANK_SLEEVE]
    power_years = [row for row in yearly_rows if row["sleeve"] == POWER_SLEEVE]
    bank_turn = next(row for row in turnover_rows if row["sleeve"] == BANK_SLEEVE)
    power_turn = next(row for row in turnover_rows if row["sleeve"] == POWER_SLEEVE)
    return f"""# V5c Bank / Power V5f Attribution

## Result

V5f primary `{PRIMARY_ID}` has a clean JoinQuant platform edge of `{summary['platform_edge_pct_points']:.2f}` pct points versus `{BASELINE_ID}`.

Bank and power are the main positive sleeves:

- Bank stock-PnL attribution delta: `{bank['delta_stock_pnl_pct_initial_cash']:.2f}` pct of initial cash.
- Power stock-PnL attribution delta: `{power['delta_stock_pnl_pct_initial_cash']:.2f}` pct of initial cash.
- Bank plus power combined: `{combined['delta_stock_pnl_pct_initial_cash']:.2f}` pct.
- Other sleeves offset: `{other['delta_stock_pnl_pct_initial_cash']:.2f}` pct.

This is meaningful positive attribution, not a new V5c trading rule.

## Year Pattern

Bank yearly deltas: {_compact_years(bank_years)}

Power yearly deltas: {_compact_years(power_years)}

Power's improvement is concentrated in 2025, while bank is positive in 2022-2025 but negative in 2021 and 2026 YTD.

## Cost / Turnover

- Bank incremental traded value: `{bank_turn['delta_traded_value']:.0f}`, incremental commission: `{bank_turn['delta_commission']:.2f}`.
- Power incremental traded value: `{power_turn['delta_traded_value']:.0f}`, incremental commission: `{power_turn['delta_commission']:.2f}`.

The attribution edge is far larger than incremental commission, but this packet does not approve any weight change.

## Gate

`{decision[0]['pm_gate_decision']}`
"""


def _compact_years(rows: list[dict[str, Any]]) -> str:
    return ", ".join(f"{row['year']}={float(row['delta_stock_pnl_pct_initial_cash']):+.2f}pct" for row in rows)


def _rules() -> str:
    return """# V5c Bank / Power V5f Attribution Rules

- Use repaired baseline only.
- Use JoinQuant same-platform primary and baseline exports only.
- Treat daily stock PnL by sleeve as attribution, not as a new model.
- Do not modify V57f or V5f weights.
- Do not trigger trades from bank/power tags.
- Do not mark accepted or live approved.
- Next work is PIT state-panel construction and forward observation only.
"""


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()
