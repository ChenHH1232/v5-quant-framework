from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v5v_application_final_report_readiness" / "current" / "figures" / "v5_agent_workflow_overview.png"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in (Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str, size: int, *, bold: bool = False, spacing: int = 12) -> None:
    draw.multiline_text(xy, text, fill=color, font=_font(size, bold), spacing=spacing)


def _card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str, title: str, body: str, fill: str, *, title_size: int = 27, body_size: int = 19) -> None:
    x0, y0, _, _ = box
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=color, width=3)
    _text(draw, (x0 + 22, y0 + 16), title, color, title_size, bold=True)
    _text(draw, (x0 + 22, y0 + 57), body, "#334e68", body_size)


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, *, width: int = 5) -> None:
    draw.line((*start, *end), fill=color, width=width)
    x, y = end
    if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
        sign = 1 if end[0] >= start[0] else -1
        draw.polygon([(x, y), (x - 16 * sign, y - 9), (x - 16 * sign, y + 9)], fill=color)
    else:
        sign = 1 if end[1] >= start[1] else -1
        draw.polygon([(x, y), (x - 9, y - 16 * sign), (x + 9, y - 16 * sign)], fill=color)


def _dashed(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str) -> None:
    x0, y0 = start
    x1, y1 = end
    distance = max(abs(x1 - x0), abs(y1 - y0))
    if not distance:
        return
    step_x, step_y = (x1 - x0) / distance, (y1 - y0) / distance
    for distance_start in range(0, int(distance), 20):
        distance_end = min(distance_start + 12, distance)
        draw.line((x0 + step_x * distance_start, y0 + step_y * distance_start, x0 + step_x * distance_end, y0 + step_y * distance_end), fill=color, width=3)


def main() -> None:
    image = Image.new("RGB", (2400, 1150), "white")
    draw = ImageDraw.Draw(image)
    navy, teal, green, orange, red, purple, grey = "#14324a", "#177e89", "#3b7a57", "#d17a22", "#c0392b", "#7b4f9e", "#52606d"

    draw.rounded_rectangle((45, 28, 2355, 140), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (75, 44), "V5 的 agent 工作流程：交接清晰，PM 治理独立", navy, 40, bold=True)
    _text(draw, (78, 96), "研究、量化、工程各自独立产出；项目经理统一冻结边界、证据标准、模型状态和升级门。", grey, 21)

    _card(draw, (770, 185, 1630, 300), purple, "持续对话的顾问", "维护项目上下文、解释取舍、提出可审计的备选假设；不绕过 PM，也不修改冻结规则。", "#fbf7ff", title_size=28, body_size=18)
    _card(draw, (770, 360, 1630, 510), navy, "项目经理（PM）：治理与最终裁决", "定义范围、优先级和比较合同；汇总冲突；冻结窗口、状态与证据标准。\n历史收益不能直接换取 accepted，PM 可以否决不充分证据。", "#f2f7fb", title_size=31, body_size=19)
    _arrow(draw, (1200, 307), (1200, 348), purple)

    _dashed(draw, (1200, 530), (1200, 570), navy)
    _dashed(draw, (285, 570), (2115, 570), navy)
    for x in (285, 895, 1505, 2115):
        _dashed(draw, (x, 570), (x, 600), navy)
    _text(draw, (998, 535), "PM 统一治理：范围、证据标准、状态与升级门", navy, 17, bold=True)

    _card(draw, (60, 615, 510, 830), green, "研究员 agent", "书籍、行业报告、财报原页。\n提出金融假设、机制与拒绝条件；\n不以叙事替代统计。", "#f3faf5")
    _card(draw, (670, 615, 1120, 830), orange, "量化验证 agent", "PIT、样本隔离、IC/RankIC、滚动、\n共同样本、稳健性与失败归因。\n输出支持、拒绝或不充分。", "#fff8ed")
    _card(draw, (1280, 615, 1730, 830), teal, "工程师 agent", "固定 spec 的实现、数据门、测试、\n哈希、复现与执行摩擦。\n不得为了通过测试修改结论。", "#f0fdfa")
    _card(draw, (1890, 615, 2340, 830), red, "治理与证据归档", "candidate / diagnostic / blocked。\n保存报告、失败原因、平台/现金证据；\n不以代理或收益掩盖 blocker。", "#fff5f5")
    _arrow(draw, (525, 722), (655, 722), green)
    _arrow(draw, (1135, 722), (1265, 722), orange)
    _arrow(draw, (1745, 722), (1875, 722), teal)
    _text(draw, (530, 680), "假设 / 知识", grey, 16)
    _text(draw, (1140, 680), "冻结 spec", grey, 16)
    _text(draw, (1750, 680), "测试 / 证据", grey, 16)

    draw.rounded_rectangle((60, 900, 2340, 1055), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (90, 922), "共同底座：可追溯输入与可复用工具", navy, 25, bold=True)
    _card(draw, (90, 970, 620, 1050), purple, "知识库", "书籍、行业报告、财报原页、研究卡与证据索引。", "#fbf7ff", title_size=20, body_size=14)
    _card(draw, (660, 970, 1190, 1050), green, "PIT 数据库", "价格/成交量、财务、分红、公司行为、股票池与可见日。", "#f3faf5", title_size=20, body_size=14)
    _card(draw, (1230, 970, 1760, 1050), orange, "外接工具与平台", "BaoStock/Tushare；JoinQuant/QMT 仅在授权边界内使用。", "#fff8ed", title_size=20, body_size=14)
    _card(draw, (1800, 970, 2310, 1050), teal, "自建 skills", "控制、研究、量化、工程、滚动验证与 PIT 审计组件。", "#f0fdfa", title_size=20, body_size=14)

    _text(draw, (90, 1090), "所有角色均受相同样本纪律与治理约束：研究、验证、工程和决策都留下可复核证据。", "#c0392b", 18, bold=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
