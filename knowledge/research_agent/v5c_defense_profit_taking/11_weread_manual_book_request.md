# WeChat Reading Manual Download / Notes Request

Purpose: these books are for V5c theory and discipline only. They cannot directly become strategy parameters.

## Priority 1: Must-Have Framework Books

1. **The Intelligent Investor / 聪明的投资者** - Benjamin Graham
   - Needed chapters: margin of safety, Mr. Market, defensive investor.
   - V5c use: discipline, valuation heat caution, no direct thresholds.

2. **A Random Walk Down Wall Street / 漫步华尔街** - Burton Malkiel
   - Needed chapters: market timing, index investing, behavioral pitfalls.
   - V5c use: anti-overtrading and anti-complex-timing guardrails.

3. **Thinking, Fast and Slow / 思考，快与慢** - Daniel Kahneman
   - Needed chapters: loss aversion, overconfidence, hindsight bias.
   - V5c use: explain why stop-profit and stop-loss rules overfit easily.

4. **The Most Important Thing / 投资最重要的事** - Howard Marks
   - Needed chapters: second-level thinking, risk, cycles, defensive investing.
   - V5c use: cycle/risk framing, not parameter rules.

## Priority 2: Asset Allocation / Rebalancing

5. **All About Asset Allocation** - Richard Ferri
   - Needed chapters: rebalancing, asset allocation policy, risk control.
   - V5c use: sleeve rebalancing and cash policy framework.

6. **The Intelligent Asset Allocator** - William Bernstein
   - Needed chapters: diversification, rebalancing, risk tolerance.
   - V5c use: risk-budget and rebalancing discipline.

7. **Expected Returns** - Antti Ilmanen
   - Needed chapters: value, carry, momentum, volatility, rebalancing.
   - V5c use: factor/asset class intuition; no direct strategy parameters.

8. **Adaptive Asset Allocation** - Adam Butler, Michael Philbrick, Rodrigo Gordillo
   - Needed chapters: momentum, volatility, correlation, adaptive allocation.
   - V5c use: hypothesis source for trend/volatility overlay; needs strict anti-overfit rules.

## Priority 3: Behavioral / Execution Discipline

9. **What Works on Wall Street** - James O'Shaughnessy
   - Needed chapters: factor discipline and long-horizon testing.
   - V5c use: why simple rules need robust validation.

10. **The Little Book of Behavioral Investing** - James Montier
   - Needed chapters: behavioral bias, patience, contrarian discipline.
   - V5c use: stop-profit and market-timing caution.

## What To Export For Each Book

- Book title and edition.
- Author.
- Chapter name.
- 5-10 short notes per relevant chapter.
- Original wording only as short excerpts; preferably your paraphrase.
- Why it matters for V5c.
- Whether it argues for defense, rebalancing, cash management, or behavioral discipline.

## How Research Agent Will Use Them

- C-level theory cards only.
- Can generate hypotheses.
- Cannot serve as factual proof.
- Cannot provide numeric thresholds.
- Cannot override PIT data and Quant validation.

## Optional Local Export Route Added 2026-08-01

The repository `lbq110/weread-exporter` may be used as a private local route to export books or chapter notes from a WeChat Reading account controlled by the user.

Governance boundaries:

- Use only books the user is permitted to read.
- Do not commit full-book Markdown, raw JSON, images, cache, browser profile, cookies or downloaded chapters into the V5 knowledge base.
- Raw exports should stay under an ignored/private workspace such as `research_reports/weread_private_raw/`.
- Only paraphrased notes, short compliant excerpts, chapter metadata and V5c relevance labels may enter knowledge cards.
- Book notes remain C-level theory/framework evidence only.
- They cannot provide thresholds, accepted rules, PIT facts or Quant validation.

Next ingestion files:

- `20_weread_exporter_ingestion_policy.md`
- `21_weread_book_note_card_template.csv`
- `22_weread_ingestion_status.csv`
