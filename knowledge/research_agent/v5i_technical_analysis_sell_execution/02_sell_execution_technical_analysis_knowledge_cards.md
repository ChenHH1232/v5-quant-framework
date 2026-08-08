# V5i Sell-Execution Technical Analysis Knowledge Cards

Status: research cards, not rules
Data assumption: cleaned 1-minute OHLCV and amount only; features may be aggregated to 5-minute or 15-minute bars.

## Card 1: VWAP Position And Reversal

**Definition.** At timestamp `t`, observed intraday VWAP is cumulative amount divided by cumulative volume using bars through `t`. Price versus this VWAP is a relative execution-location feature, not an intrinsic value estimate.

**Why it can matter.** VWAP is a common execution benchmark. For a scheduled sell, price falling below observed VWAP after having traded above it can describe a loss of intraday relative strength. The relevant claim to test is only whether a fixed delayed or earlier execution has a better realized benchmark-relative price.

**PIT contract.** Use only cumulative amount and cumulative volume up to `t`; submit a hypothetical fill no earlier than the next executable bar. Do not use end-of-day VWAP, final daily volume, final daily high, or the close.

**What it cannot say.** A VWAP break is not proof of institutional selling, an order-flow imbalance, or a reason to create a new sell decision.

**Evidence status.** Feature and execution-benchmark rationale: medium to high. V5 sell-edge evidence: absent.

## Card 2: Intraday Trend Failure

**Definition.** A trend-failure state can be represented by a sequence of observed lower highs/lower lows, or a price cross below an observed short-horizon trend reference, after a prior positive intraday move.

**Why it can matter.** It may separate a scheduled sell occurring into continued strength from one occurring after local strength has faded. Its economic role is execution timing, not a forecast that the stock must fall.

**PIT contract.** The trend reference and all turning points must be computed from bars no later than `t`. A bar-cross signal may only lead to a fill in a subsequent bar. A single one-minute spike must be quality-flagged rather than treated as a robust trend break.

**What it cannot say.** It does not prove a trend reversal for the rest of the day or next day. It cannot convert a scheduled sell into an earlier discretionary exit without separate approval.

**Evidence status.** Formal algorithmic testing is supported by the technical-analysis literature; individual V5i application is untested.

## Card 3: High-So-Far Reversal

**Definition.** Use the maximum trade price observed from session open through `t`, not the eventual daily high. Measure the observed pullback from that high and optionally require a contemporaneous VWAP or amount-pressure condition.

**Why it can matter.** A scheduled sell may obtain a better local execution when a prior intraday rise has not yet materially reversed. The feature is a state descriptor for later evaluation.

**PIT contract.** `high_so_far(t)` must use only bars through `t`; the decision may fill at `t+1` or later. Do not label any event with the final daily high when building a live feature.

**What it cannot say.** It cannot identify a day top. A large observed pullback can be a temporary pause, and apparent performance can be dominated by a small number of volatile sessions.

**Evidence status.** Plausible execution hypothesis only. It needs pre-registered out-of-sample tests and must not be visually tuned.

## Card 4: Volume And Amount Confirmation

**Definition.** Use observed intensity and pressure measures such as last-15-minute amount divided by the elapsed-session average, and cumulative signed minute-return amount divided by cumulative amount through `t`.

**Why it can matter.** Price movement accompanied by unusual observed activity may be more informative for execution quality than price alone. V5h already records PIT-safe amount and volume pressure fields.

**PIT contract.** Seasonal baselines must be estimated only from prior dates available at the time. Full-day volume or amount share is hindsight and cannot enter a live condition. Volume and amount must be non-negative and session-aligned.

**What it cannot say.** Aggregate volume or amount does not reveal bid/ask depth, order-book imbalance, aggressive buyer/seller initiation, hidden liquidity, or the market impact of V5 order size.

**Evidence status.** Data availability and PIT implementation: high. Signed-order-flow interpretation: blocked without L2/trade-direction data.

## Card 5: RSI Or Oscillator Reversal

**Definition.** RSI is a bounded oscillator based on average gains and losses over a fixed trailing sequence of completed bars. A sell-execution diagnostic may study an observed decline from a locally elevated RSI rather than assume an absolute overbought number.

**Why it can matter.** It gives a compact representation of recent directional persistence and deceleration. Its primary value here is an interaction candidate with price versus VWAP and amount confirmation.

**PIT contract.** Calculate from closed bars available at `t`; use prior-session bars when the lookback crosses a session boundary; execute no earlier than the next bar. The lookback and aggregation level must be fixed before testing.

**What it cannot say.** RSI is not a fundamental valuation signal and not evidence that a price will reverse. A historically selected lookback or overbought cutoff would be a parameter scan.

**Evidence status.** Practitioner-defined feature, not V5 sell-edge evidence.

## Card 6: Classic Chart Patterns And MACD

**Definition.** Head-and-shoulders, flags, triangles, MACD crosses, and similar tools are descriptive pattern families. Their visual definitions are often ambiguous unless converted to deterministic algorithms.

**Why they are not elevated.** Published technical-analysis evidence is heterogeneous, sensitive to model choice and transaction costs, and classic pattern studies require formal definitions and statistical controls. A familiar chart name is not an economic mechanism.

**V5i treatment.** Do not place chart patterns or MACD in the V5i initial fixed feature set. They may be documented as future research only after an independent source card, deterministic definition, PIT contract, and separate PM approval.

**Evidence status.** Hypothesis generation only; blocked from initial V5i engineering.
