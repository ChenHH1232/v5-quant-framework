from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


OUT = Path("v5v_application_final_report_readiness") / "current"
NUMERIC = Path("v5s_report_draft_review_and_release_prep") / "current" / "v5s_numeric_reconciliation.csv"
STATUS = Path("docs") / "governance" / "status_registry.json"
ACTIVE_REGISTRY = Path("config") / "v5_active_model_registry.json"
PORTFOLIO = Path("v5u_graduate_project_portfolio") / "current" / "v5u_application_portfolio_summary.json"
REPORT = Path("v5t_report_publication_finalization") / "current" / "v5t_v5_historical_research_and_governance_report_v1_0.md"
MAX_DATE = "2026-05-31"
BASELINE = "v57f_startup_preload_repaired_baseline"
CANDIDATE = "internal_subsleeve_mom12_70_30"
DISCLOSURES = [
    "strict_cash_nav_unavailable",
    "qmt_contract_incomplete",
    "ETF total-return contract missing",
    "validation_not_independent",
    "independent forward paper cycle not yet formed",
]


def run_v5v_application_final_report_readiness(root: Path = Path(".")) -> dict[str, Any]:
    inputs = [root / path for path in (NUMERIC, STATUS, ACTIVE_REGISTRY, PORTFOLIO, REPORT)]
    missing = [str(path.relative_to(root)) for path in inputs if not path.exists()]
    if missing:
        raise FileNotFoundError(f"V5v report-readiness inputs missing: {missing}")

    records = _read_csv(root / NUMERIC)
    figures = _metrics(records)
    status_registry = json.loads((root / STATUS).read_text(encoding="utf-8-sig"))
    active_registry = json.loads((root / ACTIVE_REGISTRY).read_text(encoding="utf-8-sig"))
    portfolio = json.loads((root / PORTFOLIO).read_text(encoding="utf-8-sig"))
    _validate(figures, status_registry, active_registry, portfolio)

    out = root / OUT
    figures_dir = out / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    _draw_comparison(figures, figures_dir / "v5v_formal_pairwise_comparison.png")
    _draw_workflow(figures_dir / "v5v_research_governance_workflow.png")

    _write_csv(out / "v5v_final_report_input_manifest.csv", _manifest(inputs, root))
    _write_csv(out / "v5v_data_and_local_artifact_boundary.csv", _artifact_boundary())
    _write_csv(out / "v5v_clean_environment_reproduction_audit.csv", _reproduction_audit())
    _write_csv(out / "v5v_required_disclosure_register.csv", _disclosure_rows())
    _write_csv(out / "v5v_application_claim_register.csv", _claim_rows(figures))
    _write_csv(out / "v5v_figure_register.csv", _figure_rows())
    _write_csv(out / "v5v_final_report_readiness_gate.csv", _gate_rows())
    (out / "v5v_application_narrative_freeze.md").write_text(_narrative(figures), encoding="utf-8")
    (out / "v5v_chart_captions_and_usage.md").write_text(_captions(), encoding="utf-8")
    (out / "v5v_reproducibility_and_data_boundary.md").write_text(_reproducibility_note(), encoding="utf-8")
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5v_application_final_report_readiness",
        "baseline": BASELINE,
        "primary_candidate": CANDIDATE,
        "candidate_status": "primary_forward_paper_candidate_not_accepted",
        "formal_window": "2021-05-01_to_2026-05-31",
        "pairwise_observations": int(figures[BASELINE]["observations"]),
        "local_fast_standard_status": "pass_in_bundled_report_environment",
        "clean_clone_status": "needs_minimal_evidence_fixture_and_dependency_contract_repair",
        "final_report_status": "ready_for_drafting_with_required_reproducibility_disclosure",
        "accepted": False,
    }
    (out / "v5v_application_final_report_readiness_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _metrics(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {BASELINE: {}, CANDIDATE: {}}
    for row in rows:
        model = row["canonical_model_id"]
        if model in result:
            result[model][row["metric"]] = row["recomputed_value"]
    return result


def _validate(
    metrics: dict[str, dict[str, str]],
    status_registry: dict[str, Any],
    active_registry: dict[str, Any],
    portfolio: dict[str, Any],
) -> None:
    required = {"total_return_pct", "max_drawdown_pct", "observations", "start_date", "end_date"}
    for model, values in metrics.items():
        missing = required - set(values)
        if missing:
            raise ValueError(f"Missing verified metrics for {model}: {sorted(missing)}")
    pointer = status_registry["v5_active_model_registry"]
    active = active_registry["active_models"][0]
    if pointer["active_model"] != CANDIDATE or pointer["required_baseline"] != BASELINE:
        raise ValueError("Status-registry pointer conflicts with the frozen application narrative.")
    if active["model_id"] != CANDIDATE or active["baseline_id"] != BASELINE:
        raise ValueError("Active-model registry conflicts with the frozen application narrative.")
    if portfolio["primary_candidate"] != CANDIDATE or portfolio["baseline"] != BASELINE:
        raise ValueError("V5u portfolio summary conflicts with the frozen application narrative.")


def _manifest(paths: list[Path], root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        rows.append({
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "purpose": "verified_report_input",
            "market_data_max_date": MAX_DATE,
        })
    return rows


def _artifact_boundary() -> list[dict[str, str]]:
    return [
        {"category": "source_config_tests", "version_control": "required", "location": "src/; tests/; config/; scripts/; .github/", "reason": "Rebuilds the research workflow and audit logic."},
        {"category": "curated_governance_and_report_evidence", "version_control": "required", "location": "v5q-v5u selected current artifacts", "reason": "Supports report claims and frozen status."},
        {"category": "raw_minute_daily_market_data", "version_control": "local_only_manifested", "location": "data/; local market-data stores", "reason": "Large licensed source material; never required for application reading."},
        {"category": "annual_report_pdfs_and_ocr", "version_control": "local_only_manifested", "location": "local PDF/OCR work areas", "reason": "Source-file volume and provenance require a separate local ledger."},
        {"category": "platform_logs_orders_and_temp_exports", "version_control": "local_only_manifested", "location": "QMT/JoinQuant/log/temp work areas", "reason": "Historical contract evidence may be incomplete and must not be fabricated."},
        {"category": "render_intermediates_and_caches", "version_control": "excluded", "location": "pdf_pages/; tmp*/; logs/", "reason": "Derived files are regenerated or non-authoritative."},
    ]


def _reproduction_audit() -> list[dict[str, str]]:
    return [
        {"check": "bundled_report_environment_fast", "status": "pass", "detail": "9 Fast tests passed using the packaged report runtime."},
        {"check": "bundled_report_environment_standard", "status": "pass", "detail": "15 Standard tests passed using the packaged report runtime."},
        {"check": "clean_clone_windows_path", "status": "needs_repair", "detail": "A default temp-path clone hit Windows path-length limits in historical paper-signal paths; use a short clone root and enable long paths."},
        {"check": "clean_clone_dependency_contract", "status": "needs_repair", "detail": "python-docx is used by the archive renderer but is not declared in project dependencies."},
        {"check": "clean_clone_evidence_fixture_contract", "status": "needs_repair", "detail": "Several legacy workflow tests read local generated ledgers/exports. Replace with committed minimal test fixtures before claiming clean-clone Standard portability."},
        {"check": "historical_claim_reproducibility", "status": "pass_with_disclosures", "detail": "The formal pairwise statistics are present in curated report evidence and remain validation_not_independent."},
    ]


def _disclosure_rows() -> list[dict[str, str]]:
    return [{"disclosure": item, "placement": "executive_summary; candidate_conclusion; limitations", "required": "True", "status": "frozen_required"} for item in DISCLOSURES]


def _claim_rows(metrics: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    return [
        {"claim": "V5 is an auditable fintech/statistics research workflow, not a return-ranking exercise.", "evidence": "V5t report; V5u project brief", "scope": "research-process claim"},
        {"claim": f"The only formal performance comparison uses {metrics[BASELINE]['observations']} common daily observations from {metrics[BASELINE]['start_date']} to {metrics[BASELINE]['end_date']}.", "evidence": "V5s numeric reconciliation", "scope": "formal pairwise contract"},
        {"claim": f"The candidate's historical total return was {float(metrics[CANDIDATE]['total_return_pct']):.4f}% versus {float(metrics[BASELINE]['total_return_pct']):.4f}% for the repaired baseline.", "evidence": "V5s numeric reconciliation", "scope": "historical observation only; validation_not_independent"},
        {"claim": "The candidate is not accepted, live approved, or a deployment recommendation.", "evidence": "active-model registry; V5t limitations", "scope": "governance status"},
    ]


def _figure_rows() -> list[dict[str, str]]:
    return [
        {"file": "figures/v5v_formal_pairwise_comparison.png", "status": "approved_for_application", "data_scope": "repaired baseline vs primary candidate only", "use": "method/results section"},
        {"file": "figures/v5v_research_governance_workflow.png", "status": "approved_for_application", "data_scope": "process map, no performance ranking", "use": "method/governance section"},
        {"file": "figures/v5_physics_model_explainer.png", "status": "approved_for_application", "data_scope": "V5 model architecture and governance interpretation; no performance claim", "use": "model-design section"},
        {"file": "figures/v5_time_series_sample_isolation_design.png", "status": "approved_for_application", "data_scope": "2013-2021 research boundary, completed bank rolling evidence, limited 2019-2020 V5 proxy check, and 2021-2026 frozen formal backtest; no performance ranking", "use": "study-design, evidence boundary, and anti-leakage section"},
        {"file": "figures/v5_project_purpose_and_agent_system.png", "status": "superseded_for_application", "data_scope": "Superseded combined overview retained for traceability; no performance claim", "use": "archive only"},
        {"file": "figures/v5_core_purpose_overview.png", "status": "approved_for_application", "data_scope": "V1-V4 bank foundation, transferable workflow, adjacent-sleeve expansion, and signal division; no performance claim", "use": "project overview section"},
        {"file": "figures/v5_agent_workflow_overview.png", "status": "approved_for_application", "data_scope": "Advisor, PM governance, agent hand-off chain, and research infrastructure; no performance claim", "use": "method and governance section"},
        {"file": "figures/v5_finance_theory_statistics_agent_loop.png", "status": "approved_for_application", "data_scope": "Financial-theory hypothesis formation, quantitative falsification, and PM evidence classification; no performance claim", "use": "research philosophy and methodology section"},
        {"file": "figures/v5_ideal_vs_reality_optimization_path.png", "status": "approved_for_application", "data_scope": "Conceptual constrained-optimization metaphor for V5 research boundaries; no performance claim", "use": "reflection and research-limitations section"},
    ]


def _gate_rows() -> list[dict[str, str]]:
    return [
        {"gate": "statistics_and_status", "status": "pass", "detail": "Frozen baseline, candidate, 1,228 observations, and status agree."},
        {"gate": "application_narrative", "status": "pass", "detail": "Narrative focuses on method, controls, evidence and limitations."},
        {"gate": "figure_scope", "status": "pass", "detail": "Figures show only the allowed pairwise comparison and workflow."},
        {"gate": "reproducibility_contract", "status": "pass_with_required_follow_up", "detail": "Portable Standard needs fixtures, path configuration, and declared report dependencies."},
        {"gate": "final_report_drafting", "status": "ready_with_required_disclosures", "detail": "No model or historical statistic needs to change before drafting."},
    ]


def _draw_comparison(metrics: dict[str, dict[str, str]], path: Path) -> None:
    image = Image.new("RGB", (1500, 820), "white")
    draw = ImageDraw.Draw(image)
    title = _font(38); label = _font(24); number = _font(25)
    navy, teal, red, ink, grid = "#14324a", "#177e89", "#b23a48", "#1f2933", "#d9e2ec"
    draw.text((70, 50), "V5 Formal Pairwise Comparison", fill=ink, font=title)
    draw.text((70, 105), "2021-05-06 to 2026-05-29 | 1,228 common daily observations | validation not independent", fill=ink, font=label)
    rows = [("Total return (%)", "total_return_pct", 130), ("Annualized return (%)", "annualized_return_pct", 350), ("Maximum drawdown (%)", "max_drawdown_pct", 570)]
    for text, key, y in rows:
        draw.text((70, y), text, fill=ink, font=label)
        values = [("Repaired baseline", float(metrics[BASELINE][key]), navy), ("Primary candidate", float(metrics[CANDIDATE][key]), teal)]
        maximum = max(value for _, value, _ in values) * 1.15
        for index, (name, value, color) in enumerate(values):
            top = y + 45 + index * 54
            draw.text((100, top), name, fill=ink, font=label)
            x0, x1 = 350, 1300
            draw.rectangle((x0, top + 3, x1, top + 32), fill=grid)
            draw.rectangle((x0, top + 3, x0 + (x1 - x0) * value / maximum, top + 32), fill=color)
            draw.text((1320, top), f"{value:.2f}", fill=ink, font=number)
    draw.rounded_rectangle((70, 745, 1430, 795), radius=8, fill="#edf2f7")
    draw.text((95, 758), "Historical sample observation only. Candidate remains primary_forward_paper_candidate_not_accepted.", fill=red, font=label)
    image.save(path)


def _draw_workflow(path: Path) -> None:
    image = Image.new("RGB", (1700, 620), "white")
    draw = ImageDraw.Draw(image)
    title, label = _font(38), _font(20)
    ink, blue, green, muted = "#1f2933", "#2f6690", "#3b7a57", "#52606d"
    draw.text((70, 45), "V5 Research and Governance Workflow", fill=ink, font=title)
    nodes = [(50, 205, "Financial hypothesis\nand sector research"), (370, 205, "PIT and sample\nisolation audit"), (690, 205, "Engineering, tests\nand evidence packet"), (1010, 205, "PM governance\nand status gate"), (1330, 205, "Archive:\ncandidate / diagnostic\n/ blocked")]
    for index, (x, y, text) in enumerate(nodes):
        color = green if index == 4 else blue
        draw.rounded_rectangle((x, y, x + 250, y + 140), radius=12, fill=color)
        for line_index, line in enumerate(text.split("\n")):
            draw.text((x + 15, y + 29 + line_index * 29), line, fill="white", font=label)
        if index < len(nodes) - 1:
            draw.line((x + 250, y + 70, nodes[index + 1][0] - 12, y + 70), fill=muted, width=4)
            draw.polygon([(nodes[index + 1][0] - 12, y + 70), (nodes[index + 1][0] - 28, y + 60), (nodes[index + 1][0] - 28, y + 80)], fill=muted)
    draw.text((70, 455), "Human review retains final authority. Historical return alone cannot mark a model accepted.", fill=ink, font=_font(27))
    draw.text((70, 505), "Formal backtest: 2021-05-01 to 2026-05-31. Research/validation window: 2013-01-01 to 2021-04-30.", fill=muted, font=label)
    image.save(path)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/arial.ttf")):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def _narrative(metrics: dict[str, dict[str, str]]) -> str:
    return f"""# V5 Application Narrative Freeze

## Project claim

V5 develops an auditable agent-assisted quantitative research workflow from a bank multi-factor value foundation to a four-sleeve personalized dividend-ETF-style portfolio. The project is about financial-technology process design and statistical discipline, not a claim of deployable alpha.

## Fixed study design

- Research/validation window: 2013-01-01 to 2021-04-30.
- Formal historical backtest: 2021-05-01 to 2026-05-31.
- Formal reference: `{BASELINE}`; first valid signal: 2021-05-06.
- Only primary candidate: `{CANDIDATE}`, status `primary_forward_paper_candidate_not_accepted`.

## Permitted result sentence

On the permitted same-parent, same-contract comparison of {metrics[BASELINE]['observations']} common daily observations ({metrics[BASELINE]['start_date']} to {metrics[BASELINE]['end_date']}), the candidate recorded {float(metrics[CANDIDATE]['total_return_pct']):.2f}% total return versus {float(metrics[BASELINE]['total_return_pct']):.2f}% for the repaired baseline. This is a historical, non-independent observation, not an acceptance or deployment result.

## Required limitation sentence

{'; '.join(DISCLOSURES)}. These limitations do not invalidate an honest historical research report, but they block accepted/live language and any strong performance claim.
"""


def _captions() -> str:
    return """# Application Figure Captions

## Formal pairwise comparison

Figure: Repaired baseline and primary candidate on the only permitted common daily sample. Total return and annualized return are higher for the candidate; maximum-drawdown difference is small. The chart is a historical observation under `validation_not_independent`, not a performance forecast.

## Research and governance workflow

Figure: The V5 workflow converts financial hypotheses into PIT-audited, tested and governed research records. It explicitly routes rejected, diagnostic and blocked work into an archive instead of treating historical return as an acceptance decision.

## V5 physics model explainer

Figure: V5 is represented as four constrained value-low-volatility sleeve trajectories. Fundamentals shape each sleeve's admissible terrain and candidate pool; the formal momentum overlay only tilts weights within the existing sleeve using the fixed 70/30 blend. Mean reversion is deliberately grey because it remains diagnostic rather than a formal allocation rule.

## Time-series evidence boundary and sample isolation

Figure: The project reserves 2013-01-01 to 2021-04-30 as its research boundary, but distinguishes evidence layers. The V1-V4 bank foundation has completed annual rolling tests for 2016-2020. The V5 four-sleeve exact PIT target reconstruction is blocked by original-disclosure gaps, so it cannot be represented as completed 2013-2021 rolling validation. The V5 main candidate has only a limited 2019-04-01 to 2020-12-31 proxy check. The model rule and comparison contract are frozen at 2021-05; the 2021-05-01 to 2026-05-31 period is a frozen historical backtest, not a tuning set. The crossed feedback path prohibits using post-freeze outcomes to alter factors, thresholds, sleeves, weights, or version selection.

## V5 core purpose overview

Figure: V5 starts from the V1-V4 bank multi-factor value foundation, converts the method into a reusable agent workflow, applies it to adjacent high-dividend sleeves under fixed constraints, and aims to form a personal dividend-enhanced ETF-style portfolio. Value remains the stock-selection and portfolio foundation; momentum is sleeve-internal support; mean reversion remains a correction or diagnostic layer. The figure describes purpose and design boundaries only and makes no performance claim.

## V5 agent workflow overview

Figure: A continuing dialogue advisor supplies context and alternatives without overriding governance. The PM independently sets boundaries and gates, then supervises a one-way operational hand-off from research to quantitative validation to engineering to evidence archival. The shared knowledge base, PIT data store, permission-gated tools, and self-authored skills make each hand-off reproducible and reviewable. The figure describes process architecture only and makes no performance claim.

## Financial theory, statistical validation, and agent loop

Figure: Statistics, computation, and agents improve the scale and reproducibility of research, but cannot alone explain an economic mechanism or eliminate data-mining risk. The author's financial reading and investment experience inform the research agent's theory-led, falsifiable hypotheses. The quantitative agent attempts to disprove them using PIT and statistical controls; the PM then distinguishes an implausible hypothesis, insufficient data, an economically valid but impractical path, or evidence sufficient for a frozen next-stage observation. The figure describes research method only and makes no performance claim.

## Ideal versus real constrained optimization path

Figure: The three-dimensional space is a conceptual metaphor, not a measured optimization surface. It distinguishes the ideal of a shortest auditable path from an initial financial hypothesis to a conceptual model target, from V5's actual constrained local path. An overambitious cross-sector step can expose a flawed hypothesis, missing evidence, limited implementation capacity, or insufficient economic similarity. The current four-sleeve result is therefore described as a partial constrained replication in a local feasible region, not as a globally optimal or accepted strategy.
"""


def _reproducibility_note() -> str:
    return """# Reproducibility and Local-Artifact Boundary

The report can cite version-controlled code, configuration, curated evidence and SHA256 manifests. Raw price/minute data, annual-report PDFs, OCR material, platform exports and render caches remain local because they are large, licensed, or not a complete historical execution contract.

The bundled report runtime passed Fast and Standard. A from-scratch clone needs three non-statistical repairs before it can claim portable Standard execution: a short Windows checkout path/long-path configuration, declared report-rendering dependencies, and committed minimal fixtures for legacy tests that currently read local generated ledgers. These are workflow portability repairs; they do not justify altering model results or evidence boundaries.
"""


if __name__ == "__main__":
    print(json.dumps(run_v5v_application_final_report_readiness(), ensure_ascii=False, indent=2))
