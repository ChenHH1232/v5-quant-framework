from __future__ import annotations

import math
import zipfile
from collections import defaultdict

from PIL import Image, ImageDraw

from generate_v5_sector_reference_trajectories import (
    CONFIG,
    DAILY_ZIP,
    END_DATE,
    FACTOR_ZIP,
    OUTPUT_DIR,
    REFERENCE_CODES,
    START_DATE,
    _font,
    _reference_series,
    _role_style,
)
import json


OUTPUT = OUTPUT_DIR / "figures" / "v5_all_sector_reference_overlay_2013_2026.png"


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str, size: int, *, bold: bool = False) -> None:
    draw.text(xy, text, fill=color, font=_font(size, bold))


def _light_color(role: str) -> str:
    if role in {"core_candidate", "candidate_after_platform_replication"}:
        return "#a7d8bb"
    if "excluded" in role or "blocked" in role:
        return "#c8d0dc"
    if "watchlist" in role or "manual" in role or "observation" in role:
        return "#b6cdf6"
    return "#f3c98b"


def _month_value(date: str) -> float:
    return int(date[:4]) + (int(date[4:6]) - 1) / 12


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = []
    with zipfile.ZipFile(DAILY_ZIP) as daily_zip, zipfile.ZipFile(FACTOR_ZIP) as factor_zip:
        for sector in config["candidate_sectors"]:
            series, availability = _reference_series(daily_zip, factor_zip, REFERENCE_CODES[sector["sector_id"]])
            if availability == "available":
                rows.append((sector, series))

    values_by_month: defaultdict[str, list[float]] = defaultdict(list)
    for _, series in rows:
        for date, value in series:
            values_by_month[date[:6]].append(value)
    average = [(month + "28", sum(values) / len(values)) for month, values in sorted(values_by_month.items()) if len(values) == len(rows)]

    all_values = [value for _, series in rows for _, value in series]
    lower = max(10.0, 10 ** math.floor(math.log10(min(all_values))))
    upper = 10 ** math.ceil(math.log10(max(all_values)))
    image = Image.new("RGB", (3000, 1650), "white")
    draw = ImageDraw.Draw(image)
    navy, grey, grid, average_color = "#14324a", "#52606d", "#d9e2ec", "#153e75"

    draw.rounded_rectangle((42, 28, 2958, 172), radius=18, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (76, 48), "V5 全部研究板块的市场环境轨迹：33 条本地参考证券与平均线", navy, 39, bold=True)
    _text(draw, (78, 106), "浅线：各研究板块的一只代表性 A 股复权价格，首个可用日 = 100。深线：33 条归一化轨迹的简单平均；两者均不是行业 ETF、策略净值或总回报。", grey, 20)

    left, top, right, bottom = 150, 275, 2860, 1360
    # Context bands explain the research chronology without turning the reference prices into a backtest.
    x_2021 = left + (2021 + 4 / 12 - 2013) / (2026 + 5 / 12 - 2013) * (right - left)
    draw.rectangle((left, top, x_2021, bottom), fill="#f8fbfe")
    draw.rectangle((x_2021, top, right, bottom), fill="#f4faf7")
    _text(draw, (left + 18, top + 18), "2013-2021：V1-V4 银行基础与 V5 研究环境", "#55708a", 19, bold=True)
    _text(draw, (x_2021 + 18, top + 18), "2021-05 至 2026-05：V5 冻结正式回测窗口", "#34735c", 19, bold=True)

    years = [2013, 2015, 2017, 2019, 2021, 2023, 2025, 2026]
    for year in years:
        x = left + (year - 2013) / (2026 + 5 / 12 - 2013) * (right - left)
        draw.line((x, top, x, bottom), fill=grid, width=2)
        _text(draw, (x - 24, bottom + 24), str(year), grey, 18)
    for y_value in (30, 100, 300, 1000, 3000):
        if not lower <= y_value <= upper:
            continue
        y = bottom - (math.log10(y_value) - math.log10(lower)) / (math.log10(upper) - math.log10(lower)) * (bottom - top)
        color = "#b6c5d5" if y_value == 100 else "#e6edf5"
        draw.line((left, y, right, y), fill=color, width=3 if y_value == 100 else 2)
        _text(draw, (72, y - 11), str(y_value), grey, 18)
    _text(draw, (70, top + 92), "归一化\n价格指数\n（对数）", grey, 17, bold=True)

    def plot(series: list[tuple[str, float]], color: str, width: int) -> None:
        points = []
        for date, value in series:
            x = left + (_month_value(date) - 2013) / (2026 + 5 / 12 - 2013) * (right - left)
            y = bottom - (math.log10(value) - math.log10(lower)) / (math.log10(upper) - math.log10(lower)) * (bottom - top)
            points.append((x, y))
        draw.line(points, fill=color, width=width, joint="curve")

    for sector, series in rows:
        plot(series, _light_color(sector["basket_role"]), 3)
    plot(average, average_color, 8)

    draw.rounded_rectangle((155, 1410, 1120, 1540), radius=12, fill="#ffffff", outline="#cbd5e1", width=2)
    legend_items = [("#a7d8bb", "核心 / 候选参考"), ("#b6cdf6", "观察 / 研究参考"), ("#f3c98b", "待研究参考"), ("#c8d0dc", "排除 / 数据门参考")]
    x = 185
    for color, label in legend_items:
        draw.line((x, 1448, x + 45, 1448), fill=color, width=8)
        _text(draw, (x + 55, 1436), label, grey, 17)
        x += 220
    draw.line((185, 1500, 230, 1500), fill=average_color, width=9)
    _text(draw, (242, 1488), "33 条参考轨迹的简单平均", average_color, 18, bold=True)

    draw.rounded_rectangle((1190, 1410, 2860, 1540), radius=12, fill="#fffaf5", outline="#f0c987", width=2)
    _text(draw, (1220, 1434), "读图边界", "#9a5b13", 20, bold=True)
    _text(draw, (1220, 1470), "这张图用于说明 V5 研究覆盖的行业环境差异与长期分化，不用于证明板块优劣、因子有效性、策略收益或未来表现。", grey, 18)
    _text(draw, (150, 1590), f"资料来源：本地 A 股日线与复权因子包；样本 {len(rows)} 条。日期统一截断于 {END_DATE[:4]}-{END_DATE[4:6]}-{END_DATE[6:]}。", grey, 17)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
