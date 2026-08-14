from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "v5v_application_final_report_readiness" / "current" / "figures"
PLATFORM = ROOT / "data" / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution"
V5G = ROOT / "v5g_01_state_gated_internal_subsleeve_limited_engineering" / "current" / "v5g_01_state_gated_engineering_daily_returns.csv"
V5H = ROOT / "v5h_buy_execution_backtest" / "current" / "v5h_buy_execution_backtest_daily_nav.csv"
OUTPUT = FIGURES / "v5_primary_candidate_vs_research_observation_lines_2021_2026.png"
START, END = "20210506", "20260529"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fill: str, size: int, bold: bool = False) -> None:
    draw.text(xy, value, fill=fill, font=font(size, bold))


def ordinal(day: str) -> int:
    return date(int(day[:4]), int(day[4:6]), int(day[6:8])).toordinal()


def platform_nav(path: Path) -> dict[str, float]:
    with path.open(encoding="gb18030", newline="") as handle:
        rows = list(csv.reader(handle))
    nav_column = rows[0].index("nav")
    return {row[0][:10].replace("-", ""): float(row[nav_column]) for row in rows[1:] if len(row) > nav_column and START <= row[0][:10].replace("-", "") <= END and row[nav_column]}


def nav_by_version(path: Path, version: str) -> dict[str, float]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["trade_date"].replace("-", ""): float(row["strategy_nav"]) for row in csv.DictReader(handle) if row["version_id"] == version and START <= row["trade_date"].replace("-", "") <= END}


def normalize(values: dict[str, float], days: list[str]) -> list[tuple[str, float]]:
    base = values[days[0]]
    return [(day, values[day] / base * 100) for day in days]


def main() -> None:
    series = {
        "主候选 internal_subsleeve_mom12_70_30": (platform_nav(PLATFORM / "daily_returns_primary_result_1_20.csv"), "#b42318", 13, "formal"),
        "repaired baseline": (platform_nav(PLATFORM / "daily_returns_baseline_result_1_21.csv"), "#186f78", 9, "formal"),
        "V5g 状态门 70/30": (nav_by_version(V5G, "v5g_01_state_gated_internal_subsleeve_70_30"), "#4c6a9c", 6, "observation"),
        "V5h 固定 14:00 买入执行": (nav_by_version(V5H, "v5h_fixed_1400_on_v5f_champion"), "#8b5fbf", 6, "observation"),
        "V5h pressure buy execution v1": (nav_by_version(V5H, "v5h_spec_v1_on_v5f_champion"), "#ba7a16", 6, "observation"),
    }
    common_days = sorted(set.intersection(*(set(values) for values, _, _, _ in series.values())))
    if len(common_days) != 1228 or common_days[0] != START or common_days[-1] != END:
        raise ValueError(f"Research lines are not aligned to the formal window: {len(common_days)}")
    plotted = {label: (normalize(values, common_days), color, width, status) for label, (values, color, width, status) in series.items()}
    all_values = [value for values, _, _, _ in plotted.values() for _, value in values]
    lower, upper = min(90, math.floor(min(all_values) / 10) * 10), math.ceil(max(all_values) / 10) * 10

    image = Image.new("RGB", (3200, 1840), "#ffffff")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, grid = "#17324d", "#27364a", "#5e6f82", "#dbe5ef"
    draw.rounded_rectangle((42, 30, 3158, 218), radius=18, fill="#f7fafc", outline="#c8d6e5", width=2)
    text(draw, (82, 55), "V5 同窗口研究路径：主候选与可审计的候选 / 执行观察线", navy, 42, True)
    text(draw, (84, 122), "全部使用 2021-05-06 至 2026-05-29 的 1,228 个交易日，并以起点 = 100 归一化。", muted, 23)
    text(draw, (84, 162), "正式表现正文仅允许 repaired baseline 与主候选 pairwise comparison；其余线仅展示研究轨迹，不构成收益排名或升级依据。", "#9a5b13", 21, True)

    left, top, right, bottom = 165, 310, 2980, 1272
    draw.rounded_rectangle((left, top, right, bottom), radius=8, fill="#fcfdff", outline="#d8e2ec", width=2)
    start_ordinal, end_ordinal = ordinal(START), ordinal(END)
    for year in [2021, 2022, 2023, 2024, 2025, 2026]:
        tick = date(year, 1, 1).toordinal()
        if start_ordinal <= tick <= end_ordinal:
            x = left + (tick - start_ordinal) / (end_ordinal - start_ordinal) * (right - left)
            draw.line((x, top, x, bottom), fill=grid, width=2)
            text(draw, (x - 25, bottom + 24), str(year), muted, 20)
    for value in range(int(lower), int(upper) + 1, 20):
        y = bottom - (value - lower) / (upper - lower) * (bottom - top)
        draw.line((left, y, right, y), fill="#b7c8d9" if value == 100 else "#e8eef5", width=3 if value == 100 else 2)
        text(draw, (80, y - 14), str(value), muted, 20)
    text(draw, (72, top + 58), "归一化\n净值指数", muted, 18, True)
    text(draw, (left + 22, top + 22), "正式窗口；研究线与主候选都保留其原始治理状态", "#30735f", 20, True)

    def points(values: list[tuple[str, float]]) -> list[tuple[float, float]]:
        return [(left + (ordinal(day) - start_ordinal) / (end_ordinal - start_ordinal) * (right - left), bottom - (value - lower) / (upper - lower) * (bottom - top)) for day, value in values]

    # Observation lines are intentionally behind the formal pair, so the chart cannot read as a hidden ranking table.
    for label, (values, color, width, status) in plotted.items():
        if status == "observation":
            draw.line(points(values), fill="#ffffff", width=width + 7, joint="curve")
            draw.line(points(values), fill=color, width=width, joint="curve")
    for label, (values, color, width, status) in plotted.items():
        if label == "repaired baseline":
            draw.line(points(values), fill="#ffffff", width=width + 7, joint="curve")
            draw.line(points(values), fill=color, width=width, joint="curve")
    values, color, width, _ = plotted["主候选 internal_subsleeve_mom12_70_30"]
    draw.line(points(values), fill="#ffffff", width=width + 9, joint="curve")
    draw.line(points(values), fill=color, width=width, joint="curve")

    legend_top = 1370
    draw.rounded_rectangle((165, legend_top, 1585, 1694), radius=10, fill="#fbfdff", outline="#c8d6e5", width=2)
    text(draw, (205, legend_top + 28), "正式 pairwise 比较", navy, 22, True)
    formal_labels = ["主候选 internal_subsleeve_mom12_70_30", "repaired baseline"]
    for index, label in enumerate(formal_labels):
        _, color, width, _ = plotted[label]
        y = legend_top + 88 + index * 52
        draw.line((210, y, 270, y), fill=color, width=width)
        text(draw, (295, y - 18), label, color, 20, True)
    text(draw, (205, legend_top + 215), "主候选状态：primary_forward_paper_candidate_not_accepted", muted, 18)
    text(draw, (205, legend_top + 253), "validation_not_independent；严格现金 NAV 与 QMT 合同缺口未消除。", muted, 18)

    panel_left = 1660
    draw.rounded_rectangle((panel_left, legend_top, 2980, 1694), radius=10, fill="#fffaf5", outline="#edc985", width=2)
    text(draw, (panel_left + 38, legend_top + 28), "同窗口研究 / 执行观察线（不进入正式表现表）", "#955b10", 22, True)
    for index, label in enumerate(["V5g 状态门 70/30", "V5h 固定 14:00 买入执行", "V5h pressure buy execution v1"]):
        _, color, width, _ = plotted[label]
        y = legend_top + 88 + index * 52
        draw.line((panel_left + 42, y, panel_left + 102, y), fill=color, width=width)
        text(draw, (panel_left + 125, y - 18), label, ink, 20)
    text(draw, (panel_left + 38, legend_top + 260), "它们用于呈现研究分支；不得由图形高度推导 accepted、可部署或更优的正式结论。", muted, 18)
    text(draw, (165, 1765), "数据来源：已冻结的 JoinQuant 日度净值、V5g limited engineering 与 V5h execution backtest 输出；没有生成新 target、没有改变任何模型状态。", muted, 18)

    FIGURES.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
