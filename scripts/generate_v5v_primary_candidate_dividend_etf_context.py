from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "v5v_application_final_report_readiness" / "current" / "figures"
CACHE = ROOT / "v5v_application_final_report_readiness" / "current" / "etf_context_price_cache"
CANDIDATE_NAV = ROOT / "data" / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution" / "daily_returns_primary_result_1_20.csv"
OUTPUT = FIGURES / "v5_primary_candidate_vs_dividend_etf_context_2021_2026.png"
MANIFEST = CACHE / "v5v_dividend_etf_context_manifest.csv"
START, END = "20210506", "20260529"
REFERENCES = {
    "510880.SH": ("上证红利 ETF（510880.SH）", "#2f855a", "full"),
    "512890.SH": ("红利低波 ETF（512890.SH）", "#2563a7", "one_missing_day"),
    "399986.SZ": ("中证银行指数（399986.SZ）", "#1f7a8c", "full"),
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
    nav_column = rows[0].index("nav")
    return {row[0][:10].replace("-", ""): float(row[nav_column]) for row in rows[1:] if len(row) > nav_column and START <= row[0][:10].replace("-", "") <= END and row[nav_column]}


def fetch_or_load(code: str) -> tuple[dict[str, float], str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    file_path = CACHE / f"{code.replace('.', '_')}_tencent_qfq_daily.csv"
    market_code = ("sh" if code.endswith(".SH") else "sz") + code[:6]
    source_template = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={market_code},day,{start},{end},640,qfq"
    if not file_path.exists():
        rows = []
        # Tencent returns at most 640 sessions; two non-overlapping ranges cover the formal window.
        for range_start, range_end in (("2021-05-01", "2023-10-08"), ("2023-10-09", "2026-05-31")):
            url = source_template.format(market_code=market_code, start=range_start, end=range_end)
            request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com"})
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            values = ((payload.get("data") or {}).get(market_code) or {}).get("qfqday") or ((payload.get("data") or {}).get(market_code) or {}).get("day") or []
            rows.extend((record[0], record[2]) for record in values if len(record) >= 3)
        with file_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("trade_date", "close"))
            writer.writerows(rows)
    with file_path.open(encoding="utf-8", newline="") as handle:
        values = {row["trade_date"].replace("-", ""): float(row["close"]) for row in csv.DictReader(handle) if START <= row["trade_date"].replace("-", "") <= END}
    return values, source_template.format(market_code=market_code, start="{start}", end="{end}")


def normalized(values: dict[str, float]) -> list[tuple[str, float]]:
    days = sorted(values)
    base = values[days[0]]
    return [(day, values[day] / base * 100) for day in days]


def main() -> None:
    candidate = candidate_series()
    fetched = {code: fetch_or_load(code) for code in REFERENCES}
    full_days = sorted(set(candidate) & set(fetched["510880.SH"][0]) & set(fetched["399986.SZ"][0]))
    if len(full_days) != 1228 or full_days[0] != START or full_days[-1] != END:
        raise ValueError(f"Unexpected full-window ETF context coverage: {len(full_days)}")
    plotted = {"主候选 internal_subsleeve_mom12_70_30": ([(day, candidate[day] / candidate[full_days[0]] * 100) for day in full_days], "#b42318", 13)}
    rows_for_manifest = []
    for code, (label, color, status) in REFERENCES.items():
        values, url = fetched[code]
        plotted[label] = (normalized(values), color, 7 if status != "partial" else 6)
        cache_file = CACHE / f"{code.replace('.', '_')}_tencent_qfq_daily.csv"
        rows_for_manifest.append({"code": code, "label": label, "first_date": min(values), "last_date": max(values), "observations": len(values), "contract": "tencent_qfq_adjusted_price_return_not_total_return", "use_scope": "economic_exposure_context_only", "source_url": url, "sha256": hashlib.sha256(cache_file.read_bytes()).hexdigest()})
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows_for_manifest[0].keys())
        writer.writeheader()
        writer.writerows(rows_for_manifest)

    all_values = [value for values, _, _ in plotted.values() for _, value in values]
    lower, upper = min(70, math.floor(min(all_values) / 10) * 10), math.ceil(max(all_values) / 10) * 10
    image = Image.new("RGB", (3200, 1860), "#ffffff")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, grid, candidate_color = "#17324d", "#27364a", "#5e6f82", "#dbe5ef", "#b42318"
    draw.rounded_rectangle((42, 30, 3158, 222), radius=18, fill="#f7fafc", outline="#c8d6e5", width=2)
    text(draw, (82, 56), "V5 正式窗口：主候选与红利 / 红利低波 / 银行参考的价格轨迹", navy, 40, True)
    text(draw, (84, 123), "统一时间轴为 2021-05-06 至 2026-05-29。ETF 与指数均为本地缓存的腾讯 qfq adjusted-price 序列。", muted, 22)
    text(draw, (84, 163), "它们仅用于 economic exposure context：不计算 Alpha、Beta、IR 或正式超额收益，不作为策略收益排行榜。", "#9a5b13", 21, True)

    left, top, right, bottom = 165, 314, 2980, 1284
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
    text(draw, (70, top + 58), "归一化\n价格 / 净值", muted, 18, True)
    text(draw, (left + 22, top + 22), "完整窗口：红利 ETF 与中证银行；红利低波少 1 日未插值。自由现金流 ETF 因上市过晚已剔除。", "#30735f", 18, True)

    def points(values: list[tuple[str, float]]) -> list[tuple[float, float]]:
        return [(left + (ordinal(day) - start_ordinal) / (end_ordinal - start_ordinal) * (right - left), bottom - (value - lower) / (upper - lower) * (bottom - top)) for day, value in values]

    full_index = {day: index for index, day in enumerate(full_days)}

    def segments(values: list[tuple[str, float]]) -> list[list[tuple[float, float]]]:
        output: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        previous_index: int | None = None
        for day, value in values:
            index = full_index.get(day)
            if index is not None and previous_index is not None and index != previous_index + 1:
                if current:
                    output.append(current)
                current = []
            current.append((left + (ordinal(day) - start_ordinal) / (end_ordinal - start_ordinal) * (right - left), bottom - (value - lower) / (upper - lower) * (bottom - top)))
            previous_index = index
        if current:
            output.append(current)
        return output

    for label, (values, color, width) in plotted.items():
        if label.startswith("主候选"):
            continue
        for segment in segments(values):
            draw.line(segment, fill="#ffffff", width=width + 7, joint="curve")
            draw.line(segment, fill=color, width=width, joint="curve")
    candidate_line, _, candidate_width = plotted["主候选 internal_subsleeve_mom12_70_30"]
    draw.line(points(candidate_line), fill="#ffffff", width=candidate_width + 9, joint="curve")
    draw.line(points(candidate_line), fill=candidate_color, width=candidate_width, joint="curve")

    legend_top = 1390
    draw.rounded_rectangle((165, legend_top, 1640, 1714), radius=10, fill="#fbfdff", outline="#c8d6e5", width=2)
    legend_labels = ["主候选 internal_subsleeve_mom12_70_30", *[value[0] for value in REFERENCES.values()]]
    for index, label in enumerate(legend_labels):
        values, color, width = plotted[label]
        y = legend_top + 50 + index * 56
        draw.line((210, y, 275, y), fill=color, width=width)
        suffix = "（平台日度净值）" if index == 0 else "（价格参考）"
        text(draw, (305, y - 19), label + suffix, color if index == 0 else ink, 20, index == 0)

    box_left = 1700
    draw.rounded_rectangle((box_left, legend_top, 2980, 1714), radius=10, fill="#fffaf5", outline="#edc985", width=2)
    text(draw, (box_left + 38, legend_top + 28), "解释边界与数据可得性", "#955b10", 22, True)
    text(draw, (box_left + 38, legend_top + 83), "红利 ETF、红利低波 ETF 与中证银行指数可覆盖或接近覆盖正式窗口。", ink, 19)
    text(draw, (box_left + 38, legend_top + 128), "红利低波少 1 个交易日：图中保持空缺，不做插值。", muted, 19)
    text(draw, (box_left + 38, legend_top + 173), "自由现金流 ETF 仅自 2025-02-27 起有数据，因不满足完整窗口要求，未纳入本图。", muted, 19)
    text(draw, (box_left + 38, legend_top + 228), "ETF total-return contract 仍缺失；主候选为 primary_forward_paper_candidate_not_accepted。", muted, 18)
    text(draw, (box_left + 38, legend_top + 270), "strict_cash_nav_unavailable、qmt_contract_incomplete，独立前瞻纸面周期尚未形成。", muted, 18)
    text(draw, (165, 1792), "来源与复核：见 v5v_application_final_report_readiness/current/etf_context_price_cache/v5v_dividend_etf_context_manifest.csv。数据截断于 2026-05-31。", muted, 17)

    FIGURES.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
