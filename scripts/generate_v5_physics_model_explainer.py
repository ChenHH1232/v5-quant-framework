from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "v5f_structural_rough_screen" / "current" / "v5f_structural_rough_screen_daily_returns.csv"
SLEEVES = ROOT / "v5_startup_warmup_price_repair" / "current" / "runs" / "v57f_warmup_repaired_sleeve_attribution" / "v57f_core_sleeve_daily_returns.csv"
OUTPUT = ROOT / "v5v_application_final_report_readiness" / "current" / "figures" / "v5_physics_model_explainer.png"
BASELINE = "v57f_startup_preload_repaired_baseline"
CANDIDATE = "internal_subsleeve_mom12_70_30"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, at: tuple[int, int], text: str, color: str, size: int, *, bold: bool = False, spacing: int = 10) -> None:
    draw.multiline_text(at, text, font=_font(size, bold), fill=color, spacing=spacing)


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _nav(returns: list[float]) -> list[float]:
    value = 1.0
    result = []
    for ret in returns:
        value *= 1 + ret
        result.append(value)
    return result


def _number(value: str | None) -> float:
    try:
        return float(value or 0.0)
    except ValueError:
        return 0.0


def _draw_plot(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    series: list[tuple[str, list[float], str]],
    dates: list[str],
    *,
    area_between: tuple[list[float], list[float], str] | None = None,
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=12, fill="#ffffff", outline="#cbd5e1", width=2)
    left, top, right, bottom = x0 + 58, y0 + 24, x1 - 24, y1 - 44
    values = [value for _, points, _ in series for value in points]
    if area_between:
        values.extend(area_between[0]); values.extend(area_between[1])
    lower, upper = min(values), max(values)
    margin = max((upper - lower) * 0.10, 0.02)
    lower -= margin; upper += margin
    for part in range(5):
        y = top + (bottom - top) * part / 4
        value = upper - (upper - lower) * part / 4
        draw.line((left, y, right, y), fill="#e8eef5", width=1)
        _text(draw, (x0 + 8, int(y - 10)), f"{value:.2f}", "#7b8794", 15)
    if area_between:
        first, second, color = area_between
        top_points = [_point(index, value, len(first), left, top, right, bottom, lower, upper) for index, value in enumerate(first)]
        bottom_points = [_point(index, value, len(second), left, top, right, bottom, lower, upper) for index, value in reversed(list(enumerate(second)))]
        overlay = Image.new("RGBA", (2400, 1700), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.polygon(top_points + bottom_points, fill=color)
        draw._image.alpha_composite(overlay)  # Pillow's drawing context retains the canvas image.
    for _, points, color in series:
        coordinates = [_point(index, value, len(points), left, top, right, bottom, lower, upper) for index, value in enumerate(points)]
        draw.line(coordinates, fill=color, width=4, joint="curve")
    for year in ("2021", "2022", "2023", "2024", "2025", "2026"):
        indices = [index for index, date in enumerate(dates) if date.startswith(year)]
        if not indices:
            continue
        x = left + (right - left) * indices[0] / max(len(dates) - 1, 1)
        draw.line((x, bottom, x, bottom + 6), fill="#7b8794", width=1)
        _text(draw, (int(x - 16), bottom + 10), year, "#52606d", 15)


def _point(index: int, value: float, count: int, left: int, top: int, right: int, bottom: int, lower: float, upper: float) -> tuple[int, int]:
    x = left + (right - left) * index / max(count - 1, 1)
    y = bottom - (bottom - top) * (value - lower) / max(upper - lower, 1e-12)
    return round(x), round(y)


def _card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str, title: str, body: str) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=12, fill="#ffffff", outline=color, width=3)
    _text(draw, (x0 + 20, y0 + 14), title, color, 26, bold=True)
    _text(draw, (x0 + 20, y0 + 53), body, "#334e68", 18)


def _physics_inset(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=12, fill="#ffffff", outline="#c0392b", width=3)
    _text(draw, (x0 + 18, y0 + 12), "物理解释：概念映射，不是另一条回测曲线", "#c0392b", 21, bold=True)
    left, top, right, bottom = x0 + 35, y0 + 55, x0 + 365, y1 - 38
    # A small potential landscape: it defines vocabulary only; the real paths remain in the charts.
    curve = []
    for offset in range(0, right - left + 1, 5):
        x = left + offset
        y = top + 78 + int(26 * __import__("math").sin(offset / 55) + 14 * __import__("math").sin(offset / 23))
        curve.append((x, y))
    draw.line(curve, fill="#3b7a57", width=4, joint="curve")
    ball_x, ball_y = curve[len(curve) * 3 // 5]
    draw.ellipse((ball_x - 13, ball_y - 13, ball_x + 13, ball_y + 13), fill="#64748b", outline="#1f2937", width=2)
    draw.line((ball_x - 42, ball_y + 42, ball_x - 42, ball_y + 5), fill="#3b7a57", width=4)
    draw.polygon([(ball_x - 42, ball_y - 4), (ball_x - 50, ball_y + 10), (ball_x - 34, ball_y + 10)], fill="#3b7a57")
    draw.line((ball_x + 10, ball_y - 6, ball_x + 62, ball_y - 26), fill="#d9363e", width=4)
    draw.polygon([(ball_x + 70, ball_y - 30), (ball_x + 57, ball_y - 34), (ball_x + 62, ball_y - 19)], fill="#d9363e")
    draw.arc((ball_x + 34, ball_y - 58, ball_x + 100, ball_y + 6), start=210, end=320, fill="#eb7a13", width=4)
    draw.line((ball_x + 112, ball_y - 76, ball_x + 112, ball_y - 28), fill="#6f42c1", width=3)
    draw.polygon([(ball_x + 112, ball_y - 18), (ball_x + 104, ball_y - 33), (ball_x + 120, ball_y - 33)], fill="#6f42c1")
    _text(draw, (x0 + 395, y0 + 58), "F_s  基本面/低波 -> sleeve 势能面", "#3b7a57", 15, bold=True)
    _text(draw, (x0 + 395, y0 + 88), "v  同 sleeve 12-1 -> 相对权重倾斜", "#d9363e", 15, bold=True)
    _text(draw, (x0 + 395, y0 + 118), "a  加速/减速 -> 仅作趋势诊断", "#d17a22", 15, bold=True)
    _text(draw, (x0 + 395, y0 + 148), "ε  冲击与摩擦 -> 风险审计", "#6f42c1", 15, bold=True)


def main() -> None:
    portfolio_rows = _csv(PORTFOLIO)
    dates = [row["trade_date"] for row in portfolio_rows if row["version_id"] == BASELINE]
    baseline_returns = [_number(row["strategy_return"]) for row in portfolio_rows if row["version_id"] == BASELINE]
    candidate_returns = [_number(row["strategy_return"]) for row in portfolio_rows if row["version_id"] == CANDIDATE]
    baseline_nav, candidate_nav = _nav(baseline_returns), _nav(candidate_returns)
    if not (len(dates) == len(baseline_nav) == len(candidate_nav)):
        raise ValueError("Portfolio series do not share a common V5 formal sample.")

    sleeve_rows = _csv(SLEEVES)
    sleeve_dates = [row["trade_date"] for row in sleeve_rows]
    sleeve_specs = [
        ("银行 sleeve | BANK", "bank_local_return", "#177e89", "价值、资本质量、分红可持续性"),
        ("电力公用 sleeve | POWER", "utilities_electricity_local_return", "#3b7a57", "现金流、监管回报、低波"),
        ("高速基建 sleeve | HIGHWAY", "highway_infrastructure_local_return", "#d17a22", "OCF 质量、资本开支约束、分红"),
        ("港口铁路 sleeve | PORT & RAIL", "port_rail_infrastructure_local_return", "#2f6690", "经营纯度、现金流、防御性"),
    ]
    sleeve_navs = [(name, _nav([_number(row.get(column)) for row in sleeve_rows]), color, detail) for name, column, color, detail in sleeve_specs]

    image = Image.new("RGBA", (2400, 1700), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((45, 28, 2355, 152), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (75, 43), "V5 模型的物理学解释：用正式回测期的真实轨迹，而非示意波形", "#14324a", 42, bold=True)
    _text(draw, (78, 98), "正式共同样本：2021-05-06 至 2026-05-29，1,228 日。四个 sleeve 的轨迹来自 repaired baseline；顶部展示主候选对整体的实际影响。", "#52606d", 20)

    _text(draw, (75, 188), "组合层：四条受约束轨道叠加后的真实净值与动量权重治理影响", "#14324a", 29, bold=True)
    _draw_plot(draw, (55, 235, 1655, 650), [("repaired baseline", baseline_nav, "#14324a"), ("primary candidate", candidate_nav, "#177e89")], dates, area_between=(candidate_nav, baseline_nav, "#7fd1c844"))
    draw.line((108, 278, 148, 278), fill="#14324a", width=5); _text(draw, (158, 264), "repaired baseline", "#14324a", 19)
    draw.line((380, 278, 420, 278), fill="#177e89", width=5); _text(draw, (430, 264), "internal_subsleeve_mom12_70_30", "#177e89", 19)
    _card(draw, (1705, 235, 2345, 410), "#177e89", "整体影响趋势（真实序列）", f"最终净值：{candidate_nav[-1]:.3f} vs {baseline_nav[-1]:.3f}\n正式总收益：120.69% vs 109.25%\n相对收益差：+11.43 pct points\n绿色区间 = 主候选相对基线的累计影响")
    _physics_inset(draw, (1705, 435, 2345, 650))

    _text(draw, (75, 705), "sleeve 层：四条实际累计收益轨迹（每条轨道的地形不同）", "#14324a", 29, bold=True)
    positions = [(55, 755, 1160, 1030), (1240, 755, 2345, 1030), (55, 1080, 1160, 1355), (1240, 1080, 2345, 1355)]
    for (name, nav, color, detail), box in zip(sleeve_navs, positions):
        x0, y0, x1, y1 = box
        _draw_plot(draw, box, [(name, nav, color)], sleeve_dates)
        final_return = (nav[-1] - 1) * 100
        _text(draw, (x0 + 20, y0 + 13), name, color, 24, bold=True)
        _text(draw, (x0 + 20, y0 + 45), f"F_s 的可观测输入：{detail} | 期末累计收益 {final_return:.1f}%", "#52606d", 16)

    _card(draw, (55, 1410, 770, 1575), "#3b7a57", "价值低波：选择轨道与候选池", "PIT 可见的价值、质量、现金流、分红可持续性与低波因子，\n决定四个 sleeve 的候选池、约束和长期暴露；V57f core 不被 V5 改写。")
    _card(draw, (840, 1410, 1555, 1575), "#d9363e", "动量：只改变轨道内的相对权重", "固定规则：70% 原 V57f 权重 + 30% 同 sleeve mom12 top-tercile 子组合，\n再归一化回原 sleeve 总权重。它解释绿色总体影响区间，不改变 sleeve 边界。")
    _card(draw, (1625, 1410, 2345, 1575), "#7b8794", "均值回归与治理：不把假说当结论", "均值回归是短时局部回复的诊断线，证据不足以进入主线。\nPIT、样本隔离、成本、现金和订单链是升级门槛；当前仍 not accepted。")

    draw.rounded_rectangle((55, 1605, 2345, 1660), radius=10, fill="#edf2f7", outline="#9fb3c8", width=2)
    _text(draw, (78, 1619), "研究边界：2013-01-01 至 2021-04-30 用于研究/验证；2021-05-01 至 2026-05-31 为正式回测。历史观察不等于独立验证、accepted 或 live approved。", "#b23a48", 18, bold=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
