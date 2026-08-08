# V5 Atomic Commit And Push Prompt

## Objective

Publish the reproducible V5 research framework and its application-facing
governance evidence to the configured GitHub remote without adding raw market
data, source PDFs, minute-bar caches, logs, temporary QMT material, or rendered
QA pages.

## Commit 1: framework + tests

Stage `src/`, `tests/`, `config/`, `scripts/`, and `.github/`. This commit
contains deterministic runners, tests, configuration, local test entrypoints,
and the Fast CI workflow.

## Commit 2: research / knowledge workflows

Stage `knowledge/` and bounded agent workflow packets. These describe research
hypotheses, evidence collection, rejected ideas, and agent handoffs; they do
not contain downloaded source documents or credentials.

## Commit 3: governance + V5t/V5u application reports

Stage the sample-boundary correction, startup repair evidence, mainline
comparison evidence, PIT boundary records, V5k-V5u governance/report packets,
and the V5t archive PDF/DOCX. Exclude `pdf_pages/` render intermediates.

## Verification and push

Run Git whitespace checks and the existing Fast/Standard suites before or
immediately after staging. Confirm there are no literal credentials in staged
text. Push `main` to `origin`, including prior local commits. Record that raw
data and large binary sources remain intentionally local.
