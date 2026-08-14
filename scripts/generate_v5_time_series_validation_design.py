from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v5v_application_final_report_readiness" / "current" / "figures" / "v5_time_series_sample_isolation_design.png"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    options = [
        Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ]
    for option in options:
        if option.exists():
            return ImageFont.truetype(str(option), size)
    return ImageFont.load_default()


def _text(
    draw: ImageDraw.ImageDraw,
    at: tuple[int, int],
    text: str,
    color: str,
    size: int,
    *,
    bold: bool = False,
    spacing: int = 10,
) -> None:
    draw.multiline_text(at, text, font=_font(size, bold), fill=color, spacing=spacing)


def _box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: str,
    title: str,
    body: str,
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=14, fill="#ffffff", outline=color, width=3)
    _text(draw, (x0 + 22, y0 + 16), title, color, 27, bold=True)
    _text(draw, (x0 + 22, y0 + 58), body, "#334e68", 19)


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
    if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
        direction = 1 if end[0] >= start[0] else -1
        draw.polygon([(x, y), (x - 16 * direction, y - 9), (x - 16 * direction, y + 9)], fill=color)
    else:
        direction = 1 if end[1] >= start[1] else -1
        draw.polygon([(x, y), (x - 9, y - 16 * direction), (x + 9, y - 16 * direction)], fill=color)


def main() -> None:
    image = Image.new("RGB", (2400, 1450), "white")
    draw = ImageDraw.Draw(image)
    navy, teal, green, red, orange, grey = "#14324a", "#177e89", "#3b7a57", "#c0392b", "#d17a22", "#52606d"

    draw.rounded_rectangle((45, 28, 2355, 150), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (75, 44), "V5 的真实样本隔离口径：研究边界、已完成证据与未完成验证", navy, 42, bold=True)
    _text(draw, (78, 100), "区分“项目的 2013-2021 研究边界”与“V5 全四 sleeve 已完成的验证”。后者不能被前者自动替代。", grey, 21)

    x_start, x_cut, x_end, y_line = 110, 1430, 2280, 350
    _arrow(draw, (x_start, y_line), (x_end, y_line), navy, width=5)
    for x, label in [(x_start, "2013-01"), (430, "2015"), (760, "2017"), (1090, "2019"), (x_cut, "2021-05"), (1760, "2023"), (2050, "2025"), (x_end, "2026-05")]:
        draw.line((x, y_line - 12, x, y_line + 12), fill="#7b8794", width=2)
        _text(draw, (x - 32, y_line + 26), label, grey, 17)
    draw.line((x_cut, 225, x_cut, 930), fill=red, width=7)
    draw.rounded_rectangle((x_cut - 103, 173, x_cut + 103, 218), radius=12, fill=red)
    _text(draw, (x_cut - 70, 181), "规则冻结", "white", 20, bold=True)

    _text(draw, (110, 236), "项目研究边界：2013-01-01 至 2021-04-30", teal, 29, bold=True)
    _text(draw, (1470, 236), "正式回测期：2021-05-01 至 2026-05-31", navy, 29, bold=True)

    _box(draw, (145, 435, 690, 660), green, "已完成：银行基础滚动证据", "V1-V4 银行多因子基础研究。\n2016-2020 有年度 rolling test 记录，\n用于覆盖度、IC/RankIC、年度刷新与稳健性审计。\n它支持“银行因子研究方法”，不等同完整 V5 组合。")
    _box(draw, (735, 435, 1300, 660), red, "未完成：V5 全四 sleeve exact rolling", "2013-2021 的 exact PIT target reconstruction\n受早期银行监管字段、基础设施现金流/资本开支\n及公司行为原始证据缺口阻塞。\n不得用 proxy target 写成已完成独立验证。")
    _box(draw, (145, 720, 690, 940), orange, "已完成但有限：V5 主候选 proxy 检验", "2019-04-01 至 2020-12-31。\ninternal_subsleeve_mom12_70_30 相对\npre-2021 equal-sleeve baseline proxy：\n增量收益 +0.2799 个百分点；未 accepted。")
    _box(draw, (735, 720, 1300, 940), teal, "适用的滚动协议", "任何未来补齐的 exact PIT 多 sleeve 验证，\n都应在每个 t 时点仅使用当时可见信息：\n先训练/冻结规则，再检验 t+1；\n窗口结果不能拼接为“最优模型”。")

    _box(draw, (1470, 435, 1915, 660), navy, "冻结对象", "唯一正式基线：\nv57f_startup_preload_repaired_baseline\n主候选：internal_subsleeve_mom12_70_30\n规则、窗口与比较合同固定。")
    _box(draw, (1960, 435, 2280, 660), green, "只允许观察", "记录每日净值、共同样本、\n回撤、成本和治理证据。\n不因回测表现重选参数。")
    _box(draw, (1470, 720, 1915, 940), orange, "正式比较", "同父策略、同窗口、同回报合同。\n2021-05-06 至 2026-05-29\n共 1,228 个共同日样本。")
    _box(draw, (1960, 720, 2280, 940), red, "严禁回流", "不得用 2021-2026 的收益\n修改因子、阈值、sleeve、权重\n或选择“最好”的版本。")

    draw.line((2100, 990, 1080, 1140), fill=red, width=6)
    draw.line((1080, 990, 2100, 1140), fill=red, width=6)
    draw.rounded_rectangle((680, 1025, 1740, 1120), radius=14, fill="#fff5f5", outline=red, width=3)
    _text(draw, (725, 1044), "样本外污染禁止：正式回测期的表现不能反向参与模型发现、参数调优、版本选择或“成功叙事”修订。", red, 24, bold=True)

    draw.rounded_rectangle((110, 1190, 2290, 1370), radius=16, fill="#edf2f7", outline="#9fb3c8", width=3)
    _text(draw, (145, 1215), "报告中应使用的真实表述", navy, 29, bold=True)
    _text(draw, (145, 1263), "2013-2021 是 V5 的研究边界；其中银行基础研究有滚动审计证据，V5 主候选只有 2019-2020 的有限 proxy 检验。\n2021-2026 是冻结后的正式历史回测。即使主候选优于 repaired baseline，也仍是 validation_not_independent，不能写成 accepted、live approved 或未来收益承诺。", "#334e68", 22)
    _text(draw, (145, 1330), "关键限制：pre-2021 多 sleeve 的 exact PIT target reconstruction 尚未完成；不得以代理结果伪造“2013-2021 全组合已滚动验证”。", red, 19, bold=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
