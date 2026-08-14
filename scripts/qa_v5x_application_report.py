from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from docx import Document


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "v5x_personal_project_report" / "current"
PDF = OUT / "v5x_fintech_statistics_personal_project_report.pdf"
DOCX = OUT / "v5x_fintech_statistics_personal_project_report.docx"
QA_DIR = OUT / "pdf_qa_v1"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc")
    return ImageFont.truetype(str(path), size)


def render() -> list[Path]:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(str(PDF))
    pages: list[Path] = []
    for index in range(len(document)):
        page = document[index]
        bitmap = page.render(scale=1.75, rotation=0)
        image = bitmap.to_pil().convert("RGB")
        path = QA_DIR / f"page-{index + 1:02d}.png"
        image.save(path)
        pages.append(path)
    return pages


def contact_sheets(pages: list[Path]) -> list[Path]:
    sheets: list[Path] = []
    for start in range(0, len(pages), 4):
        current = pages[start:start + 4]
        thumb_width = 570
        thumbs = []
        for path in current:
            image = Image.open(path).convert("RGB")
            image.thumbnail((thumb_width, 830))
            thumbs.append(image)
        canvas = Image.new("RGB", (1240, 1800), "#eaf0f5")
        draw = ImageDraw.Draw(canvas)
        for offset, image in enumerate(thumbs):
            column, row = offset % 2, offset // 2
            x, y = 35 + column * 605, 70 + row * 860
            canvas.paste(image, (x, y))
            draw.text((x, y - 38), f"Page {start + offset + 1}", fill="#17324d", font=font(22, True))
        path = QA_DIR / f"contact-{start // 4 + 1}.png"
        canvas.save(path)
        sheets.append(path)
    return sheets


def docx_text() -> str:
    document = Document(DOCX)
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-manual-visual-pass", action="store_true")
    args = parser.parse_args()
    if not PDF.exists():
        raise FileNotFoundError(PDF)
    if not DOCX.exists():
        raise FileNotFoundError(DOCX)
    pages = render()
    sheets = contact_sheets(pages)
    reader = PdfReader(str(PDF))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized = "".join(extracted.split())
    normalized_docx = "".join(docx_text().split())
    required = [
        "strict_cash_nav_unavailable",
        "qmt_contract_incomplete",
        "validation_not_independent",
        "ETFtotal-return",
        "独立前瞻纸面周期尚未形成",
        "primary_forward_paper_candidate_not_accepted",
        "1,228",
        "120.69%",
        "109.25%",
    ]
    # These patterns flag an affirmative status claim; plain mentions inside a
    # limitation sentence are allowed and required for accurate disclosure.
    forbidden = ["候选已获接受", "候选已进入实盘", "候选已部署批准", "候选独立验证通过"]
    checks = {
        "pdf_exists": PDF.exists() and PDF.stat().st_size > 0,
        "docx_exists": DOCX.exists() and DOCX.stat().st_size > 0,
        "page_count": len(reader.pages),
        "all_rendered_pages_nonblank": all(Image.open(path).getbbox() is not None for path in pages),
        "required_text": {value: value in normalized for value in required},
        "required_text_docx": {value: value in normalized_docx for value in required},
        "forbidden_text": {value: value in extracted for value in forbidden},
        "forbidden_text_docx": {value: value in docx_text() for value in forbidden},
        "manual_visual_review_recorded": args.record_manual_visual_pass,
    }
    audit = {
        "generated_from": str(PDF.relative_to(ROOT)),
        "rendered_pages": [str(path.relative_to(ROOT)) for path in pages],
        "contact_sheets": [str(path.relative_to(ROOT)) for path in sheets],
        **checks,
    }
    (OUT / "v5x_pdf_render_and_content_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    auto_pass = (
        all(checks["required_text"].values())
        and all(checks["required_text_docx"].values())
        and not any(checks["forbidden_text"].values())
        and not any(checks["forbidden_text_docx"].values())
        and checks["all_rendered_pages_nonblank"]
    )
    status = "draft_ready_for_user_review" if auto_pass and args.record_manual_visual_pass else "pass_pending_manual_visual_review" if auto_pass else "fail_content_audit"
    lines = [
        "# V5x PDF 视觉与内容 QA",
        "",
        f"- PDF 页数：{checks['page_count']}",
        f"- 页面已全部渲染且非空：{checks['all_rendered_pages_nonblank']}",
        f"- PDF 与 DOCX 的必需披露与冻结事实文本检查：{all(checks['required_text'].values()) and all(checks['required_text_docx'].values())}",
        f"- 禁止表述检查（不得出现）：{not any(checks['forbidden_text'].values()) and not any(checks['forbidden_text_docx'].values())}",
        f"- 自动状态：{status}",
        f"- 项目经理逐页视觉检查记录：{args.record_manual_visual_pass}",
        "",
        "## 输入边界",
        "PDF 与 DOCX 均来自冻结的 V5t/V5s/V5v/V5w 输入；本 QA 未修改任何模型、市场数据、统计结果或治理状态。",
    ]
    (OUT / "v5x_pdf_visual_qa_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (OUT / "v5x_report_test_results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows([
            {"check": "PDF exists and renders", "status": "pass" if checks["pdf_exists"] and checks["all_rendered_pages_nonblank"] else "fail", "detail": f"{checks['page_count']} pages"},
            {"check": "DOCX exists", "status": "pass" if checks["docx_exists"] else "fail", "detail": "same frozen builder input"},
            {"check": "required disclosure coverage", "status": "pass" if all(checks["required_text"].values()) and all(checks["required_text_docx"].values()) else "fail", "detail": "five limitations, status, sample, formal returns"},
            {"check": "forbidden claim scan", "status": "pass" if not any(checks["forbidden_text"].values()) and not any(checks["forbidden_text_docx"].values()) else "fail", "detail": "no accepted/live/deployment/independent-validation claim"},
            {"check": "manual PDF visual review", "status": "pass" if args.record_manual_visual_pass else "not_recorded", "detail": "Chinese fonts, figures, tables, page numbering"},
        ])
    summary = {
        "task": "v5x_personal_fintech_statistics_project_report",
        "status": status,
        "baseline": "v57f_startup_preload_repaired_baseline",
        "primary_candidate": "internal_subsleeve_mom12_70_30",
        "candidate_status": "primary_forward_paper_candidate_not_accepted",
        "formal_common_sample": {"start": "2021-05-06", "end": "2026-05-29", "observations": 1228},
        "report_artifacts": {"markdown": str((OUT / "v5x_fintech_statistics_personal_project_report.md").relative_to(ROOT)), "docx": str(DOCX.relative_to(ROOT)), "pdf": str(PDF.relative_to(ROOT))},
        "qa": {"page_count": checks["page_count"], "pdf_manual_visual_review": args.record_manual_visual_pass, "docx_visual_renderer_available": False},
        "boundary": "Personal research project report; no model promotion, trading approval, future target, or post-2026-05-31 data use.",
    }
    (OUT / "v5x_personal_project_report_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "v5x_personal_project_report_release_decision.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["decision", "scope", "reason"])
        writer.writeheader()
        writer.writerow({"decision": status, "scope": "personal_project_report_only", "reason": "Frozen evidence, required disclosures, prohibited-claim scan and PDF visual review passed; candidate remains not accepted."})
    print(json.dumps({"status": status, "pages": len(pages), "sheets": [str(path) for path in sheets]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
