from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v5v_application_final_report_readiness" / "current" / "figures" / "v5_finance_theory_statistics_agent_loop.png"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in (Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str, size: int, *, bold: bool = False, spacing: int = 11) -> None:
    draw.multiline_text(xy, text, fill=color, font=_font(size, bold), spacing=spacing)


def _card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str, title: str, body: str, fill: str, *, title_size: int = 27, body_size: int = 19) -> None:
    x0, y0, _, _ = box
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=color, width=3)
    _text(draw, (x0 + 22, y0 + 16), title, color, title_size, bold=True)
    _text(draw, (x0 + 22, y0 + 58), body, "#334e68", body_size)


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, *, width: int = 5) -> None:
    draw.line((*start, *end), fill=color, width=width)
    x, y = end
    if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
        sign = 1 if end[0] >= start[0] else -1
        draw.polygon([(x, y), (x - 17 * sign, y - 10), (x - 17 * sign, y + 10)], fill=color)
    else:
        sign = 1 if end[1] >= start[1] else -1
        draw.polygon([(x, y), (x - 10, y - 17 * sign), (x + 10, y - 17 * sign)], fill=color)


def main() -> None:
    image = Image.new("RGB", (2400, 1250), "white")
    draw = ImageDraw.Draw(image)
    navy, teal, green, orange, red, purple, grey = "#14324a", "#177e89", "#3b7a57", "#d17a22", "#c0392b", "#7b4f9e", "#52606d"

    draw.rounded_rectangle((45, 28, 2355, 145), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (75, 44), "V5 的研究闭环：统计发现结果，金融理论解释结果，agent 把两者变成可证伪流程", navy, 38, bold=True)
    _text(draw, (78, 98), "数学和计算扩大研究能力，但不能单独证明经济机制；理论、数据与执行成本必须共同经受审计。", grey, 20)

    _card(draw, (85, 205, 755, 465), teal, "统计学、计算与 agent 的帮助", "自动化读取数据、构建面板、执行检验、复现实验；\n识别相关性、异常和候选模式，显著提高研究效率。\n但“结果为正”本身不能解释为何会持续有效。", "#f0fdfa", title_size=29, body_size=20)
    _card(draw, (1645, 205, 2315, 465), purple, "作者的金融知识与经验", "阅读金融书籍、文章、行业报告与财报；\n结合既有理财/投资经验理解现金流、风险、\n竞争结构、估值与行为偏差，形成经济解释。", "#fbf7ff", title_size=29, body_size=20)
    _text(draw, (245, 495), "若只从统计结果反推故事，会引入数据挖掘与过拟合风险。", red, 19, bold=True)

    _card(draw, (825, 255, 1575, 505), green, "研究员 agent：从理论到可检验假设", "把书籍/报告/财报信息结构化为金融机制、因子方向、\nPIT 可见性要求与拒绝条件。例如：现金流质量为何应\n影响红利持续性，或动量为何只能在同 sleeve 内辅助。", "#f3faf5", title_size=30, body_size=20)
    _arrow(draw, (770, 335), (810, 335), teal)
    _arrow(draw, (1630, 335), (1590, 335), purple)

    _card(draw, (310, 625, 1020, 860), orange, "量化验证 agent：尝试证伪，而非寻找最好看的结果", "检查 PIT、样本隔离、截面覆盖、IC/RankIC、滚动稳健性、\n共同样本、费用和执行摩擦。输出支持、拒绝或证据不足；\n不得用 2021-2026 正式回测表现反向调参。", "#fff8ed", title_size=29, body_size=20)
    _card(draw, (1380, 625, 2090, 860), navy, "项目经理：解释失败属于哪一类", "综合金融机制、量化证据、数据质量、工程可复现性与治理约束。\n不因为历史收益高就提升状态；必要时将路径退回研究或归档。", "#f2f7fb", title_size=29, body_size=20)
    draw.line((1200, 525, 1200, 560, 665, 560, 665, 610), fill=green, width=5)
    draw.polygon([(665, 610), (655, 593), (675, 593)], fill=green)
    _text(draw, (870, 530), "可证伪假设", grey, 17)
    _arrow(draw, (1040, 745), (1360, 745), orange)
    _text(draw, (1050, 705), "验证包 / 失败归因", grey, 17)

    draw.rounded_rectangle((85, 945, 2315, 1145), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (115, 968), "PM 的四种可审计结论", navy, 27, bold=True)
    _card(draw, (115, 1020, 625, 1125), red, "假设不合理", "金融机制不成立或无法解释；回到研究，不硬做因子。", "#fff5f5", title_size=22, body_size=16)
    _card(draw, (665, 1020, 1175, 1125), orange, "数据不过关", "PIT、覆盖、样本或公司行为证据不足；数据门 blocker。", "#fff8ed", title_size=22, body_size=16)
    _card(draw, (1215, 1020, 1725, 1125), purple, "路径不可行", "理论可能合理，但交易成本、换手或执行摩擦过高；归为 diagnostic。", "#fbf7ff", title_size=22, body_size=16)
    _card(draw, (1765, 1020, 2285, 1125), green, "证据支持", "冻结规则并进入下一工程/观察门；仍不自动成为 accepted。", "#f3faf5", title_size=22, body_size=16)

    _text(draw, (115, 1185), "正确顺序：金融理论提出假设 → 量化检验尝试推翻 → PM 解释并治理结论。不是先挖出收益，再补一个故事。", red, 19, bold=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
