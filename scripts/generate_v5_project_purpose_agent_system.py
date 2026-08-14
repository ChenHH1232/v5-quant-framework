from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v5v_application_final_report_readiness" / "current" / "figures" / "v5_project_purpose_and_agent_system.png"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, position: tuple[int, int], value: str, color: str, size: int, *, bold: bool = False, spacing: int = 11) -> None:
    draw.multiline_text(position, value, font=_font(size, bold), fill=color, spacing=spacing)


def _card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: str,
    title: str,
    body: str,
    *,
    fill: str = "#ffffff",
    title_size: int = 28,
    body_size: int = 20,
) -> None:
    x0, y0, _, _ = box
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=color, width=3)
    _text(draw, (x0 + 22, y0 + 16), title, color, title_size, bold=True)
    _text(draw, (x0 + 22, y0 + 58), body, "#334e68", body_size)


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, *, width: int = 5) -> None:
    draw.line((*start, *end), fill=color, width=width)
    x, y = end
    if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
        direction = 1 if end[0] >= start[0] else -1
        draw.polygon([(x, y), (x - 16 * direction, y - 9), (x - 16 * direction, y + 9)], fill=color)
    else:
        direction = 1 if end[1] >= start[1] else -1
        draw.polygon([(x, y), (x - 9, y - 16 * direction), (x + 9, y - 16 * direction)], fill=color)


def _dashed_line(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, *, width: int = 3, dash: int = 12, gap: int = 8) -> None:
    x0, y0 = start
    x1, y1 = end
    distance = max(abs(x1 - x0), abs(y1 - y0))
    if distance == 0:
        return
    step_x, step_y = (x1 - x0) / distance, (y1 - y0) / distance
    progress = 0
    while progress < distance:
        segment_end = min(progress + dash, distance)
        draw.line((x0 + step_x * progress, y0 + step_y * progress, x0 + step_x * segment_end, y0 + step_y * segment_end), fill=color, width=width)
        progress += dash + gap


def main() -> None:
    image = Image.new("RGB", (2600, 1700), "white")
    draw = ImageDraw.Draw(image)
    navy, teal, green, orange, red, purple, grey = "#14324a", "#177e89", "#3b7a57", "#d17a22", "#c0392b", "#7b4f9e", "#52606d"

    draw.rounded_rectangle((45, 28, 2555, 152), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (78, 44), "V5 的核心目的：从银行策略开发，建立可迁移的量化策略 agent 工作流程", navy, 42, bold=True)
    _text(draw, (80, 102), "以价值投资为主导，在近似高股息板块重复可审计开发，最终组成个人的红利增强 ETF 式组合。", grey, 22)

    _card(draw, (90, 205, 610, 435), teal, "1. V1-V4：银行策略开发基础", "低估、分红可持续、财务质量、资产质量与低波动。\n从银行研究中沉淀 PIT、统计验证、工程复现\n和治理门，而非只沉淀一条收益曲线。", fill="#f0fdfa", title_size=27, body_size=20)
    _arrow(draw, (630, 320), (675, 320), teal, width=6)
    _card(draw, (700, 205, 1220, 435), navy, "2. 提炼可迁移的开发工作流", "将金融假设、知识证据、PIT 数据门、\n量化验证、工程测试与 PM 决策固化为\n可复用的 agent 协作流程。", fill="#f2f7fb", title_size=27, body_size=20)
    _arrow(draw, (1240, 320), (1285, 320), navy, width=6)
    _card(draw, (1310, 205, 1830, 435), purple, "3. 在近似板块自动化开发", "固定约束下扩展到银行、电力公用事业、\n高速基础设施、港口/铁路等高股息相近板块。\n不是全市场选股，也不随结果临时加行业。", fill="#fbf7ff", title_size=27, body_size=20)
    _arrow(draw, (1850, 320), (1895, 320), purple, width=6)
    _card(draw, (1920, 205, 2510, 435), green, "4. 形成个人红利增强 ETF 式组合", "价值低波负责选股与组合骨架；\n动量只在同 sleeve 内辅助权重；\n均值回归用于识别价值与情绪偏离，保持校正/诊断边界。", fill="#f3faf5", title_size=27, body_size=20)

    draw.rounded_rectangle((90, 490, 2510, 1195), radius=16, fill="#fbfdff", outline="#cbd5e1", width=2)
    _text(draw, (120, 515), "人机协作、交接与监督", navy, 31, bold=True)

    _card(draw, (935, 560, 1665, 680), purple, "持续对话的顾问", "保持项目上下文，解释取舍，提出可审计的备选假设；不绕过 PM，不改变冻结规则。", fill="#fbf7ff", title_size=28, body_size=19)
    _card(draw, (935, 735, 1665, 885), navy, "项目经理（PM）：治理与最终裁决", "定义研究边界与优先级，分派与汇总 agent，冻结模型状态和比较合同；\n历史收益不能直接换取 accepted，PM 对不充分证据保留否决权。", fill="#f2f7fb", title_size=31, body_size=20)
    _arrow(draw, (1300, 685), (1300, 725), purple, width=5)

    # Dashed governance bus is deliberately separate from the operational hand-off chain below.
    _dashed_line(draw, (1300, 900), (1300, 940), navy)
    _dashed_line(draw, (390, 940), (2210, 940), navy)
    for x in (390, 1000, 1610, 2210):
        _dashed_line(draw, (x, 940), (x, 970), navy)
    _text(draw, (1120, 908), "PM 统一治理：范围、证据标准、状态与升级门", navy, 18, bold=True)

    _card(draw, (110, 980, 670, 1180), green, "研究员 agent", "阅读书籍、行业报告与财报原页；\n提出金融假设、机制与拒绝条件；\n沉淀知识卡，不以叙事替代统计。", fill="#f3faf5", title_size=28, body_size=20)
    _card(draw, (720, 980, 1280, 1180), orange, "量化验证 agent", "执行 PIT、样本隔离、IC/RankIC、滚动、\n共同样本与稳健性检查；\n将结果归为支持、拒绝或不充分。", fill="#fff8ed", title_size=28, body_size=20)
    _card(draw, (1330, 980, 1890, 1180), teal, "工程师 agent", "把固定 spec 变成可运行实现；\n维护数据门、测试、哈希、复现与执行摩擦；\n不得为通过测试修改结论。", fill="#f0fdfa", title_size=28, body_size=20)
    _card(draw, (1940, 980, 2500, 1180), red, "治理与证据归档", "登记 candidate / diagnostic / blocked；\n保存报告、失败原因、订单与现金证据；\n不以代理或收益掩盖 blocker。", fill="#fff5f5", title_size=28, body_size=20)

    _arrow(draw, (685, 1080), (705, 1080), green, width=5)
    _arrow(draw, (1295, 1080), (1315, 1080), orange, width=5)
    _arrow(draw, (1905, 1080), (1925, 1080), teal, width=5)
    _text(draw, (535, 1040), "假设 / 知识", grey, 16)
    _text(draw, (1145, 1040), "冻结 spec", grey, 16)
    _text(draw, (1748, 1040), "测试 / 证据", grey, 16)

    draw.rounded_rectangle((90, 1235, 2510, 1415), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (120, 1260), "组合中的信号分工：价值主导，动量辅助，均值回归校正偏离", navy, 29, bold=True)
    _card(draw, (120, 1310, 850, 1390), green, "价值投资主导", "以低估、分红可持续、财务/现金流质量和低波动定义股票池与组合骨架。", fill="#f3faf5", title_size=23, body_size=17)
    _card(draw, (935, 1310, 1665, 1390), teal, "动量策略辅助", "只在既有 sleeve 内进行固定规则的相对权重倾斜，不替代价值选股。", fill="#f0fdfa", title_size=23, body_size=17)
    _card(draw, (1750, 1310, 2480, 1390), orange, "均值回归校正", "用于观察短期价值/情绪偏离；现阶段保持诊断或校正模块，不独立主导配置。", fill="#fff8ed", title_size=23, body_size=17)

    draw.rounded_rectangle((90, 1460, 2510, 1615), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (120, 1483), "共同底座：知识、数据、工具与自建 skills", navy, 27, bold=True)
    _card(draw, (120, 1530, 670, 1590), purple, "知识库", "书籍、行业报告、财报原页、研究卡与证据索引。", fill="#fbf7ff", title_size=21, body_size=15)
    _card(draw, (715, 1530, 1265, 1590), green, "PIT 数据库", "价格/成交量、财务字段、分红、公司行为、股票池与可见日。", fill="#f3faf5", title_size=21, body_size=15)
    _card(draw, (1310, 1530, 1860, 1590), orange, "外接工具与平台", "BaoStock、Tushare；JoinQuant/QMT 仅在授权与合同边界内使用。", fill="#fff8ed", title_size=21, body_size=15)
    _card(draw, (1905, 1530, 2480, 1590), teal, "自建 skills", "控制器、研究、量化验证、工程、滚动验证与 PIT 泄漏审计组件。", fill="#f0fdfa", title_size=21, body_size=15)

    _text(draw, (120, 1640), "样本纪律：2013-01-01 至 2021-04-30 为研究边界；2021-05-01 至 2026-05-31 为冻结正式回测。回测结果不得反向调参、改权重或选择版本。", red, 20, bold=True)

    # Repaint compact cards after the overview layer to keep every caption inside its border.
    _card(draw, (120, 1300, 850, 1405), green, "价值投资主导", "以低估、分红可持续、财务/现金流质量和低波动定义股票池与组合骨架。", fill="#f3faf5", title_size=23, body_size=16)
    _card(draw, (935, 1300, 1665, 1405), teal, "动量策略辅助", "只在既有 sleeve 内进行固定规则的相对权重倾斜，不替代价值选股。", fill="#f0fdfa", title_size=23, body_size=16)
    _card(draw, (1750, 1300, 2480, 1405), orange, "均值回归校正", "用于观察短期价值/情绪偏离；现阶段保持诊断或校正模块，不独立主导配置。", fill="#fff8ed", title_size=23, body_size=16)
    _card(draw, (120, 1520, 670, 1615), purple, "知识库", "书籍、行业报告、财报原页、研究卡与证据索引。", fill="#fbf7ff", title_size=21, body_size=14)
    _card(draw, (715, 1520, 1265, 1615), green, "PIT 数据库", "价格/成交量、财务字段、分红、公司行为、股票池与可见日。", fill="#f3faf5", title_size=21, body_size=14)
    _card(draw, (1310, 1520, 1860, 1615), orange, "外接工具与平台", "BaoStock/Tushare；JoinQuant/QMT 仅在授权与合同边界内使用。", fill="#fff8ed", title_size=21, body_size=14)
    _card(draw, (1905, 1520, 2480, 1615), teal, "自建 skills", "控制、研究、量化、工程、滚动与 PIT 审计的可复用组件。", fill="#f0fdfa", title_size=21, body_size=14)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
