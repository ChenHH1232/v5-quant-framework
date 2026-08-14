from __future__ import annotations

import csv
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

from generate_v5_sector_reference_trajectories import (
    CHINESE_NAMES,
    CONFIG,
    DAILY_ZIP,
    FACTOR_ZIP,
    OUTPUT_DIR,
    REFERENCE_CODES,
    _font,
    _reference_series,
)


PRIMARY_NAV = Path("data/joinquant_exports/v5f_internal_subsleeve_mom12_70_30/historical_platform_attribution/daily_returns_primary_result_1_20.csv")
OUTPUT = OUTPUT_DIR / "figures" / "v5_primary_candidate_vs_core_sector_context_2021_2026.png"
START, END = "20210506", "20260529"
HIGHLIGHTS = {
    "bank": "#9fcfd0",
    "utilities_electricity": "#f2c58a",
    "highway_infrastructure": "#c9b5f5",
    "port_rail_infrastructure": "#a9d4b6",
}


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str, size: int, *, bold: bool = False) -> None:
    draw.text(xy, text, fill=color, font=_font(size, bold))


def _date_value(date: str) -> float:
    return int(date[:4]) + (int(date[4:6]) - 1) / 12 + (int(date[6:8]) - 1) / 365


def _primary_series() -> list[tuple[str, float]]:
    with PRIMARY_NAV.open(encoding="gb18030", newline="") as handle:
        rows = list(csv.DictReader(handle))
    output = []
    for row in rows:
        date = row["时间"][:10].replace("-", "")
        if START <= date <= END:
            output.append((date, float(row["nav"])))
    base = output[0][1]
    return [(date, value / base * 100) for date, value in output]


def _window_normalized(series: list[tuple[str, float]]) -> list[tuple[str, float]]:
    trimmed = [(date, value) for date, value in series if START <= date <= END]
    base = trimmed[0][1]
    return [(date, value / base * 100) for date, value in trimmed]


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    reference_rows = []
    with zipfile.ZipFile(DAILY_ZIP) as daily_zip, zipfile.ZipFile(FACTOR_ZIP) as factor_zip:
        for sector in config["candidate_sectors"]:
            series, availability = _reference_series(daily_zip, factor_zip, REFERENCE_CODES[sector["sector_id"]])
            if availability == "available":
                reference_rows.append((sector["sector_id"], _window_normalized(series)))
    average_by_month: defaultdict[str, list[float]] = defaultdict(list)
    for _, series in reference_rows:
        for date, value in series:
            average_by_month[date[:6]].append(value)
    average = [(month + "28", sum(values) / len(values)) for month, values in sorted(average_by_month.items()) if len(values) == len(reference_rows)]
    primary = _primary_series()
    all_values = [value for _, series in reference_rows for _, value in series] + [value for _, value in primary]
    lower = max(60.0, 10 * math.floor(min(all_values) / 10))
    upper = 10 * math.ceil(max(all_values) / 10)

    image = Image.new("RGB", (3000, 1640), "white")
    draw = ImageDraw.Draw(image)
    navy, grey, grid, model_color = "#14324a", "#52606d", "#d9e2ec", "#b42318"
    draw.rounded_rectangle((42, 28, 2958, 176), radius=18, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (76, 48), "V5 正式回测窗口：主候选净值与四个核心研究板块的市场环境", navy, 39, bold=True)
    _text(draw, (78, 106), "低对比背景：33 条参考证券平均与银行、电力、高速、港口铁路的本地复权价格代理。高亮：主候选 internal_subsleeve_mom12_70_30 的平台日度净值。", grey, 20)

    left, top, right, bottom = 150, 270, 2860, 1325
    draw.rounded_rectangle((left, top, right, bottom), radius=8, fill="#fcfdff", outline="#e2e8f0", width=2)
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    for year in years:
        x = left + (year - 2021) / (2026 + 5 / 12 - 2021) * (right - left)
        draw.line((x, top, x, bottom), fill=grid, width=2)
        _text(draw, (x - 23, bottom + 24), str(year), grey, 18)
    for value in range(int(lower), int(upper) + 1, 25):
        y = bottom - (value - lower) / (upper - lower) * (bottom - top)
        draw.line((left, y, right, y), fill="#b6c5d5" if value == 100 else "#e6edf5", width=3 if value == 100 else 2)
        _text(draw, (78, y - 11), str(value), grey, 18)
    _text(draw, (70, top + 92), "归一化\n净值 / 价格\n指数", grey, 17, bold=True)
    _text(draw, (left + 18, top + 18), "正式共同样本：2021-05-06 至 2026-05-29，1,228 个交易日", "#34735c", 19, bold=True)

    def points(series: list[tuple[str, float]]) -> list[tuple[float, float]]:
        return [
            (
                left + (_date_value(date) - _date_value(START)) / (_date_value(END) - _date_value(START)) * (right - left),
                bottom - (value - lower) / (upper - lower) * (bottom - top),
            )
            for date, value in series
        ]

    # Context first: all comparison content stays visually secondary to the candidate path.
    for sector_id, series in reference_rows:
        if sector_id not in HIGHLIGHTS:
            draw.line(points(series), fill="#edf1f7", width=2, joint="curve")
    for sector_id, series in reference_rows:
        if sector_id in HIGHLIGHTS:
            draw.line(points(series), fill=HIGHLIGHTS[sector_id], width=4, joint="curve")
    draw.line(points(average), fill="#a3adbb", width=5, joint="curve")
    primary_points = points(primary)
    draw.line(primary_points, fill="#ffffff", width=19, joint="curve")
    draw.line(primary_points, fill=model_color, width=12, joint="curve")

    draw.rounded_rectangle((155, 1390, 1580, 1535), radius=12, fill="#ffffff", outline="#cbd5e1", width=2)
    draw.line((185, 1430, 238, 1430), fill=model_color, width=12)
    _text(draw, (252, 1417), "主候选：internal_subsleeve_mom12_70_30（历史平台净值）", model_color, 20, bold=True)
    _text(draw, (252, 1452), "状态：primary_forward_paper_candidate_not_accepted", grey, 18)
    legend_x = 185
    for sector_id, color in HIGHLIGHTS.items():
        draw.line((legend_x, 1498, legend_x + 42, 1498), fill=color, width=6)
        _text(draw, (legend_x + 52, 1486), CHINESE_NAMES[sector_id], grey, 17)
        legend_x += 220
    draw.line((1080, 1498, 1122, 1498), fill="#a3adbb", width=6)
    _text(draw, (1132, 1486), "33 条参考证券平均", grey, 17)

    draw.rounded_rectangle((1625, 1390, 2860, 1535), radius=12, fill="#fffaf5", outline="#f0c987", width=2)
    _text(draw, (1655, 1415), "读图边界", "#9a5b13", 20, bold=True)
    _text(draw, (1655, 1450), "背景价格代理与主候选净值的回报合同不同，仅用于市场环境叙事，禁止据此计算 Alpha、Beta、IR 或直接比较收益。", grey, 18)
    _text(draw, (1655, 1485), "主候选的正向历史观察不构成独立验证、accepted、实盘批准或未来收益承诺。", grey, 18)
    _text(draw, (150, 1590), "主候选来源：JoinQuant 导出日度净值；背景来源：本地 A 股日线与复权因子包。严格现金 NAV、QMT 历史合同与独立前瞻纸面周期仍未完成。", grey, 17)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
