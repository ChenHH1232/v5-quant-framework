# V5c WeRead Exporter Ingestion Policy

## Purpose

This file records a practical route for filling the V5c book-note gap using `lbq110/weread-exporter`.

The route is for theory and discipline notes only. It does not reopen V5c Quant validation, does not modify V57f, and does not create accepted strategy rules.

## Tool Route

- Tool: `lbq110/weread-exporter`
- Location: `https://github.com/lbq110/weread-exporter`
- Reviewed date: `2026-08-01`
- Mechanism summary: the tool uses Playwright to open WeChat Reading in a browser session, captures Canvas-rendered text through a text-render hook, advances pages, and writes Markdown/raw chapter outputs locally.
- Required user action: user login / QR authorization and user-controlled book access.

## Allowed Use

Allowed:

- Export books or relevant chapters the user is permitted to read.
- Keep raw exports in a private ignored directory such as `research_reports/weread_private_raw/`.
- Convert relevant chapters into V5c theory cards.
- Store only chapter metadata, paraphrased notes, short compliant excerpts, and V5c relevance labels in the knowledge base.

Not allowed:

- Commit full-book Markdown, raw JSON, images, browser cookies, cache, or exported chapters to the V5 repo knowledge cards.
- Use book text as a direct quantitative threshold.
- Use book opinions as PIT market facts.
- Treat the GitHub tool itself as investment evidence.
- Mark any V5c/V5f/V5e model accepted because of book notes.

## Evidence Grade

Book notes generated through this route are C-level framework evidence.

They can support:

- investment discipline;
- behavioral guardrails;
- rebalancing language;
- risk-management framing;
- anti-overtrading principles;
- cash policy discussion.

They cannot support:

- accepted strategy status;
- live approval;
- threshold selection;
- parameter optimization;
- PIT financial facts;
- direct proof of future alpha.

## Ingestion Workflow

1. Export user-authorized source material outside the committed knowledge base.
2. Select only relevant chapters from the V5c book request list.
3. Create one note-card row per book/chapter/topic.
4. Prefer paraphrase over quotation.
5. Keep any direct excerpt short and local to the card.
6. Assign evidence grade `C`.
7. Mark `can_be_quant_hypothesis` as `no` unless the card only motivates a separately PIT-audited hypothesis.
8. Update source register and theory cards after manual review.

## Target Books From Existing Request

- `The Intelligent Investor / 聪明的投资者`
- `A Random Walk Down Wall Street / 漫步华尔街`
- `Thinking, Fast and Slow / 思考，快与慢`
- `The Most Important Thing / 投资最重要的事`
- `All About Asset Allocation`
- `The Intelligent Asset Allocator`
- `Expected Returns`
- `Adaptive Asset Allocation`
- `What Works on Wall Street`
- `The Little Book of Behavioral Investing`

## Current Status

`tool_route_recorded_notes_not_ingested`

No book notes have been imported yet. This file only closes the previous tooling ambiguity and defines the safe ingestion boundary.
