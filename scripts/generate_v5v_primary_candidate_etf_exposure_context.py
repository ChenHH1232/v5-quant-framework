from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "v5v_application_final_report_readiness" / "current" / "figures"
ETF_DATA = ROOT / "v5p_benchmark_discovery_and_research_sequence" / "current" / "benchmark_data"
CANDIDATE_NAV = ROOT / "data" / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution" / "daily_returns_primary_result_1_20.csv"
OUTPUT = FIGURES / "v5_primary_candidate_vs_local_etf_exposure_context_2021_2026.png"
START, END = "20210506", "20260529"
ETFS = {
    "512800_SH_daily.csv": ("银行ETF华宝（512800.SH）", "#317a87"),
    "159930_SZ_daily.csv": ("能源ETF（159930.SZ）", "#b7791f"),
    "159996_SZ_daily.csv": ("家电ETF（159996.SZ）", "#805ad5"),
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fill: str, size: int, bold: bool = False) -> None:
    draw.text(xy, value, fill=fill, font=font(size, bold))


def ordinal(day: str) -> int:
    return date(int(day[:4]), int(day[4:6]), int(day[6:8])).toordinal()


def candidate_series() -> dict[str, float]:
    with CANDIDATE_NAV.open(encoding="gb18030", newline="") as handle:
        rows = list(csv.reader(handle))
    nav_index = rows[0].index("nav")
    return {row[0][:10].replace("-", ""): float(row[nav_index]) for row in rows[1:] if len(row) > nav_index and START <= row[0][:10].replace("-", "") <= END and row[nav_index]}


def etf_series(path: Path) -> dict[str, float]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["trade_date"].replace("-", ""): float(row["close"]) for row in csv.DictReader(handle) if START <= row["trade_date"].replace("-", "") <= END}


def normalize(values: dict[str, float], days: list[str]) -> list[tuple[str, float]]:
    base = values[days[0]]
    return [(day, values[day] / base * 100) for day in days]


def main() -> None:
    candidate = candidate_series()
    etfs = {name: etf_series(ETF_DATA / filename) for filename, (name, _) in ETFS.items()}
    common_days = sorted(set(candidate).intersection(*(set(series) for series in etfs.values())))
    if len(common_days) != 1228 or common_days[0] != START or common_days[-1] != END:
        raise ValueError(f"ETF context sample is not the formal common window: {len(common_days)}")
    candidate_line = normalize(candidate, common_days)
    etf_lines = {name: normalize(series, common_days) for name, series in etfs.items()}
    all_values = [value for _, value in candidate_line] + [value for line in etf_lines.values() for _, value in line]
    lower, upper = min(75, math.floor(min(all_values) / 10) * 10), math.ceil(max(all_values) / 10) * 10

    image = Image.new("RGB", (3200, 1820), "#ffffff")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, grid, candidate_color = "#17324d", "#27364a", "#5e6f82", "#dbe5ef", "#b42318"
    draw.rounded_rectangle((42, 30, 3158, 220), radius=18, fill="#f7fafc", outline="#c8d6e5", width=2)
    text(draw, (82, 56), "V5 正式共同窗口：主候选与本地可用 ETF 的经济暴露参考", navy, 42, True)
    text(draw, (84, 123), "同一日期窗口、各自起点 = 100。ETF 为 eastmoney_fqt_1 adjusted-price 序列，不是可追溯总回报合同。", muted, 23)
    text(draw, (84, 163), "因此本图不计算 Alpha、Beta、IR 或超额收益，也不构成正式策略表现排序。", "#9a5b13", 22, True)

    left, top, right, bottom = 165, 310, 2980, 1270
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
    text(draw, (72, top + 58), "归一化\n价格 / 净值", muted, 18, True)
    text(draw, (left + 22, top + 22), "共同观察：2021-05-06 至 2026-05-29 | 1,228 日 | 经济暴露参考", "#30735f", 20, True)

    def points(series: list[tuple[str, float]]) -> list[tuple[float, float]]:
        return [(left + (ordinal(day) - start_ordinal) / (end_ordinal - start_ordinal) * (right - left), bottom - (value - lower) / (upper - lower) * (bottom - top)) for day, value in series]

    for filename, (label, color) in ETFS.items():
        draw.line(points(etf_lines[label]), fill="#ffffff", width=12, joint="curve")
        draw.line(points(etf_lines[label]), fill=color, width=6, joint="curve")
    draw.line(points(candidate_line), fill="#ffffff", width=22, joint="curve")
    draw.line(points(candidate_line), fill=candidate_color, width=13, joint="curve")

    box_top = 1370
    draw.rounded_rectangle((165, box_top, 1585, 1668), radius=10, fill="#fbfdff", outline="#c8d6e5", width=2)
    draw.line((210, box_top + 56, 280, box_top + 56), fill=candidate_color, width=13)
    text(draw, (305, box_top + 38), "主候选：internal_subsleeve_mom12_70_30（平台日度净值）", candidate_color, 22, True)
    for index, (filename, (label, color)) in enumerate(ETFS.items()):
        y = box_top + 120 + index * 50
        draw.line((210, y, 270, y), fill=color, width=6)
        text(draw, (295, y - 17), label, ink, 20)

    right_box = 1660
    draw.rounded_rectangle((right_box, box_top, 2980, 1668), radius=10, fill="#fffaf5", outline="#edc985", width=2)
    text(draw, (right_box + 38, box_top + 30), "合同与解释边界", "#955b10", 24, True)
    text(draw, (right_box + 38, box_top + 91), "本地没有覆盖正式窗口、可追溯总回报合同的广义红利 ETF。", ink, 20, True)
    text(draw, (right_box + 38, box_top + 136), "所示 ETF 仅是已缓存、完整覆盖窗口的板块价格暴露参考。", muted, 20)
    text(draw, (right_box + 38, box_top + 181), "基建 50 / 电力 ETF 的上市或数据覆盖不足，未被画入该图。", muted, 20)
    text(draw, (right_box + 38, box_top + 226), "主候选：primary_forward_paper_candidate_not_accepted；历史观察不构成独立验证。", muted, 18)
    text(draw, (165, 1740), "限制：ETF total-return contract 缺失；strict_cash_nav_unavailable、qmt_contract_incomplete，且独立前瞻纸面周期尚未形成。", muted, 18)

    FIGURES.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
