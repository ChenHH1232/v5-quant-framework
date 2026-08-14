from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v5w_final_report_preparation" / "current"
FIGURES = OUTPUT / "figures"
CANONICAL_DAILY = ROOT / "v5f_structural_rough_screen" / "current" / "v5f_structural_rough_screen_daily_returns.csv"
PERFORMANCE = ROOT / "v5r_overall_research_governance_report_draft" / "current" / "v5r_performance_comparison_table.csv"
SECTORS = ROOT / "sector_replication_batches_v59" / "current" / "screening" / "sector_screening_results.csv"
FIGURE_REGISTER = ROOT / "v5v_application_final_report_readiness" / "current" / "v5v_figure_register.csv"
START, END = "20210506", "20260529"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fill: str, size: int, bold: bool = False) -> None:
    draw.text(xy, value, fill=fill, font=font(size, bold))


def day_ordinal(day: str) -> int:
    return date(int(day[:4]), int(day[4:6]), int(day[6:8])).toordinal()


def canonical_nav(version_id: str) -> dict[str, float]:
    with CANONICAL_DAILY.open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return {
            row["trade_date"].replace("-", ""): float(row["strategy_nav"])
            for row in rows
            if row["version_id"] == version_id and START <= row["trade_date"].replace("-", "") <= END
        }


def common_series() -> dict[str, list[tuple[str, float]]]:
    candidate = canonical_nav("internal_subsleeve_mom12_70_30")
    baseline = canonical_nav("v57f_startup_preload_repaired_baseline")
    days = sorted(set(candidate) & set(baseline))
    if len(days) != 1228 or days[0] != START or days[-1] != END:
        raise ValueError(f"Unexpected formal common sample: {len(days)} {days[:1]} {days[-1:]}")
    return {
        "internal_subsleeve_mom12_70_30": [(day, candidate[day] / candidate[days[0]]) for day in days],
        "v57f_startup_preload_repaired_baseline": [(day, baseline[day] / baseline[days[0]]) for day in days],
    }


def annual_statistics(series: list[tuple[str, float]]) -> list[dict[str, object]]:
    by_year: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for item in series:
        by_year[item[0][:4]].append(item)
    previous_end = 1.0
    output = []
    for year, values in sorted(by_year.items()):
        start_value = previous_end
        end_value = values[-1][1]
        high = start_value
        max_drawdown = 0.0
        for _, nav in values:
            high = max(high, nav)
            max_drawdown = min(max_drawdown, nav / high - 1.0)
        output.append({
            "year": year,
            "sample_start": values[0][0],
            "sample_end": values[-1][0],
            "observations": len(values),
            "calendar_return_pct": (end_value / start_value - 1.0) * 100,
            "in_year_max_drawdown_pct": max_drawdown * 100,
            "partial_calendar_year": year in {"2021", "2026"},
        })
        previous_end = end_value
    return output


def draw_pairwise_chart(series: dict[str, list[tuple[str, float]]], annual: list[dict[str, object]]) -> Path:
    output = FIGURES / "v5w_formal_pairwise_annual_return_and_underwater.png"
    candidate = series["internal_subsleeve_mom12_70_30"]
    baseline = series["v57f_startup_preload_repaired_baseline"]
    annual_map: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in annual:
        annual_map[row["model_id"]][row["year"]] = row
    image = Image.new("RGB", (3200, 2020), "#ffffff")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, grid = "#17324d", "#27364a", "#5e6f82", "#dbe5ef"
    red, teal = "#ca7a73", "#3f8f98"
    draw.rounded_rectangle((42, 30, 3158, 214), radius=18, fill="#f7fafc", outline="#c8d6e5", width=2)
    text(draw, (82, 56), "V5 正式共同样本：年度收益拆解与共同窗口 underwater 路径", navy, 42, True)
    text(draw, (84, 123), "仅比较 repaired baseline 与主候选：2021-05-06 至 2026-05-29，1,228 个共同交易日，同父策略、同回报合同。", muted, 22)
    text(draw, (84, 163), "年度收益仅为描述性拆解；2021 与 2026 为非完整日历年。validation_not_independent，主候选尚未 accepted。", "#9a5b13", 21, True)

    left, right = 165, 2980
    bar_top, bar_bottom = 330, 870
    draw.rounded_rectangle((left, bar_top, right, bar_bottom), radius=8, fill="#fcfdff", outline="#d8e2ec", width=2)
    years = ["2021", "2022", "2023", "2024", "2025", "2026"]
    returns = [float(annual_map[model][year]["calendar_return_pct"]) for model in annual_map for year in years]
    scale = max(10, math.ceil(max(returns) / 5) * 5)
    y_zero = bar_bottom
    for value in range(0, scale + 1, 5):
        y = bar_bottom - value / scale * (bar_bottom - bar_top)
        draw.line((left, y, right, y), fill="#b7c8d9" if value == 0 else "#e8eef5", width=3 if value == 0 else 2)
        text(draw, (72, y - 13), f"{value}%", muted, 18)
    text(draw, (left + 22, bar_top + 20), "日历年度收益（2021 / 2026 为部分年度）", "#30735f", 20, True)
    group_width = (right - left) / len(years)
    for index, year in enumerate(years):
        center = left + group_width * (index + 0.5)
        for offset, model, color in [(-56, "v57f_startup_preload_repaired_baseline", teal), (14, "internal_subsleeve_mom12_70_30", red)]:
            value = float(annual_map[model][year]["calendar_return_pct"])
            x1, x2 = center + offset, center + offset + 48
            y = y_zero - value / scale * (bar_bottom - bar_top)
            draw.rounded_rectangle((x1, min(y, y_zero), x2, max(y, y_zero)), radius=4, fill=color)
            label_y = y - 30 if value >= 0 else y + 8
            text(draw, (x1 - 10, label_y), f"{value:.1f}%", color, 16, True)
        text(draw, (center - 25, bar_bottom + 24), year + ("*" if year in {"2021", "2026"} else ""), muted, 20)
    draw.rounded_rectangle((2100, bar_top + 20, 2920, bar_top + 98), radius=8, fill="#ffffff", outline="#d8e2ec", width=2)
    draw.line((2130, bar_top + 48, 2190, bar_top + 48), fill=teal, width=8)
    text(draw, (2210, bar_top + 29), "repaired baseline", teal, 19, True)
    draw.line((2515, bar_top + 48, 2575, bar_top + 48), fill=red, width=8)
    text(draw, (2595, bar_top + 29), "主候选", red, 19, True)

    uw_top, uw_bottom = 1030, 1655
    # Reserve a header band and bottom breathing room so the 0% line and
    # drawdown path cannot cover the title or touch the panel border.
    uw_plot_top, uw_plot_bottom = uw_top + 104, uw_bottom - 30
    draw.rounded_rectangle((left, uw_top, right, uw_bottom), radius=8, fill="#fcfdff", outline="#d8e2ec", width=2)
    start_ordinal, end_ordinal = day_ordinal(START), day_ordinal(END)
    for year in [2021, 2022, 2023, 2024, 2025, 2026]:
        tick = date(year, 1, 1).toordinal()
        if start_ordinal <= tick <= end_ordinal:
            x = left + (tick - start_ordinal) / (end_ordinal - start_ordinal) * (right - left)
            draw.line((x, uw_plot_top, x, uw_plot_bottom), fill=grid, width=2)
            text(draw, (x - 25, uw_bottom + 22), str(year), muted, 20)
    drawdowns: dict[str, list[tuple[str, float]]] = {}
    for label, values in [("主候选", candidate), ("repaired baseline", baseline)]:
        high = values[0][1]
        drawdowns[label] = []
        for day, nav in values:
            high = max(high, nav)
            drawdowns[label].append((day, (nav / high - 1) * 100))
    lower = math.floor(min(value for values in drawdowns.values() for _, value in values) / 2) * 2
    for value in range(int(lower), 1, 2):
        y = uw_plot_top + (0 - value) / (0 - lower) * (uw_plot_bottom - uw_plot_top)
        draw.line((left, y, right, y), fill="#b7c8d9" if value == 0 else "#e8eef5", width=3 if value == 0 else 2)
        text(draw, (72, y - 13), f"{value}%", muted, 18)
    text(draw, (left + 22, uw_top + 20), "共同窗口 underwater / 自历史高点回撤", "#30735f", 20, True)

    def points(values: list[tuple[str, float]]) -> list[tuple[float, float]]:
        return [(left + (day_ordinal(day) - start_ordinal) / (end_ordinal - start_ordinal) * (right - left), uw_plot_top + (0 - value) / (0 - lower) * (uw_plot_bottom - uw_plot_top)) for day, value in values]

    baseline_points = points(drawdowns["repaired baseline"])
    draw.line(baseline_points, fill="#ffffff", width=14, joint="curve")
    draw.line(baseline_points, fill=teal, width=8, joint="curve")
    # A light dashed candidate line keeps the near-overlapping baseline visible.
    candidate_points = points(drawdowns["主候选"])
    for index in range(0, len(candidate_points) - 4, 8):
        draw.line(candidate_points[index:index + 5], fill=red, width=8, joint="curve")
    text(draw, (165, 1825), "解读边界：图表呈现同窗口历史观察，不构成独立验证、未来收益预测、accepted 或实盘批准。严格现金 NAV、QMT 历史合同与独立前瞻纸面周期仍未完成。", muted, 18)
    image.save(output, quality=95)
    return output


def draw_sector_funnel(rows: list[dict[str, str]]) -> Path:
    output = FIGURES / "v5w_sector_research_decision_funnel.png"
    stages = [
        ("纳入近似板块研究", len(rows), "#2f855a"),
        ("可进入 basket shadow pool", sum(row["pm_screening_decision"] == "ready_for_basket_shadow_pool" for row in rows), "#2563a7"),
        ("仅观察 / 专项研究", sum(row["pm_screening_decision"] in {"basket_observation_only", "needs_manual_research_before_formal"} for row in rows), "#b7791f"),
        ("周期数据门阻塞", sum(row["pm_screening_decision"] == "blocked_by_cycle_data_gate" for row in rows), "#b42318"),
    ]
    image = Image.new("RGB", (3200, 1700), "#ffffff")
    draw = ImageDraw.Draw(image)
    navy, ink, muted = "#17324d", "#27364a", "#5e6f82"
    draw.rounded_rectangle((42, 30, 3158, 215), radius=18, fill="#f7fafc", outline="#c8d6e5", width=2)
    text(draw, (82, 56), "V5 近似行业研究漏斗：从板块探索到受限 basket 候选", navy, 42, True)
    text(draw, (84, 123), "来源为冻结的 8 个板块 data-availability screening；它描述研究门禁与路径，不按历史收益挑选行业。", muted, 22)
    text(draw, (84, 162), "通过筛选不等于 accepted、实盘批准或已形成独立验证；所有板块仍受 PIT、执行与前瞻证据边界约束。", "#9a5b13", 21, True)

    center, top, height = 1600, 330, 150
    for index, (label, count, color) in enumerate(stages):
        y = top + index * 220
        width = 260 + count * 210
        x1, x2 = center - width / 2, center + width / 2
        draw.rounded_rectangle((x1, y, x2, y + height), radius=12, fill=color)
        text(draw, (x1 + 40, y + 35), label, "#ffffff", 28, True)
        text(draw, (x2 - 100, y + 35), f"{count} 个板块", "#ffffff", 27, True)
        if index < len(stages) - 1:
            draw.line((center, y + height + 18, center, y + 200), fill="#93a4b5", width=6)
            draw.polygon([(center - 14, y + 190), (center + 14, y + 190), (center, y + 212)], fill="#93a4b5")
    ready = [row["display_name"] for row in rows if row["pm_screening_decision"] == "ready_for_basket_shadow_pool"]
    draw.rounded_rectangle((170, 1270, 1510, 1530), radius=10, fill="#f8fafc", outline="#c8d6e5", width=2)
    text(draw, (210, 1305), "进入 shadow pool 的四个核心研究方向", navy, 24, True)
    text(draw, (210, 1360), " / ".join(ready), ink, 21)
    draw.rounded_rectangle((1690, 1270, 3030, 1530), radius=10, fill="#fffaf5", outline="#edc985", width=2)
    text(draw, (1730, 1305), "为什么其余方向没有直接进入核心组合", "#955b10", 24, True)
    text(draw, (1730, 1360), "小样本集中度、经营纯度与专项字段缺失、周期状态 PIT 数据门，或需要单独的行业研究假设。", muted, 20)
    text(draw, (170, 1620), "注：正式 V5 repaired baseline 的四个 core sleeve 为银行、电力、高速、港口铁路；本图是早期/并行行业筛选证据，应在报告中与最终主线构成区分说明。", muted, 17)
    image.save(output, quality=95)
    return output


def draw_sector_funnel(rows: list[dict[str, str]]) -> Path:
    """Render mutually exclusive sector decisions as branches, not a sequential funnel."""
    output = FIGURES / "v5w_sector_research_decision_funnel.png"
    buckets = [
        ("Shadow pool 候选", "ready_for_basket_shadow_pool", "#2563a7", "可进入受限 basket 研究", ["Bank", "Utilities / Electricity", "Highway Infrastructure", "Port / Rail Infrastructure"]),
        ("仅观察", "basket_observation_only", "#b7791f", "不作为普通核心 sleeve", ["Telecom Operators", "Insurance"]),
        ("待人工专项研究", "needs_manual_research_before_formal", "#9a6b16", "先补经营纯度与行业字段", ["Gas / Water Operators"]),
        ("周期数据门阻塞", "blocked_by_cycle_data_gate", "#b42318", "只允许修复 PIT 状态数据门", ["Coal"]),
    ]
    counts = {decision: sum(row["pm_screening_decision"] == decision for row in rows) for _, decision, _, _, _ in buckets}
    if sum(counts.values()) != len(rows):
        raise ValueError("Sector decisions are not an exhaustive mutually exclusive partition")
    image = Image.new("RGB", (3200, 1700), "#ffffff")
    draw = ImageDraw.Draw(image)
    navy, ink, muted = "#17324d", "#27364a", "#5e6f82"
    draw.rounded_rectangle((42, 30, 3158, 215), radius=18, fill="#f7fafc", outline="#c8d6e5", width=2)
    text(draw, (82, 56), "V5 近似行业研究决策分布：8 个板块的互斥去向", navy, 42, True)
    text(draw, (84, 123), "来源为冻结的 data-availability screening。四个结果是并列分类，不是按历史收益排序，也不是连续漏斗。", muted, 22)
    text(draw, (84, 162), "进入 shadow pool 只表示可进入受限 basket 研究，不代表 accepted、实盘批准或已形成独立验证。", "#9a5b13", 21, True)

    root_left, root_right, root_top, root_bottom = 590, 2610, 330, 500
    draw.rounded_rectangle((root_left, root_top, root_right, root_bottom), radius=12, fill="#2f855a")
    text(draw, (root_left + 44, root_top + 45), "近似行业探索起点", "#ffffff", 30, True)
    text(draw, (root_right - 170, root_top + 45), "8 个板块", "#ffffff", 30, True)
    junction_y = 690
    draw.line((1600, root_bottom + 18, 1600, junction_y), fill="#93a4b5", width=7)
    draw.line((480, junction_y, 2820, junction_y), fill="#93a4b5", width=7)

    box_y, box_h, box_w = 805, 350, 660
    x_positions = [150, 930, 1710, 2490]
    for (title, decision, color, description, examples), x in zip(buckets, x_positions):
        center_x = x + box_w / 2
        draw.line((center_x, junction_y, center_x, box_y - 22), fill="#93a4b5", width=6)
        draw.polygon([(center_x - 14, box_y - 33), (center_x + 14, box_y - 33), (center_x, box_y - 12)], fill="#93a4b5")
        draw.rounded_rectangle((x, box_y, x + box_w, box_y + box_h), radius=12, fill="#ffffff", outline=color, width=5)
        draw.rounded_rectangle((x, box_y, x + box_w, box_y + 76), radius=12, fill=color)
        text(draw, (x + 28, box_y + 21), title, "#ffffff", 24, True)
        text(draw, (x + box_w - 120, box_y + 21), f"{counts[decision]} 个", "#ffffff", 23, True)
        text(draw, (x + 28, box_y + 112), description, ink, 22, True)
        line_y = box_y + 165
        for example in examples:
            text(draw, (x + 28, line_y), example, muted, 22)
            line_y += 45
    draw.rounded_rectangle((170, 1290, 3030, 1515), radius=10, fill="#f8fafc", outline="#c8d6e5", width=2)
    text(draw, (210, 1323), "报告使用方式", navy, 23, True)
    text(draw, (210, 1373), "将此图放在“行业迁移与研究路径”章节，用来解释为什么金融理论、统计证据、PIT 数据与工程可行性必须同时通过；它不是收益宣传图。", muted, 23)
    text(draw, (170, 1602), "注：正式 V5 repaired baseline 的四个 core sleeve 为银行、电力、高速、港口铁路；本图来自早期/并行行业筛选证据，正文需明确二者的时间与治理层级不同。", muted, 19)
    image.save(output, quality=95)
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "not_available"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    series = common_series()
    annual_rows: list[dict[str, object]] = []
    for model_id, values in series.items():
        for row in annual_statistics(values):
            annual_rows.append({"model_id": model_id, **row, "return_contract": "local_daily_parent_strategy_contract", "validation_status": "validation_not_independent"})
    write_csv(OUTPUT / "v5w_formal_pairwise_annual_decomposition.csv", annual_rows)

    drawdown_rows = []
    for model_id, values in series.items():
        high = values[0][1]
        for day, nav in values:
            high = max(high, nav)
            drawdown_rows.append({"model_id": model_id, "trade_date": f"{day[:4]}-{day[4:6]}-{day[6:]}", "normalized_nav": nav, "underwater_pct": (nav / high - 1) * 100})
    write_csv(OUTPUT / "v5w_formal_pairwise_underwater.csv", drawdown_rows)

    with SECTORS.open(encoding="utf-8-sig", newline="") as handle:
        sector_rows = list(csv.DictReader(handle))
    funnel_rows = [{"sector_id": row["sector_id"], "display_name": row["display_name"], "screening_decision": row["pm_screening_decision"], "basket_role": row["basket_role"], "next_gate": row["next_gate"], "blockers": row["blockers"]} for row in sector_rows]
    write_csv(OUTPUT / "v5w_sector_research_funnel_source.csv", funnel_rows)

    evidence_rows = [
        {"evidence_area": "正式 daily NAV pairwise", "status": "available", "scope": "2021-05-06 至 2026-05-29，1,228 日", "report_use": "正式表现正文", "boundary": "validation_not_independent"},
        {"evidence_area": "repaired baseline 合同", "status": "available", "scope": "startup preload repaired baseline", "report_use": "正式比较基线", "boundary": "旧 2021-10 链路不得使用"},
        {"evidence_area": "2013-2021 V5 四 sleeve exact PIT 重建", "status": "partial_unresolved", "scope": "部分原始披露与公司行为证据仍缺", "report_use": "研究边界与限制", "boundary": "不得写成完成的独立 rolling 验证"},
        {"evidence_area": "严格现金 NAV", "status": "unavailable", "scope": "历史原始现金状态缺失", "report_use": "强制披露", "boundary": "阻塞 accepted 与强执行结论"},
        {"evidence_area": "QMT 历史成交合同", "status": "incomplete", "scope": "脚本、配置、target/order/fill/position/cash 原件不完整", "report_use": "执行证据附录", "boundary": "不得声称精确成交归因"},
        {"evidence_area": "ETF total-return 合同", "status": "unavailable", "scope": "本地仅有价格参考", "report_use": "economic exposure context", "boundary": "不得计算正式 ETF Alpha/Beta/IR/超额收益"},
        {"evidence_area": "独立前瞻纸面周期", "status": "not_formed", "scope": "尚无完整 target->order->fill->position->cash 周期", "report_use": "下一门槛", "boundary": "主候选保持 not accepted"},
    ]
    write_csv(OUTPUT / "v5w_evidence_coverage_matrix.csv", evidence_rows)

    annual_chart = draw_pairwise_chart(series, annual_rows)
    funnel_chart = draw_sector_funnel(sector_rows)

    prompt = """# V5w 最终报告前期准备执行提示词

工作目录：`D:\\hh\\codex\\v5`

目标：为研究生申请用途准备最终报告的可审计前置材料。报告应呈现 V1-V4 银行多因子价值基础如何被扩展为近似行业的 agent 研究流程，并最终形成受治理的个人化红利 ETF 式组合研究；不是实盘说明、募资材料或收益承诺。

固定边界：唯一正式基线为 `v57f_startup_preload_repaired_baseline`；正式窗口为 2021-05-01 至 2026-05-31，正式共同样本为 2021-05-06 至 2026-05-29 的 1,228 日；主候选为 `internal_subsleeve_mom12_70_30`，状态只能保持 `primary_forward_paper_candidate_not_accepted`。

分工：研究 agent 审查行业假设、金融解释与失败路径；量化 agent 复核所有正式图表和统计口径；工程 agent 复核输入、哈希、脚本和文件边界；PM 合并结论并阻止 diagnostics、执行工程、ETF 价格参考进入正式收益排序。

必须输出：
1. 正式 pairwise 年度收益/underwater 图和表，只含 baseline 与主候选；
2. 行业筛选漏斗，区分 shadow-pool、观察、人工研究和周期数据门；
3. 一张证据覆盖矩阵，明确 pre-2021 PIT、严格现金 NAV、QMT 合同、ETF total return 和前瞻纸面周期边界；
4. 最终报告目录、图表使用顺序、每图的一句限制说明；
5. 申请材料视角的作者贡献说明：金融解释提出假设，统计和 agent 提高研究规模与可复现性，PM 治理避免事后调参和越界升级。

禁止：不修改模型、窗口、费用、因子、权重、候选状态；不联网补数据；不运行 JoinQuant/QMT/桥接；不生成 future target；不将 validation_not_independent 写成独立验证；不将 ETF price return 写成 ETF total return。

最终交付应先让读者理解：研究发现了什么、没有证明什么、下一项证据门槛是什么。
"""
    (OUTPUT / "v5w_project_manager_execution_prompt.md").write_text(prompt, encoding="utf-8")

    plan = """# V5 最终报告前期内容与图表计划

## 正文建议顺序

1. 研究问题与作者贡献：从 V1-V4 银行多因子价值基础出发，建立理论驱动、统计验证、工程复现和 PM 治理相互约束的 agent 工作流。
2. 研究边界：PIT 原则、startup preload repair、正式窗口、禁止事后调参，以及验证非独立的含义。
3. 行业迁移：用行业研究漏斗说明哪些路径进入 shadow pool，哪些保留观察或被周期数据门阻断。
4. 正式核心组合与主候选：四个 core sleeve 的经济角色；价值低波为选股基础，动量仅在同 sleeve 内做固定治理。
5. 唯一正式表现比较：repaired baseline 与主候选的同合同 pairwise 表、年度收益/underwater 图。
6. 研究分支与失败：V5g/V5h 等只能作为观察线；均值回归、日内技术路径和其他诊断不进入收益排序。
7. 现实执行与证据边界：现金 NAV、QMT 合同、ETF total return 与前瞻纸面闭环。
8. 结论：历史研究形成了一个受约束的候选和可迁移流程，但没有形成 accepted 或实盘批准。

## 推荐主文图表（最多 8 张）

1. 项目目的与 agent 系统图。
2. 时间序列隔离与 PIT 证据边界图。
3. 金融理论、统计验证、工程实现三角图。
4. 行业研究漏斗图。
5. 四个 core sleeve 的市场背景图。
6. repaired baseline 与主候选正式 pairwise 图。
7. 年度收益与 underwater 图。
8. ETF 经济暴露参考图（仅上下文，不进入正式表现章节）。

## 附录材料

- 研究/执行观察线相对主候选图。
- 完整模型分层、执行工程、数据门、QMT 和 ETF 证据表。
- 可复现性输入、SHA256、Git HEAD、统计口径与 claim-to-evidence 索引。
"""
    (OUTPUT / "v5w_report_content_and_visual_plan.md").write_text(plan, encoding="utf-8")

    readiness = [
        {"item": "正式 pairwise 数字与共同样本复核", "status": "completed", "evidence": "v5w_formal_pairwise_annual_decomposition.csv / v5w_formal_pairwise_underwater.csv"},
        {"item": "行业漏斗及非通过路径的可视化", "status": "completed", "evidence": "v5w_sector_research_funnel_source.csv / figure"},
        {"item": "强制证据边界汇总", "status": "completed", "evidence": "v5w_evidence_coverage_matrix.csv"},
        {"item": "最终报告图表顺序与正文定位", "status": "completed", "evidence": "v5w_report_content_and_visual_plan.md"},
        {"item": "pre-2021 exact PIT 完整重建", "status": "unresolved", "evidence": "只能作为限制，不能写为已完成 V5 独立验证"},
        {"item": "strict cash NAV / QMT 历史合同 / 前瞻纸面闭环", "status": "unresolved", "evidence": "阻塞 accepted、实盘与强执行结论"},
    ]
    write_csv(OUTPUT / "v5w_final_report_preparation_checklist.csv", readiness)

    inputs = [PERFORMANCE, CANONICAL_DAILY, SECTORS, FIGURE_REGISTER]
    manifest = [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "role": role} for path, role in zip(inputs, ["formal_statistics", "canonical_pairwise_daily_nav", "sector_screening_source", "existing_figure_register"])]
    write_csv(OUTPUT / "v5w_input_manifest.csv", manifest)
    write_csv(OUTPUT / "v5w_source_contract_conflict_log.csv", [{
        "artifact": "v5w_formal_pairwise_annual_return_and_underwater",
        "detected_issue": "platform_export_nav_drawdown_conflicts_with_v5r_v5s_frozen_formal_statistics",
        "excluded_source": "data/joinquant_exports/v5f_internal_subsleeve_mom12_70_30/historical_platform_attribution/daily_returns_primary_result_1_20.csv and daily_returns_baseline_result_1_21.csv",
        "resolved_source": str(CANONICAL_DAILY.relative_to(ROOT)),
        "resolution": "use_version-filtered canonical rows for internal_subsleeve_mom12_70_30 and v57f_startup_preload_repaired_baseline",
        "status": "resolved_before_final_report_use",
    }])
    summary = {
        "task": "v5w_final_report_preparation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "formal_baseline": "v57f_startup_preload_repaired_baseline",
        "formal_window": "2021-05-01_to_2026-05-31",
        "formal_common_sample": {"start": "2021-05-06", "end": "2026-05-29", "observations": 1228},
        "primary_candidate": "internal_subsleeve_mom12_70_30",
        "candidate_status": "primary_forward_paper_candidate_not_accepted",
        "new_figures": [str(annual_chart.relative_to(ROOT)), str(funnel_chart.relative_to(ROOT))],
        "formal_pairwise_source": str(CANONICAL_DAILY.relative_to(ROOT)),
        "sector_screening_source_count": len(sector_rows),
        "git_head": git_head(),
        "hard_boundaries": ["validation_not_independent", "strict_cash_nav_unavailable", "qmt_contract_incomplete", "etf_total_return_contract_missing", "independent_forward_paper_cycle_not_formed"],
    }
    (OUTPUT / "v5w_final_report_preparation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
