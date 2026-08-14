from __future__ import annotations

import json
import math
import zipfile
from collections import defaultdict

from PIL import Image, ImageDraw

from generate_v5_sector_reference_trajectories import (
    CHINESE_NAMES,
    CONFIG,
    DAILY_ZIP,
    END_DATE,
    FACTOR_ZIP,
    OUTPUT_DIR,
    REFERENCE_CODES,
    _font,
    _reference_series,
)


OUTPUT = OUTPUT_DIR / "figures" / "v5_core_sleeve_reference_comparison_2013_2026.png"
HIGHLIGHTS = {
    "bank": "#167c80",
    "utilities_electricity": "#d97706",
    "highway_infrastructure": "#7c3aed",
    "port_rail_infrastructure": "#2f855a",
}


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str, size: int, *, bold: bool = False) -> None:
    draw.text(xy, text, fill=color, font=_font(size, bold))


def _month_value(date: str) -> float:
    return int(date[:4]) + (int(date[4:6]) - 1) / 12


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = []
    with zipfile.ZipFile(DAILY_ZIP) as daily_zip, zipfile.ZipFile(FACTOR_ZIP) as factor_zip:
        for sector in config["candidate_sectors"]:
            series, availability = _reference_series(daily_zip, factor_zip, REFERENCE_CODES[sector["sector_id"]])
            if availability == "available":
                rows.append((sector["sector_id"], series))

    by_month: defaultdict[str, list[float]] = defaultdict(list)
    for _, series in rows:
        for date, value in series:
            by_month[date[:6]].append(value)
    average = [(month + "28", sum(values) / len(values)) for month, values in sorted(by_month.items()) if len(values) == len(rows)]
    values = [value for _, series in rows for _, value in series]
    lower = max(10.0, 10 ** math.floor(math.log10(min(values))))
    upper = 10 ** math.ceil(math.log10(max(values)))

    image = Image.new("RGB", (3000, 1650), "white")
    draw = ImageDraw.Draw(image)
    navy, grey, grid = "#14324a", "#52606d", "#d9e2ec"
    draw.rounded_rectangle((42, 28, 2958, 172), radius=18, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (76, 48), "V5 四个核心研究 sleeve 的市场环境：与全部已研究板块参考轨迹对比", navy, 39, bold=True)
    _text(draw, (78, 106), "浅灰线为其余参考证券；彩色线为银行、电力、高速、港口铁路的代表性证券；深海军蓝粗线为 33 条归一化轨迹的简单平均。", grey, 20)

    left, top, right, bottom = 150, 270, 2860, 1355
    x_2021 = left + (2021 + 4 / 12 - 2013) / (2026 + 5 / 12 - 2013) * (right - left)
    draw.rectangle((left, top, x_2021, bottom), fill="#f8fbfe")
    draw.rectangle((x_2021, top, right, bottom), fill="#f4faf7")
    _text(draw, (left + 18, top + 18), "2013-2021：银行基础与 V5 研究环境", "#55708a", 19, bold=True)
    _text(draw, (x_2021 + 18, top + 18), "2021-05 至 2026-05：V5 冻结正式回测窗口", "#34735c", 19, bold=True)

    years = [2013, 2015, 2017, 2019, 2021, 2023, 2025, 2026]
    for year in years:
        x = left + (year - 2013) / (2026 + 5 / 12 - 2013) * (right - left)
        draw.line((x, top, x, bottom), fill=grid, width=2)
        _text(draw, (x - 24, bottom + 24), str(year), grey, 18)
    for y_value in (30, 100, 300, 1000, 3000):
        if lower <= y_value <= upper:
            y = bottom - (math.log10(y_value) - math.log10(lower)) / (math.log10(upper) - math.log10(lower)) * (bottom - top)
            draw.line((left, y, right, y), fill="#b6c5d5" if y_value == 100 else "#e6edf5", width=3 if y_value == 100 else 2)
            _text(draw, (72, y - 11), str(y_value), grey, 18)
    _text(draw, (70, top + 92), "归一化\n价格指数\n（对数）", grey, 17, bold=True)

    def points(series: list[tuple[str, float]]) -> list[tuple[float, float]]:
        return [
            (
                left + (_month_value(date) - 2013) / (2026 + 5 / 12 - 2013) * (right - left),
                bottom - (math.log10(value) - math.log10(lower)) / (math.log10(upper) - math.log10(lower)) * (bottom - top),
            )
            for date, value in series
        ]

    for sector_id, series in rows:
        if sector_id not in HIGHLIGHTS:
            draw.line(points(series), fill="#d8e1ee", width=3, joint="curve")
    for sector_id, series in rows:
        if sector_id in HIGHLIGHTS:
            draw.line(points(series), fill=HIGHLIGHTS[sector_id], width=7, joint="curve")
    # Render last: the aggregate is the visual benchmark and must sit above every sector path.
    average_points = points(average)
    draw.line(average_points, fill="#ffffff", width=19, joint="curve")
    draw.line(average_points, fill="#0f2747", width=12, joint="curve")

    draw.rounded_rectangle((155, 1410, 1475, 1540), radius=12, fill="#ffffff", outline="#cbd5e1", width=2)
    x = 185
    for sector_id, color in HIGHLIGHTS.items():
        draw.line((x, 1445, x + 46, 1445), fill=color, width=9)
        _text(draw, (x + 58, 1433), f"{CHINESE_NAMES[sector_id]}（{REFERENCE_CODES[sector_id]}）", color, 18, bold=True)
        x += 315
    draw.line((185, 1500, 230, 1500), fill="#0f2747", width=9)
    _text(draw, (242, 1488), "33 条参考轨迹的简单平均", "#0f2747", 18, bold=True)

    draw.rounded_rectangle((1520, 1410, 2860, 1540), radius=12, fill="#fffaf5", outline="#f0c987", width=2)
    _text(draw, (1550, 1432), "读图边界", "#9a5b13", 20, bold=True)
    _text(draw, (1550, 1468), "四条高亮线说明核心研究板块所经历的市场环境；并非四个独立已接受策略，也不构成收益比较或投资建议。", grey, 18)
    _text(draw, (150, 1590), f"资料来源：本地 A 股日线与复权因子包；33 条参考证券。所有轨迹统一截断于 {END_DATE[:4]}-{END_DATE[4:6]}-{END_DATE[6:]}。", grey, 17)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
