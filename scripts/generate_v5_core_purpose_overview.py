from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v5v_application_final_report_readiness" / "current" / "figures" / "v5_core_purpose_overview.png"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in (Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str, size: int, *, bold: bool = False, spacing: int = 12) -> None:
    draw.multiline_text(xy, text, fill=color, font=_font(size, bold), spacing=spacing)


def _card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str, title: str, body: str, fill: str) -> None:
    x0, y0, _, _ = box
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=color, width=3)
    _text(draw, (x0 + 22, y0 + 17), title, color, 27, bold=True)
    _text(draw, (x0 + 22, y0 + 60), body, "#334e68", 19)


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str) -> None:
    draw.line((*start, *end), fill=color, width=6)
    x, y = end
    draw.polygon([(x, y), (x - 18, y - 10), (x - 18, y + 10)], fill=color)


def main() -> None:
    image = Image.new("RGB", (2400, 1000), "white")
    draw = ImageDraw.Draw(image)
    navy, teal, green, orange, purple, grey = "#14324a", "#177e89", "#3b7a57", "#d17a22", "#7b4f9e", "#52606d"

    draw.rounded_rectangle((45, 28, 2355, 140), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (75, 44), "V5 的核心目的：从银行策略开发到个人红利增强 ETF 式组合", navy, 40, bold=True)
    _text(draw, (78, 96), "目标是建立可迁移、可审计的量化策略开发流程，而不是在历史中寻找收益最高的版本。", grey, 21)

    _card(draw, (85, 215, 570, 460), teal, "1. 银行策略开发基础", "V1-V4 的银行多因子价值研究：\n低估、分红可持续、财务/资产质量、低波动。\n沉淀 PIT、统计验证与工程复现。", "#f0fdfa")
    _arrow(draw, (592, 337), (645, 337), teal)
    _card(draw, (670, 215, 1155, 460), navy, "2. 可迁移的开发流程", "把金融假设、知识证据、PIT 数据门、\n量化验证、工程测试和 PM 治理固化为\n可复用的 agent 工作流。", "#f2f7fb")
    _arrow(draw, (1177, 337), (1230, 337), navy)
    _card(draw, (1255, 215, 1740, 460), purple, "3. 多个近似板块的筛选与拒绝", "示例：银行、电力、高速、港口/铁路、煤炭、保险。\n煤炭：周期状态依赖与数据门阻塞，未纳入。\n保险：部分 PIT、截面样本偏小与专属字段不足，未纳入。", "#fbf7ff")
    _arrow(draw, (1762, 337), (1815, 337), purple)
    _card(draw, (1840, 215, 2315, 460), green, "4. 四个核心 sleeve → ETF", "最终纳入：银行、电力、高速、港口/铁路。\n它们通过行业匹配、PIT 可见性、样本覆盖与\n统计/稳健性门，形成个人红利增强 ETF 式组合；\n早期 exact PIT 缺口仍保留披露，未有单独策略 accepted。", "#f3faf5")

    draw.rounded_rectangle((85, 545, 2315, 820), radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    _text(draw, (115, 570), "组合内的信号分工", navy, 29, bold=True)
    _card(draw, (115, 630, 800, 780), green, "价值投资主导", "低估、分红可持续、财务/现金流质量、低波动\n决定股票池与组合骨架。", "#f3faf5")
    _card(draw, (858, 630, 1543, 780), teal, "动量策略辅助", "只在现有 sleeve 内按固定规则倾斜相对权重；\n不替代价值选股，也不扩展股票池。", "#f0fdfa")
    _card(draw, (1601, 630, 2285, 780), orange, "均值回归校正", "观察短期的价值/情绪偏离；\n现阶段保持校正或诊断边界，不独立主导配置。", "#fff8ed")

    draw.rounded_rectangle((85, 865, 2315, 940), radius=14, fill="#fff5f5", outline="#c0392b", width=2)
    _text(draw, (115, 885), "研究纪律：2013-01-01 至 2021-04-30 为研究边界；2021-05-01 至 2026-05-31 为冻结正式回测。回测结果不得反向调参、改权重或选择版本。", "#c0392b", 18, bold=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)


if __name__ == "__main__":
    main()
