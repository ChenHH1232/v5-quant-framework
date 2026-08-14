from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "v5v_application_final_report_readiness" / "current" / "figures"
STATS = ROOT / "v5r_overall_research_governance_report_draft" / "current" / "v5r_performance_comparison_table.csv"
CANDIDATE_NAV = ROOT / "data" / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution" / "daily_returns_primary_result_1_20.csv"
BASELINE_NAV = ROOT / "data" / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution" / "daily_returns_baseline_result_1_21.csv"
OUTPUT = FIGURES / "v5_primary_candidate_vs_repaired_baseline_2021_2026.png"
START, END = "20210506", "20260529"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fill: str, size: int, bold: bool = False) -> None:
    draw.text(xy, value, fill=fill, font=font(size, bold))


def platform_nav(path: Path) -> dict[str, float]:
    with path.open(encoding="gb18030", newline="") as handle:
        rows = list(csv.reader(handle))
    header = rows[0]
    nav_index = header.index("nav")
    values: dict[str, float] = {}
    for row in rows[1:]:
        if len(row) <= nav_index:
            continue
        day = row[0][:10].replace("-", "")
        if START <= day <= END and row[nav_index]:
            values[day] = float(row[nav_index])
    return values


def normalized_common_series() -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    candidate, baseline = platform_nav(CANDIDATE_NAV), platform_nav(BASELINE_NAV)
    days = sorted(set(candidate) & set(baseline))
    if len(days) != 1228 or days[0] != START or days[-1] != END:
        raise ValueError(f"Unexpected formal common sample: {len(days)} {days[:1]} {days[-1:]}")
    return ([(day, candidate[day] / candidate[days[0]] * 100) for day in days], [(day, baseline[day] / baseline[days[0]] * 100) for day in days])


def stats() -> dict[str, dict[str, str]]:
    with STATS.open(encoding="utf-8-sig", newline="") as handle:
        return {row["canonical_model_id"]: row for row in csv.DictReader(handle)}


def date_axis(day: str) -> float:
    return date(int(day[:4]), int(day[4:6]), int(day[6:8])).toordinal()


def main() -> None:
    candidate, baseline = normalized_common_series()
    report_stats = stats()
    c_stat, b_stat = report_stats["internal_subsleeve_mom12_70_30"], report_stats["v57f_startup_preload_repaired_baseline"]
    values = [value for _, value in candidate + baseline]
    lower = min(90, math.floor(min(values) / 10) * 10)
    upper = math.ceil(max(values) / 10) * 10

    image = Image.new("RGB", (3200, 1820), "#ffffff")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, grid = "#17324d", "#27364a", "#5e6f82", "#dbe5ef"
    candidate_color, baseline_color = "#b42318", "#186f78"

    draw.rounded_rectangle((42, 30, 3158, 210), radius=18, fill="#f7fafc", outline="#c8d6e5", width=2)
    text(draw, (82, 57), "V5 正式共同窗口：主候选与 repaired baseline 的唯一正式可比比较", navy, 42, True)
    text(draw, (84, 123), "同父策略、同回报合同、同 1,228 个交易日。两条线均以 2021-05-06 = 100 归一化。", muted, 23)
    text(draw, (84, 159), "此图是历史样本中的 pairwise observation；validation_not_independent，主候选尚未 accepted。", "#9a5b13", 22, True)

    left, top, right, bottom = 165, 300, 2980, 1275
    draw.rounded_rectangle((left, top, right, bottom), radius=8, fill="#fcfdff", outline="#d8e2ec", width=2)
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    start_ordinal, end_ordinal = date_axis(START), date_axis(END)
    for year in years:
        ordinal = date(year, 1, 1).toordinal()
        if start_ordinal <= ordinal <= end_ordinal:
            x = left + (ordinal - start_ordinal) / (end_ordinal - start_ordinal) * (right - left)
            draw.line((x, top, x, bottom), fill=grid, width=2)
            text(draw, (x - 25, bottom + 24), str(year), muted, 20)
    for value in range(int(lower), int(upper) + 1, 20):
        y = bottom - (value - lower) / (upper - lower) * (bottom - top)
        draw.line((left, y, right, y), fill="#b7c8d9" if value == 100 else "#e8eef5", width=3 if value == 100 else 2)
        text(draw, (80, y - 14), str(value), muted, 20)
    text(draw, (72, top + 58), "归一化\n净值指数", muted, 18, True)
    text(draw, (left + 22, top + 22), "正式共同样本：2021-05-06 至 2026-05-29 | 1,228 日", "#30735f", 20, True)

    def points(series: list[tuple[str, float]]) -> list[tuple[float, float]]:
        return [(left + (date_axis(day) - start_ordinal) / (end_ordinal - start_ordinal) * (right - left), bottom - (value - lower) / (upper - lower) * (bottom - top)) for day, value in series]

    # Baseline draws first, leaving the primary candidate visually dominant without hiding the comparison.
    draw.line(points(baseline), fill="#ffffff", width=16, joint="curve")
    draw.line(points(baseline), fill=baseline_color, width=9, joint="curve")
    draw.line(points(candidate), fill="#ffffff", width=22, joint="curve")
    draw.line(points(candidate), fill=candidate_color, width=13, joint="curve")

    legend_top = 1370
    draw.rounded_rectangle((165, legend_top, 1450, 1665), radius=10, fill="#fbfdff", outline="#c8d6e5", width=2)
    draw.line((210, legend_top + 58, 280, legend_top + 58), fill=candidate_color, width=13)
    text(draw, (305, legend_top + 40), "主候选：internal_subsleeve_mom12_70_30", candidate_color, 22, True)
    draw.line((210, legend_top + 126, 280, legend_top + 126), fill=baseline_color, width=9)
    text(draw, (305, legend_top + 108), "正式基线：v57f_startup_preload_repaired_baseline", baseline_color, 22, True)
    text(draw, (210, legend_top + 194), "状态：primary_forward_paper_candidate_not_accepted", muted, 19)
    text(draw, (210, legend_top + 236), "严格现金 NAV 与独立前瞻纸面周期尚未形成。", muted, 19)

    panel_left = 1530
    draw.rounded_rectangle((panel_left, legend_top, 2980, 1665), radius=10, fill="#fffaf5", outline="#edc985", width=2)
    text(draw, (panel_left + 38, legend_top + 30), "审计统计 | 仅用于该同合同比较", "#955b10", 24, True)
    headers = ["模型", "总收益", "年化收益", "最大回撤", "夏普", "信息比率"]
    columns = [panel_left + 38, panel_left + 400, panel_left + 600, panel_left + 830, panel_left + 1080, panel_left + 1240]
    for x, label in zip(columns, headers):
        text(draw, (x, legend_top + 87), label, muted, 18, True)
    rows = [("主候选", c_stat, candidate_color), ("repaired baseline", b_stat, baseline_color)]
    for index, (label, row, color) in enumerate(rows):
        y = legend_top + 135 + index * 55
        information_ratio = f"{float(row['information_ratio']):.3f}" if row['information_ratio'] != 'not_available' else "不适用"
        values = [label, f"{float(row['total_return_pct']):.2f}%", f"{float(row['annualized_return_pct']):.2f}%", f"{float(row['max_drawdown_pct']):.2f}%", f"{float(row['sharpe_ratio']):.3f}", information_ratio]
        for x, value in zip(columns, values):
            text(draw, (x, y), value, color if x == columns[0] else ink, 19, x == columns[0])
    text(draw, (panel_left + 38, legend_top + 260), "来源：V5r 已核验正式表现表。候选相对 baseline：总收益 +11.43 个百分点，最大回撤差 -0.05 个百分点。", muted, 18)
    text(draw, (165, 1740), "回报合同：local_daily_parent_strategy_contract。此处不构成独立验证、投资建议、收益承诺或 accepted/live 结论。", muted, 18)

    FIGURES.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
