from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v5v_application_final_report_readiness" / "current" / "figures" / "v5_ideal_vs_reality_optimization_path.png"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = (
        Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    )
    for path in paths:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    color: str,
    size: int,
    *,
    bold: bool = False,
    spacing: int = 10,
) -> None:
    draw.multiline_text(xy, text, fill=color, font=_font(size, bold), spacing=spacing)


def _card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: str,
    title: str,
    body: str,
    fill: str,
    *,
    title_size: int = 25,
    body_size: int = 18,
) -> None:
    x0, y0, _, _ = box
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=color, width=3)
    _text(draw, (x0 + 20, y0 + 15), title, color, title_size, bold=True)
    _text(draw, (x0 + 20, y0 + 58), body, "#334e68", body_size, spacing=12)


def _arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str,
    *,
    width: int = 5,
) -> None:
    draw.line((*start, *end), fill=color, width=width)
    x, y = end
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if not length:
        return
    ux, uy = dx / length, dy / length
    # Arrow wings are perpendicular to the shaft, so diagonal coordinate axes terminate correctly.
    base_x, base_y = x - ux * 22, y - uy * 22
    wing_x, wing_y = -uy * 10, ux * 10
    draw.polygon([(x, y), (base_x + wing_x, base_y + wing_y), (base_x - wing_x, base_y - wing_y)], fill=color)


def _dashed_path(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], color: str, *, width: int = 5) -> None:
    for start, end in zip(points, points[1:]):
        x0, y0 = start
        x1, y1 = end
        distance = max(abs(x1 - x0), abs(y1 - y0))
        if not distance:
            continue
        step_x, step_y = (x1 - x0) / distance, (y1 - y0) / distance
        for progress in range(0, int(distance), 24):
            stop = min(progress + 14, distance)
            draw.line((x0 + step_x * progress, y0 + step_y * progress, x0 + step_x * stop, y0 + step_y * stop), fill=color, width=width)


def _point(draw: ImageDraw.ImageDraw, xy: tuple[int, int], color: str, label: str, label_xy: tuple[int, int]) -> None:
    x, y = xy
    draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=color, outline="white", width=3)
    _text(draw, label_xy, label, color, 21, bold=True, spacing=12)


def _label_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    color: str,
    *,
    size: int = 20,
) -> None:
    """Keep explanatory labels clear of paths and axes."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=10, fill="#ffffff", outline="#d9e2ec", width=1)
    _text(draw, (x0 + 14, y0 + 10), text, color, size, bold=True, spacing=12)


def _center_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str, size: int, *, bold: bool = False) -> None:
    draw.multiline_text(xy, text, fill=color, font=_font(size, bold), spacing=10, anchor="mm", align="center")


def _perspective_triangle(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    first: tuple[int, int],
    second: tuple[int, int],
    *,
    steps: int,
) -> None:
    """A bounded triangular plane keeps the 3D perspective inside its intended panel."""
    ox, oy = origin
    draw.polygon([origin, first, second], fill="#f8fbfe")
    for i in range(1, steps):
        ratio = i / steps
        on_first = (ox + (first[0] - ox) * ratio, oy + (first[1] - oy) * ratio)
        opposite_first = ((1 - ratio) * second[0] + ratio * first[0], (1 - ratio) * second[1] + ratio * first[1])
        on_second = (ox + (second[0] - ox) * ratio, oy + (second[1] - oy) * ratio)
        opposite_second = ((1 - ratio) * first[0] + ratio * second[0], (1 - ratio) * first[1] + ratio * second[1])
        draw.line((*on_first, *opposite_first), fill="#d4e2ef", width=2)
        draw.line((*on_second, *opposite_second), fill="#dce7f1", width=2)


def main() -> None:
    image = Image.new("RGB", (2600, 1450), "white")
    draw = ImageDraw.Draw(image)
    navy, teal, green, orange, red, purple, grey, blue = "#14324a", "#0f766e", "#3b7a57", "#d17a22", "#c0392b", "#7c3aed", "#52606d", "#2563eb"
    path_grey, return_magenta = "#475569", "#b4539b"

    draw.rounded_rectangle((45, 28, 2555, 155), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (75, 44), "V5 的理想与现实：从三维优化设想，到受约束的局部可行路径", navy, 39, bold=True)
    _text(draw, (78, 100), "理想目标是以工作流寻找从金融假设到理想模型的最短可审计路径；实际研究必须承认假设、数据、能力与行业相似度的边界。", grey, 20)

    draw.rounded_rectangle((65, 190, 1670, 1225), radius=16, fill="#fbfdff", outline="#cbd5e1", width=2)
    _text(draw, (95, 218), "理想的三维研究空间", navy, 30, bold=True)
    _text(draw, (95, 264), "三个坐标轴不是收益本身，而是同时决定模型能否成立的约束：金融解释、统计证据、工程 / 执行可行性。", grey, 18)

    origin = (320, 1000)
    x_axis, y_axis, z_axis = (1400, 1000), (830, 430), (110, 690)
    # Three bounded coordinate planes read as a conceptual 3D volume without spilling into labels.
    _perspective_triangle(draw, origin, x_axis, y_axis, steps=5)
    _perspective_triangle(draw, origin, x_axis, z_axis, steps=5)
    _arrow(draw, origin, x_axis, blue, width=5)
    _arrow(draw, origin, y_axis, purple, width=5)
    _arrow(draw, origin, z_axis, orange, width=5)
    _text(draw, (1190, 1025), "X 统计证据", blue, 23, bold=True)
    _text(draw, (800, 335), "Y 金融解释", purple, 23, bold=True)
    _text(draw, (72, 596), "Z 工程 / 执行\n可行性", orange, 22, bold=True, spacing=12)
    _point(draw, origin, navy, "H0：金融假设的出发点", (350, 1025))

    ideal = (1240, 450)
    _point(draw, ideal, green, "M*：三项同时满足的\n概念目标", (1270, 380))
    _dashed_path(draw, [origin, (515, 845), (700, 705), (930, 560), ideal], path_grey, width=6)
    _label_box(draw, (890, 505, 1195, 600), "理想路径：逐次校正，\n同时满足三类约束", path_grey)

    actual_path = [origin, (500, 900), (720, 845), (1040, 860)]
    for start, end in zip(actual_path, actual_path[1:]):
        _arrow(draw, start, end, grey, width=7)
    failure = (1040, 860)
    _point(draw, failure, red, "", (1070, 885))
    draw.line((failure[0] - 32, failure[1] + 40, failure[0] + 42, failure[1] - 72), fill=red, width=6)
    draw.line((failure[0] + 42, failure[1] + 40, failure[0] - 32, failure[1] - 72), fill=red, width=6)
    _label_box(draw, (1060, 875, 1375, 970), "跨行业复制步子过大\n复制失真 / 数据门暴露", red)

    feasible = (735, 665)
    draw.ellipse((feasible[0] - 150, feasible[1] - 80, feasible[0] + 150, feasible[1] + 80), outline=blue, width=4)
    _point(draw, feasible, navy, "", (485, 565))
    _label_box(draw, (455, 515, 700, 625), "P：局部可行的\n部分近似复刻", navy)
    _arrow(draw, (1010, 838), feasible, return_magenta, width=6)
    _label_box(draw, (430, 745, 740, 845), "现实路径：退回、缩小、\n在证据边界内重新验证", grey)

    _card(draw, (95, 1080, 1635, 1182), red, "重要边界", "“近似行业”只是研究起点，不是成立的结论。即使商业标签相近，现金流机制、周期敏感度、监管、样本结构与执行摩擦也可能不同。", "#fff5f5", title_size=23, body_size=18)

    draw.rounded_rectangle((1715, 190, 2535, 1225), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (1745, 218), "现实中的三重约束（概念）", navy, 30, bold=True)
    _text(draw, (1745, 260), "上方是治理逻辑；下方只列 V5 已真实发生的对应案例。", grey, 17)

    triangle_top, triangle_left, triangle_right = (2125, 330), (1825, 625), (2425, 625)
    draw.line((*triangle_top, *triangle_left), fill=purple, width=5)
    draw.line((*triangle_left, *triangle_right), fill=blue, width=5)
    draw.line((*triangle_right, *triangle_top), fill=orange, width=5)
    for point, color in ((triangle_top, purple), (triangle_left, blue), (triangle_right, orange)):
        draw.ellipse((point[0] - 11, point[1] - 11, point[0] + 11, point[1] + 11), fill=color, outline="white", width=2)
    _center_text(draw, (2125, 302), "金融解释", purple, 20, bold=True)
    _center_text(draw, (1810, 662), "统计证据", blue, 20, bold=True)
    _center_text(draw, (2440, 662), "工程实现", orange, 20, bold=True)
    draw.rounded_rectangle((1983, 433, 2267, 548), radius=12, fill="#ffffff", outline="#cbd5e1", width=2)
    _center_text(draw, (2125, 487), "三项同时满足\n只是概念门槛\nV5 尚未证明", red, 19, bold=True)

    _card(draw, (1745, 705, 2505, 830), purple, "V5 例：短窗均值回归，统计证据不足", "回测期内部诊断出现正向观察，但缺少独立 pre-2021 验证；因此只保留为 diagnostic，不升级。", "#fbf7ff", title_size=21, body_size=17)
    _card(draw, (1745, 855, 2505, 980), orange, "V5 例：动量现金中性执行，工程关闭", "81 个 sleeve-period 中有 43 个不能严格自融资；未完成现金闭环的执行路径被关闭。", "#fff8ed", title_size=21, body_size=17)
    _card(draw, (1745, 1005, 2505, 1150), blue, "V5 没有形成“统计 + 工程、缺金融解释”的候选", "V5i 技术卖出线甚至在保守统计上为负，已关闭；该格表示流程防止的风险，不是已成功模型。", "#f4f8ff", title_size=19, body_size=16)

    _text(draw, (95, 1310), "研究成熟度不在于宣称抵达 M*，而在于能清楚说明：离它还有多远、为什么停下、下一步需要什么证据。", red, 22, bold=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
