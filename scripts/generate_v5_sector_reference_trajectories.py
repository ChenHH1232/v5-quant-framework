from __future__ import annotations

import csv
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "v5a.1_broad_sector_coarse_screening.json"
DAILY_ZIP = Path(r"D:\hh\一分钟行情数据 2000至2026\股票全周期K线包\历史数据\a股日线.zip")
FACTOR_ZIP = Path(r"D:\hh\一分钟行情数据 2000至2026\股票全周期K线包\历史数据\复权因子.zip")
OUTPUT_DIR = ROOT / "v5v_application_final_report_readiness" / "current"
OUTPUT = OUTPUT_DIR / "figures" / "v5_sector_reference_trajectories_2013_2026.png"
MANIFEST = OUTPUT_DIR / "v5_sector_reference_trajectories_2013_2026_manifest.csv"

START_DATE = "20130101"
END_DATE = "20260531"

# One liquid, long-lived A-share reference security per research sector. These are market-context proxies only.
REFERENCE_CODES = {
    "bank": "600036.SH",
    "utilities_electricity": "600900.SH",
    "highway_infrastructure": "600350.SH",
    "port_rail_infrastructure": "601006.SH",
    "gas_water_operators": "600008.SH",
    "telecom_operators": "600050.SH",
    "insurance": "601318.SH",
    "securities_brokerage": "600030.SH",
    "oil_gas_pipeline_integrated": "601857.SH",
    "coal": "601088.SH",
    "steel": "600019.SH",
    "nonferrous_metals": "601600.SH",
    "chemical_materials": "600309.SH",
    "building_materials_cement": "600585.SH",
    "construction_engineering": "601668.SH",
    "environmental_project_operators": "000598.SZ",
    "real_estate": "000002.SZ",
    "consumer_staples_cashflow": "000895.SZ",
    "food_beverage": "600519.SH",
    "home_appliances": "000651.SZ",
    "textile_apparel": "600398.SH",
    "pharma_medical_services": "600276.SH",
    "agriculture_forestry_fishery": "000998.SZ",
    "logistics_express": "002352.SZ",
    "shipping": "601919.SH",
    "retail_commerce": "600827.SH",
    "media_entertainment": "300251.SZ",
    "computer_software": "000938.SZ",
    "electronics_semiconductor": "002371.SZ",
    "auto_and_parts": "600104.SH",
    "machinery_equipment": "600031.SH",
    "power_equipment_new_energy": "600406.SH",
    "military_defense": "600893.SH",
}

CHINESE_NAMES = {
    "bank": "银行", "utilities_electricity": "电力公用", "highway_infrastructure": "高速公路",
    "port_rail_infrastructure": "港口铁路", "gas_water_operators": "燃气水务", "telecom_operators": "电信运营",
    "insurance": "保险", "securities_brokerage": "证券", "oil_gas_pipeline_integrated": "油气",
    "coal": "煤炭", "steel": "钢铁", "nonferrous_metals": "有色金属", "chemical_materials": "基础化工",
    "building_materials_cement": "建材水泥", "construction_engineering": "建筑工程", "environmental_project_operators": "环保运营",
    "real_estate": "房地产", "consumer_staples_cashflow": "消费品", "food_beverage": "食品饮料",
    "home_appliances": "家用电器", "textile_apparel": "纺织服装", "pharma_medical_services": "医药服务",
    "agriculture_forestry_fishery": "农林牧渔", "logistics_express": "物流快递", "shipping": "航运",
    "retail_commerce": "商贸零售", "media_entertainment": "传媒娱乐", "computer_software": "计算机软件",
    "electronics_semiconductor": "电子半导体", "auto_and_parts": "汽车零部件", "machinery_equipment": "机械设备",
    "power_equipment_new_energy": "电力设备新能源", "military_defense": "国防军工",
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = (Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf"))
    for path in paths:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _role_style(role: str) -> tuple[str, str]:
    if role in {"core_candidate", "candidate_after_platform_replication"}:
        return "#2f855a", "核心 / 候选"
    if "excluded" in role or "blocked" in role:
        return "#718096", "排除 / 数据门"
    if "watchlist" in role or "manual" in role or "observation" in role:
        return "#2563eb", "观察 / 研究"
    return "#d17a22", "待研究"


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def _reference_series(daily_zip: zipfile.ZipFile, factor_zip: zipfile.ZipFile, code: str) -> tuple[list[tuple[str, float]], str]:
    daily_name = f"a股日线/{code}.csv"
    factor_name = f"复权因子/{code}.csv"
    try:
        daily_rows = list(csv.reader(io.StringIO(_decode_text(daily_zip.read(daily_name)))))
        factor_rows = list(csv.DictReader(io.StringIO(_decode_text(factor_zip.read(factor_name)))))
    except KeyError:
        return [], "missing_reference_file"

    factors = {row["date"]: float(row["adj_factor"]) for row in factor_rows if row.get("date") and row.get("adj_factor")}
    by_month: dict[str, tuple[str, float]] = {}
    for row in daily_rows[1:]:
        if len(row) < 6:
            continue
        date = row[1]
        if not (START_DATE <= date <= END_DATE) or date not in factors:
            continue
        try:
            adjusted_close = float(row[5]) * factors[date]
        except ValueError:
            continue
        by_month[date[:6]] = (date, adjusted_close)
    points = [by_month[key] for key in sorted(by_month)]
    if not points:
        return [], "no_2013_to_2026_05_data"
    base = points[0][1]
    return [(date, 100.0 * value / base) for date, value in points], "available"


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, size: int, *, bold: bool = False) -> None:
    draw.text(xy, text, fill=fill, font=_font(size, bold))


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    sectors = config["candidate_sectors"]
    with zipfile.ZipFile(DAILY_ZIP) as daily_zip, zipfile.ZipFile(FACTOR_ZIP) as factor_zip:
        rows = []
        for sector in sectors:
            sector_id = sector["sector_id"]
            code = REFERENCE_CODES[sector_id]
            series, availability = _reference_series(daily_zip, factor_zip, code)
            rows.append({"sector": sector, "code": code, "series": series, "availability": availability})

    all_values = [value for row in rows for _, value in row["series"]]
    lower = max(10.0, 10 ** math.floor(math.log10(min(all_values))))
    upper = 10 ** math.ceil(math.log10(max(all_values)))

    image = Image.new("RGB", (3000, 2400), "white")
    draw = ImageDraw.Draw(image)
    navy, grey, light = "#14324a", "#52606d", "#d9e2ec"
    draw.rounded_rectangle((42, 28, 2958, 176), radius=18, fill="#f8fafc", outline="#cbd5e1", width=2)
    _draw_text(draw, (76, 48), "V5 研究覆盖板块：2013-01 至 2026-05 的本地参考证券复权价格轨迹", navy, 39, bold=True)
    _draw_text(draw, (78, 104), "每个小图使用一只长期存在的代表性 A 股；各自首个可用交易日 = 100。仅作市场环境参考，不是行业 ETF、策略收益、总回报或模型表现比较。", grey, 20)

    legend = [("#2f855a", "核心 / 候选"), ("#2563eb", "观察 / 研究"), ("#d17a22", "待研究"), ("#718096", "排除 / 数据门")]
    legend_x = 78
    for color, label in legend:
        draw.rounded_rectangle((legend_x, 205, legend_x + 22, 227), radius=4, fill=color)
        _draw_text(draw, (legend_x + 30, 201), label, grey, 18)
        legend_x += 190
    _draw_text(draw, (940, 201), "纵轴为对数尺度；浅灰虚线为基准 100。所有曲线于 2026-05-31 截断。", grey, 18)

    columns, panel_w, panel_h = 6, 470, 330
    start_x, start_y = 70, 260
    plot_pad_left, plot_pad_right, plot_pad_top, plot_pad_bottom = 42, 24, 72, 56
    years = [2013, 2016, 2019, 2021, 2023, 2026]
    for index, row in enumerate(rows):
        col, grid_row = index % columns, index // columns
        x0, y0 = start_x + col * 490, start_y + grid_row * 350
        x1, y1 = x0 + panel_w, y0 + panel_h
        color, label = _role_style(row["sector"]["basket_role"])
        draw.rounded_rectangle((x0, y0, x1, y1), radius=10, fill="#fcfdff", outline=color, width=3)
        name = CHINESE_NAMES[row["sector"]["sector_id"]]
        _draw_text(draw, (x0 + 18, y0 + 14), name, navy, 23, bold=True)
        _draw_text(draw, (x0 + 18, y0 + 45), f"{row['code']}  |  {label}", color, 15, bold=True)
        px0, py0, px1, py1 = x0 + plot_pad_left, y0 + plot_pad_top, x1 - plot_pad_right, y1 - plot_pad_bottom
        for year in years:
            ratio = (year - 2013) / (2026 - 2013)
            x = px0 + (px1 - px0) * ratio
            draw.line((x, py0, x, py1), fill="#edf2f7", width=1)
        baseline_y = py1 - (math.log10(100) - math.log10(lower)) / (math.log10(upper) - math.log10(lower)) * (py1 - py0)
        draw.line((px0, baseline_y, px1, baseline_y), fill="#cbd5e1", width=2)
        if row["series"]:
            points = []
            for date, value in row["series"]:
                year_float = int(date[:4]) + (int(date[4:6]) - 1) / 12
                x = px0 + (year_float - 2013) / (2026 - 2013) * (px1 - px0)
                y = py1 - (math.log10(value) - math.log10(lower)) / (math.log10(upper) - math.log10(lower)) * (py1 - py0)
                points.append((x, y))
            draw.line(points, fill=color, width=4, joint="curve")
            first_date, final_value = row["series"][0][0], row["series"][-1][1]
            first_year = first_date[:4]
            _draw_text(draw, (x0 + 18, y1 - 38), f"{first_year} 起点=100    截止: {final_value:.0f}", grey, 15)
        else:
            _draw_text(draw, (x0 + 18, y0 + 156), "本地参考证券数据不可用", red := "#c0392b", 18, bold=True)

    footer_y = 2360
    _draw_text(draw, (70, footer_y), "资料来源：本地 A 股日线与复权因子包；板块清单：config/v5a.1_broad_sector_coarse_screening.json。代表证券按研究板块手工选取，不构成投资建议或指数追踪声明。", grey, 17)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)

    with MANIFEST.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sector_id", "display_name", "reference_security", "basket_role", "availability", "first_date", "last_date", "final_normalized_price", "scope_note"])
        writer.writeheader()
        for row in rows:
            series = row["series"]
            writer.writerow({
                "sector_id": row["sector"]["sector_id"],
                "display_name": row["sector"]["display_name"],
                "reference_security": row["code"],
                "basket_role": row["sector"]["basket_role"],
                "availability": row["availability"],
                "first_date": series[0][0] if series else "",
                "last_date": series[-1][0] if series else "",
                "final_normalized_price": f"{series[-1][1]:.6f}" if series else "",
                "scope_note": "Local adjusted-price reference proxy only; not sector ETF, strategy performance, or total-return claim.",
            })


if __name__ == "__main__":
    main()
