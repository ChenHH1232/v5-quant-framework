from __future__ import annotations

"""V5u application-facing portfolio pack.

This is a documentation and provenance layer only. It reads frozen local
evidence and does not touch strategy rules, historical series, platforms, or
post-2026-05-31 market data.
"""

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5u_graduate_project_portfolio") / "current"
BASELINE = "v57f_startup_preload_repaired_baseline"
PRIMARY = "internal_subsleeve_mom12_70_30"
REQUIRED = (
    "config/v5_context.json",
    "config/v5_active_model_registry.json",
    "config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json",
    "v5_sample_split_governance_correction/current/v5_sample_split_governance_summary.json",
    "v5f_pre2021_multisleeve_mainline_validation/current/v5f_pre2021_validation_summary.json",
    "v5j_pit_availability_boundary_closeout/current/v5j_pit_availability_boundary_closeout_summary.json",
    "v5m_p0_closure/current/v5m_p0_closure_summary.json",
    "v5t_report_publication_finalization/current/v5t_publication_summary.json",
    "v5r_overall_research_governance_report_draft/current/v5r_performance_comparison_table.csv",
    "config/v5_test_tiers.json",
)


def run_v5u_graduate_project_portfolio(root: Path = Path("."), output_dir: Path | None = None, test_status: str = "not_run_by_runner") -> dict[str, Any]:
    root = Path(root)
    _assert_inputs(root)
    out = output_dir or root / OUT
    out.mkdir(parents=True, exist_ok=True)
    context = _json(root / "config/v5_context.json")
    registry = _json(root / "config/v5_active_model_registry.json")
    split = _json(root / "v5_sample_split_governance_correction/current/v5_sample_split_governance_summary.json")
    pre = _json(root / "v5f_pre2021_multisleeve_mainline_validation/current/v5f_pre2021_validation_summary.json")
    pit = _json(root / "v5j_pit_availability_boundary_closeout/current/v5j_pit_availability_boundary_closeout_summary.json")
    closure = _json(root / "v5m_p0_closure/current/v5m_p0_closure_summary.json")
    published = _json(root / "v5t_report_publication_finalization/current/v5t_publication_summary.json")
    etf = _json(root / "config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json")
    metrics = _performance(root)

    prompt = _execution_prompt()
    (out / "v5u_execution_prompt.md").write_text(prompt, encoding="utf-8")
    (out / "v5u_application_project_brief.md").write_text(_project_brief(context, split, metrics), encoding="utf-8")
    (out / "v5u_application_abstract_cn_en.md").write_text(_abstract(), encoding="utf-8")
    (out / "v5u_golden_case_bank_reproduction.md").write_text(_golden_case(), encoding="utf-8")
    (out / "v5u_reproducibility_release_protocol.md").write_text(_release_protocol(), encoding="utf-8")
    (out / "v5u_personalized_dividend_etf_methodology.md").write_text(_etf_methodology(etf), encoding="utf-8")
    (out / "v5u_pre2021_validation_evidence_hierarchy.md").write_text(_pre2021_note(split, pre, pit), encoding="utf-8")
    (out / "v5u_application_submission_outline.md").write_text(_submission_outline(), encoding="utf-8")

    _write_csv(out / "v5u_sector_extension_scorecard.csv", _sector_scorecard())
    _write_csv(out / "v5u_golden_case_input_manifest.csv", _golden_case_manifest(root))
    _write_csv(out / "v5u_reproducibility_release_manifest.csv", _release_manifest(root))
    _write_csv(out / "v5u_standard_ci_readiness.csv", _ci_readiness(root))
    _write_csv(out / "v5u_test_results.csv", [{"test_scope": "v5u_targeted", "status": test_status}, {"test_scope": "fast", "status": "not_run_by_runner"}, {"test_scope": "standard", "status": "not_run_by_runner"}, {"test_scope": "extended", "status": "not_run"}])
    _write_csv(out / "v5u_blockers.csv", _blockers(pit, closure))
    (out / "v5u_pm_application_readiness_report.md").write_text(_pm_report(pre, pit, closure), encoding="utf-8")

    summary = {
        "created_at_utc": _now(),
        "task": "v5u_graduate_project_portfolio",
        "purpose": "graduate_application_fintech_statistics_portfolio",
        "historical_research_window": split["train_test_window"],
        "formal_backtest_window": split["backtest_window"],
        "baseline": BASELINE,
        "primary_candidate": PRIMARY,
        "primary_candidate_status": registry["active_models"][0]["role"],
        "v5t_archive_release": published["release_decision"],
        "portfolio_components_completed": 7,
        "strategy_or_status_modified": False,
        "network_or_platform_started": False,
        "accepted": False,
    }
    _write_json(out / "v5u_application_portfolio_summary.json", summary)
    return summary


def update_v5u_test_results(root: Path = Path("."), output_dir: Path | None = None, statuses: dict[str, str] | None = None) -> None:
    out = output_dir or Path(root) / OUT
    statuses = statuses or {}
    _write_csv(out / "v5u_test_results.csv", [{"test_scope": name, "status": value} for name, value in statuses.items()])


def _execution_prompt() -> str:
    return """# V5u Application Portfolio Execution Prompt

## Objective

Turn V5 into a graduate-application-ready FinTech and statistics project without changing any strategy, data window, historical statistic or governance status.

## Fixed facts

- Research train/test window: 2013-01-01 to 2021-04-30.
- Formal backtest window: 2021-05-01 to 2026-05-31.
- Sole formal baseline: `v57f_startup_preload_repaired_baseline`.
- Primary candidate: `internal_subsleeve_mom12_70_30`, `primary_forward_paper_candidate_not_accepted`.
- Do not claim accepted, live approval, independent validation, or an ETF total-return comparison.

## Deliver seven components

1. A bilingual application brief that explains the V1-V4 bank foundation, V5 agent workflow, statistical discipline and personalized dividend-ETF construction.
2. A reproducible bank golden-case runbook from hypothesis to evidence packet.
3. A sector-extension scorecard showing the core sleeves, negative cases and evidence tier.
4. A release manifest and clean-room reproduction protocol.
5. A Standard-CI readiness record; do not claim hosted CI is ready while ignored evidence artifacts are not versioned.
6. A personalized dividend ETF methodology, clearly separated from commercial ETF return comparison.
7. A pre-2021 evidence hierarchy that reports genuine PIT limitations rather than using proxies as exact reconstruction.

## Required tone

Academic, concrete and falsifiable. Present negative results and data unavailability as research controls. Do not optimize or rank models by historical return.
"""


def _abstract() -> str:
    return """# 摘要 / Abstract

## 中文

本项目从 V1-V4 的银行多因子价值策略出发，发展出 V5：一个由项目经理、研究、统计验证和工程四类 agent 协作的量化研究流程。系统要求每个假设经过财务解释、PIT 数据可见性审计、样本隔离、统计验证、工程复现和治理决策。项目进一步将银行方法扩展至电力公用事业、高速基础设施和港口铁路等高股息相近行业，以固定 sleeve、行业内因子和组合约束构建个性化红利 ETF 式组合。2013-01-01 至 2021-04-30 用于训练与验证，2021-05-01 至 2026-05-31 为冻结的正式回测窗。项目明确记录数据不可得、代理基准、现金状态和平台合同等限制，不把历史收益视为策略接受或实盘许可。

## English

This project develops V5, an AI-assisted quantitative research workflow, from a V1-V4 bank multi-factor value strategy. A project-manager, research, statistical-validation, and engineering agent structure enforces financial rationale, point-in-time data visibility, sample isolation, reproducible implementation, and explicit governance decisions. The approach is extended from banks to adjacent dividend-oriented sleeves in utilities, highway infrastructure, and port/rail infrastructure to construct a personalized dividend-ETF-like portfolio under fixed sector and position constraints. The 2013-01-01 to 2021-04-30 period is reserved for research and validation; 2021-05-01 to 2026-05-31 is a frozen formal backtest window. The project documents missing data, proxy benchmarks, cash-state limitations, and incomplete platform contracts rather than translating historical returns into an acceptance or live-trading claim.
"""


def _project_brief(context: dict[str, Any], split: dict[str, Any], metrics: dict[str, dict[str, str]]) -> str:
    baseline, primary = metrics[BASELINE], metrics[PRIMARY]
    return f"""# V5 研究生申请项目简介

## 研究命题

V5 回答的不是“怎样找到最高历史收益的策略”，而是：能否把一个银行多因子价值投资思想，转化成可审计、可复现、可扩展且受统计纪律约束的量化研究系统？项目的金融科技贡献是 agent 分工、结构化策略规格与证据链；统计贡献是 PIT、样本隔离、共同样本比较、滚动/稳健性审计和拒绝机制。

## 从 V1-V4 到 V5

V1-V4 建立了银行多因子价值策略及其统计验证习惯。V5 将该过程系统化：项目经理决定研究顺序；研究 agent 将金融逻辑转成假设；统计 agent 负责 PIT、因子与样本审计；工程 agent 生成可运行代码、测试与结果包。人类负责最终研究判断，AI 不拥有策略接受权限。

```mermaid
flowchart LR
    H[金融假设与银行多因子基础] --> R[研究 Agent\n经济逻辑与因子规格]
    R --> Q[统计验证 Agent\nPIT、样本隔离、稳健性]
    Q --> E[工程 Agent\n回测、测试、来源哈希]
    E --> P[项目经理 Agent\n证据分层与治理决定]
    P --> A[归档：candidate / diagnostic / blocked]
    P --> X[拒绝：不得仅凭收益 accepted]
```

## 数据与样本设计

- 训练/验证窗口：{split['train_test_window']}。
- 冻结正式回测窗口：{split['backtest_window']}。
- 2021-2026 不可用于因子发现、参数调优、滚动验证或独立验证。
- 唯一正式基线：`{BASELINE}`；首个有效信号日为 2021-05-06。

## 组合构建

个性化红利 ETF 式组合由银行、电力公用事业、高速基础设施和港口铁路基础设施四个核心 sleeve 构成。每个 sleeve 使用同一受约束研究流程，但允许金融机制决定行业内可用因子；组合层固定行业上限、单股上限、目标持仓数与调仓频率，防止跨行业事后调权。

## 正式可比结果的正确表述

唯一允许写入正式表现表的是 repaired baseline 与主候选 `internal_subsleeve_mom12_70_30` 的共同日样本比较：{primary['observations']} 个交易日，{primary['start_date']} 至 {primary['end_date']}。主候选历史总收益为 {float(primary['total_return_pct']):.4f}%，基线为 {float(baseline['total_return_pct']):.4f}%；这只是 `validation_not_independent` 条件下的历史观察，绝非接受、部署或未来收益承诺。

## 评审应看到的能力

1. 将金融理论转为可检验策略假设。
2. 正确隔离研究窗与回测窗，并主动拒绝污染性结论。
3. 用 agent 分工和机器可读规格降低研究与工程混淆。
4. 用行业扩展和失败案例检验可迁移性，而不是只展示赢家。
5. 将现金、交易、平台一致性和数据不可得性纳入同一治理框架。
"""


def _golden_case() -> str:
    return """# 银行黄金案例：可复现演示路径

## 用途

这是申请材料中的端到端演示，而非新的策略实验。案例从 V1-V4 银行多因子价值研究出发，展示 V5 如何将一个金融假设转为受审计的研究包。

## 输入

- 基础策略规格：`examples/bank_value_15y_strategy.json` 与 `examples/bank_high_dividend_sustainability_v3_strategy.json`。
- 研究假设：低估、分红、资产质量与低波动共同刻画银行价值与可持续性。
- 证据层：`docs/governance/bank_high_dividend_v3_research_validation_v1.md`、PIT 面板与平台复现材料。

## 流程

1. 研究 agent 写入因子方向、经济解释和不可接受的替代解释。
2. 数据层记录报告期、可见日、来源和缺失状态；不得用后续年报补当时不可见字段。
3. 统计 agent 在 2013-01-01 至 2021-04-30 内完成覆盖度、IC/RankIC、年度刷新、滚动与稳健性检查。
4. 项目经理冻结规则和比较合同；2021-05-01 至 2026-05-31 只作正式回测，不再挑选因子。
5. 工程 agent 生成回测、持仓、订单健康度、测试和来源哈希；平台适配不得改变策略合同。
6. PM 输出 candidate、diagnostic 或 blocked 决定，并将失败原因保留为可复查证据。

## 复现实验命令

```powershell
$env:PYTHONPATH = 'src'
python -m unittest tests.test_v5u_graduate_project_portfolio_runner
python scripts/run_v5_tests.ps1 -Tier Fast
python scripts/run_v5_tests.ps1 -Tier Standard
```

历史数据和生成产物不应被重新抓取或覆盖。复现者必须先对照 `v5u_golden_case_input_manifest.csv` 的 SHA256 与本地输入。

## 展示重点

展示“假设如何被证据支持或拒绝”，而不是只展示收益曲线。银行案例是最完整的领域样本；其余行业用于检验工作流的迁移性与边界。
"""


def _release_protocol() -> str:
    return """# V5 可复现发布协议

## 目标

将申请材料与可运行研究代码分开，避免生成产物、原始资料和临时文件污染可复现的项目版本。

## 建议发布结构

1. `source-release`：`src/`、`tests/`、`config/`、`examples/`、`docs/` 和测试入口。
2. `evidence-bundle`：冻结的 CSV/JSON/PDF，附 SHA256 清单；不得被测试直接覆盖。
3. `application-bundle`：摘要、系统图、黄金案例、行业 scorecard、限制清单和 V5t 报告。
4. `raw-data-index`：只保留来源说明、可见日和哈希；不把受许可或大体量数据混入源码仓库。

## 发布门禁

- 记录 Git HEAD 与工作区状态，不在归档任务中执行 add、commit、reset 或 clean。
- Fast 必须通过；Standard 必须在匹配的本地 evidence-bundle 上通过。
- 所有报告显示研究窗、回测窗、基线、收益合同、候选状态和限制。
- 任何缺失原始文件必须写为 `unavailable`，不能用代理值冒充 exact reconstruction。

## 当前结论

V5 已可生成本地可追溯的申请包；托管 Standard CI 尚未就绪，因为其所需的历史研究产物目前被 `.gitignore` 排除且未被作为版本化 fixture 发布。
"""


def _etf_methodology(etf: dict[str, Any]) -> str:
    sectors = "、".join(item["sector_id"] for item in etf["sectors"])
    factors = "、".join(item["name"] for item in etf["signals"]["factors"])
    p = etf["portfolio"]
    return f"""# 个性化红利 ETF 式组合方法说明

## 定位

这是研究型、规则驱动的个性化红利 ETF 式组合方法，不是对任何商业 ETF 的复制、推荐或总回报比较。商业 ETF 仅可作为经济暴露背景；当前本地资料没有可追溯 NAV 加分红合同，因此不计算正式 ETF Alpha、Beta、信息比率或超额收益。

## 成分与分层

- 核心 sleeve：{sectors}。
- 行业角色：银行为金融价值与质量；其余 sleeve 为非金融现金流核心或候选。
- 因子库：{factors}。
- 银行使用行业覆写的资产质量和资本充足率字段；非金融行业保留经营现金流、估值与风险字段。

## 投资组合合同

- 目标持仓数：{p['target_count']}。
- 单行业上限：{p['sector_weight_cap']:.0%}；单股上限：{p['single_stock_weight_cap']:.0%}。
- 调仓频率：{p['rebalance_frequency']}。
- 权重：{p['weight_policy']}。
- 调仓日：各 sleeve 合法 PIT 信号日的并集；不以未来财报或事后行业表现调整权重。

## 研究边界

`{BASELINE}` 是冻结的正式基线。`{PRIMARY}` 仅在已选股票池内进行 sleeve 内权重治理，不新增股票、不跨 sleeve 转移，也不替代 V57f core。历史结果不能变成 ETF 产品承诺。
"""


def _pre2021_note(split: dict[str, Any], pre: dict[str, Any], pit: dict[str, Any]) -> str:
    return f"""# 2013-2021 早期样本：证据层级与方法边界

## 固定样本规则

{split['train_test_window']} 为研究和验证窗；{split['backtest_window']} 为冻结的正式回测窗。后者不用于因子发现或升级候选。

## 当前可主张的证据

1. 银行 V1-V4 是最完整的长样本领域案例，可作为黄金案例展示统计流程。
2. 多 sleeve 主线有一段有限的 pre-2021 proxy 验证：{pre['pre2021_validation_start']} 至 {pre['pre2021_validation_end']}。主线相对其 proxy baseline 的增量收益为 {pre['p1_delta_return_pct_points_vs_pre2021_baseline']:.4f} 个百分点，PM 结论是“支持 forward tracking，但未 accepted”。
3. 这不是完整的 2013-2021 exact V57f 重建，不能改写为独立验证通过。

## 不能主张的证据

- 已完成完整 multi-sleeve exact PIT 2013-2021 验证。
- 用后续年报、价格代理或未核对公司行为补成当时可见因子。
- 把 limited proxy validation 当作主候选升级依据。

## 原因

PIT 边界收口记录了 {pit['bank_genuine_disclosure_unavailable_count']} 条银行真实披露不可得项、{pit['infra_availability_registry_count']} 条基础设施可得性登记，以及 {pit['action_original_notice_evidence_count']} 条公司行为原始通知证据。PM 已将 exact reconstruction 标记为 unavailable。对研究生项目而言，这不是缺陷掩盖，而是数据可得性与因果/时间一致性纪律的直接证据。

## 后续研究设计

将“领域内完整银行案例”与“多行业组合的有限 early proxy 证据”分层呈现；未来只有在原始 PIT 原件齐备时，才重启 exact multi-sleeve early-window 检验。
"""


def _submission_outline() -> str:
    return """# 建议提交包结构

1. 两页项目简介：问题、方法、研究边界与主要贡献。
2. 中英摘要：`v5u_application_abstract_cn_en.md`。
3. 系统说明：四 agent 架构、数据/验证/工程流水线和治理门禁。
4. 黄金案例：银行多因子价值策略从假设到冻结证据包。
5. 行业扩展 scorecard：四核心 sleeve、煤炭/保险等拒绝或受限案例。
6. 个性化红利 ETF 式组合方法：规则、约束、非商业 ETF 比较边界。
7. V5t 历史研究与治理报告：作为可追溯附录，而不是收益宣传页。
8. 局限性：early PIT、严格现金 NAV、QMT 合同、ETF total-return 合同、前瞻纸面周期。

评审顺序应是“研究问题 -> 方法 -> 证据 -> 失败与限制 -> 可复现性”，而不是“先展示收益排名”。
"""


def _sector_scorecard() -> list[dict[str, str]]:
    return [
        {"sector": "银行", "role": "V1-V4 基础与 V57f 金融 sleeve", "financial_hypothesis": "低估、分红、资产质量、资本充足率与低波动", "evidence_level": "long-sample core case", "application_treatment": "黄金案例", "status": "formal research foundation; not an accepted live strategy"},
        {"sector": "电力公用事业", "role": "V57f 非金融现金流 core sleeve", "financial_hypothesis": "经营现金流、分红、低波动与需求状态", "evidence_level": "core sleeve with PIT limitations", "application_treatment": "行业扩展主案例", "status": "research evidence, not separate performance ranking"},
        {"sector": "高速基础设施", "role": "V57f 非金融现金流 core sleeve", "financial_hypothesis": "现金流、分红、capex 负担与经营纯度", "evidence_level": "core sleeve with early disclosure gaps", "application_treatment": "迁移性案例", "status": "exact pre-2021 reconstruction unavailable"},
        {"sector": "港口铁路基础设施", "role": "V57f 非金融现金流 core sleeve", "financial_hypothesis": "现金流价值、经营纯度与低波动", "evidence_level": "core sleeve with early disclosure gaps", "application_treatment": "迁移性案例", "status": "exact pre-2021 reconstruction unavailable"},
        {"sector": "煤炭", "role": "周期行业反例", "financial_hypothesis": "现金流与周期状态", "evidence_level": "rejected / data gated", "application_treatment": "展示拒绝机制", "status": "not a promotion candidate"},
        {"sector": "保险", "role": "金融相近行业反例", "financial_hypothesis": "低 PB、偿付能力、EV/NBV", "evidence_level": "partial PIT and small cross-section", "application_treatment": "展示小样本与字段限制", "status": "not a promotion candidate"},
    ]


def _golden_case_manifest(root: Path) -> list[dict[str, Any]]:
    paths = (
        "examples/bank_value_15y_strategy.json",
        "examples/bank_high_dividend_sustainability_v3_strategy.json",
        "docs/governance/bank_high_dividend_v3_research_validation_v1.md",
        "docs/governance/bank_high_dividend_v3_platform_replication_passed_v1.md",
        "config/v5_context.json",
        "v5_sample_split_governance_correction/current/v5_sample_split_rules.md",
    )
    return _manifest(root, paths, "bank_golden_case")


def _release_manifest(root: Path) -> list[dict[str, Any]]:
    return _manifest(root, REQUIRED, "application_release")


def _manifest(root: Path, paths: tuple[str, ...], purpose: str) -> list[dict[str, Any]]:
    head = _git(root, ["rev-parse", "HEAD"])
    status = _git(root, ["status", "--porcelain"])
    result = []
    for raw in paths:
        path = root / raw
        result.append({"purpose": purpose, "source_path": raw, "exists": path.exists(), "sha256": _sha(path) if path.exists() else "not_available", "git_head": head, "worktree_status_recorded_only": bool(status), "created_at_utc": _now()})
    return result


def _ci_readiness(root: Path) -> list[dict[str, str]]:
    tests = _json(root / "config/v5_test_tiers.json")
    status = _git(root, ["status", "--porcelain"])
    return [
        {"layer": "Fast", "local_entrypoint": "scripts/run_v5_tests.ps1 -Tier Fast", "test_module_count": str(len(tests["tiers"]["fast"])), "github_workflow": ".github/workflows/v5-fast-tests.yml", "status": "implemented"},
        {"layer": "Standard", "local_entrypoint": "scripts/run_v5_tests.ps1 -Tier Standard", "test_module_count": str(len(tests["tiers"]["standard"])), "github_workflow": "not_promoted", "status": "local_ready_hosted_ci_blocked_by_nonversioned_evidence_bundle"},
        {"layer": "Standard promotion prerequisite", "local_entrypoint": "freeze evidence-bundle SHA256 manifest and provide CI-readable fixture/artifact", "test_module_count": "n/a", "github_workflow": "add after artifact contract", "status": "required; current worktree status recorded" if status else "required; clean tree still needs fixture contract"},
    ]


def _blockers(pit: dict[str, Any], closure: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"blocker": "exact_pre2021_multisleeve_pit_unavailable", "effect": f"{pit['pm_gate_decision']}; no full exact 2013-2021 multi-sleeve reconstruction claim"},
        {"blocker": "strict_cash_nav_unavailable", "effect": "historical quantity/lot/cash/priority/fill/corporate-action state is incomplete"},
        {"blocker": "qmt_contract_incomplete", "effect": "historical submitted script/config/target/order/fill/position/cash chain is incomplete"},
        {"blocker": "ETF_total_return_contract_missing", "effect": "commercial ETF comparison remains economic-exposure context only"},
        {"blocker": "forward_paper_cycle_not_formed", "effect": "candidate cannot be called accepted or independently forward validated"},
    ]


def _pm_report(pre: dict[str, Any], pit: dict[str, Any], closure: dict[str, Any]) -> str:
    return f"""# V5u PM Application Readiness Report

## Completed

All seven application-enhancement components have been generated without changing a model, sample boundary, historical statistic or candidate status.

## Application readiness

The strongest story is an auditable research system anchored in a mature bank case, then tested for transferability across adjacent dividend sectors. The system's refusal to use future data or to promote unsupported branches is part of the contribution.

## Evidence boundary

The early multi-sleeve evidence is limited rather than exact: `{pit['pm_gate_decision']}`. The limited 2019-2020 proxy mainline result is {pre['p1_delta_return_pct_points_vs_pre2021_baseline']:.4f} percentage points relative to its proxy baseline, with no acceptance. Historical strict cash NAV is `{closure['strict_cash_nav_available']}` and QMT historical contract recovery is `{closure['qmt_contract_recovered']}`.

## Next presentation action

Use the project brief, bilingual abstract, scorecard and golden case as the main application narrative. Keep V5t and detailed CSVs as an evidence appendix. Do not add new models merely to make the application look broader.
"""


def _performance(root: Path) -> dict[str, dict[str, str]]:
    rows = _rows(root / "v5r_overall_research_governance_report_draft/current/v5r_performance_comparison_table.csv")
    chosen = {row["canonical_model_id"]: row for row in rows if row["canonical_model_id"] in {BASELINE, PRIMARY}}
    if set(chosen) != {BASELINE, PRIMARY}: raise ValueError("canonical performance pair missing")
    for row in chosen.values():
        if row["observations"] != "1228" or row["start_date"] != "2021-05-06" or row["end_date"] != "2026-05-29":
            raise ValueError("canonical comparison contract failed")
    return chosen


def _assert_inputs(root: Path) -> None:
    missing = [path for path in REQUIRED if not (root / path).exists()]
    if missing: raise FileNotFoundError("; ".join(missing))


def _json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
def _write_json(path: Path, value: Any) -> None: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _git(root: Path, args: list[str]) -> str:
    try: return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip() or "clean"
    except Exception: return "not_available"


if __name__ == "__main__": print(json.dumps(run_v5u_graduate_project_portfolio(), ensure_ascii=False, indent=2))
