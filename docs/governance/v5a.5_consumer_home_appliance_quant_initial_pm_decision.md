# V5a.5 Consumer / Home Appliance Initial Quant PM Decision

Date: 2026-07-21  
Layer: research_pit_validation  
Status: completed_initial_quant_pass_not_engineering_handoff  
Owner: Project Manager Agent

## Decision

V5a.5 completed the first data gate and initial formal validation for the second-pass consumer queue.

The PM decision is:

- `home_appliances_ocf_quality_v5a5b` is a promising research signal, but not yet an Engineering handoff.
- `food_beverage_ocf_low_vol_v5a5` is rejected as a composite hypothesis.
- `food_beverage_low_vol_diagnostic_v5a5b` is retained only as a defensive diagnostic, not a strategy candidate.
- `consumer_staples_ocf_low_vol_v5a5` is rejected as a broad parent-pool composite; it is too mixed for current ETF-sleeve construction.

No V5a.5 strategy is accepted, platform-ready or paper-trading-ready.

## Data Gate Result

PIT quarterly panels were built for five second-pass sectors:

| Sector | PIT rows | Dates | Codes | Status |
| --- | ---: | ---: | ---: | --- |
| Home appliances | 1687 | 20 | 101 | data gate passed |
| Food / beverage | 2290 | 20 | 135 | data gate passed |
| Consumer staples cash-flow | 5132 | 20 | 295 | data gate passed but pool too broad |
| Building materials / cement | 445 | 20 | 28 | data gate collected, cycle-state blocked |
| Pharma / medical services | 8704 | 20 | 490 | data gate collected, specialist-data blocked |

Real daily JoinQuant prices and low-volatility factors were also built for these sectors. Dividend files were not supplied at this stage, so V5a.5 remains a research validation layer rather than an Engineering daily-simulation layer.

## Initial Quant Result

### Home Appliances V5a.5

The initial `OCF + low-vol + dividend` composite produced strong headline performance, but ablation showed the composite was not clean:

- Equal-weight universe cumulative return: `49.62%`
- High OCF top 10: `86.43%`
- Low-volatility top 10: `51.92%`
- High-dividend top 10: `60.25%`
- Composite top 10: `92.03%`
- Dropping low-vol improved performance to `118.46%`
- Dropping dividend improved performance to `116.94%`

PM interpretation: the initial composite should not be accepted. Low-volatility and dividend are useful diagnostics or support variables, but they are not confirmed as positive scoring factors for this sector.

### Home Appliances V5a.5b

Research / Quant loop revised the hypothesis to an OCF-quality mainline:

- `operating_cash_flow_yield`
- `operating_cash_flow_to_net_profit`
- `capex_burden`

Validation result:

- Equal-weight universe cumulative return: `49.62%`
- High OCF top 10: `86.43%`
- V5a.5b OCF-quality top 10: `130.81%`
- PIT leakage audit: pass
- Rolling 2023: `24.84%`
- Rolling 2024: `31.88%`
- Rolling 2025: `11.15%`
- Rolling 2026: `-2.18%`

Ablation:

- Composite: `130.81%`
- Drop OCF yield: `77.30%`
- Drop OCF-to-net-profit: `108.47%`
- Drop capex_burden: `137.78%`

PM interpretation: OCF yield is the strongest confirmed contributor. OCF-to-net-profit is supportive. Capex burden is not confirmed as a positive scoring component and should be reviewed as a sector-specific risk / diagnostic variable before any Engineering handoff.

### Food / Beverage

Initial composite result:

- Equal-weight universe cumulative return: `-26.33%`
- High OCF top 10: `-5.95%`
- Low-volatility top 10: `13.80%`
- High-dividend top 10: `-6.00%`
- Composite: `-19.52%`

V5a.5b low-volatility diagnostic:

- Low-volatility top 10 cumulative return: `13.80%`
- Mean IC: `0.0493`
- Mean RankIC: `0.0811`
- Positive IC ratio: `57.89%`
- Rolling 2026: `-14.61%`

PM interpretation: the low-volatility signal exists as a defensive diagnostic, but the sector does not pass the current dividend / OCF / low-vol ETF-sleeve test. Food / beverage needs subsector separation, especially liquor vs non-liquor, plus channel inventory and working-capital state before another formal model attempt.

### Consumer Staples Parent Pool

Initial composite result:

- Equal-weight universe cumulative return: `-16.61%`
- High OCF top 10: `31.05%`
- Low-volatility top 10: `18.86%`
- High-dividend top 10: `23.34%`
- Composite: `7.93%`
- Dropping dividend improved performance to `37.15%`

PM interpretation: the broad parent pool is too mixed. It should not be used as an ETF sleeve without subsector routing.

## Agent Routing

| Candidate | PM status | Next agent | Allowed next action |
| --- | --- | --- | --- |
| Home appliances OCF quality | promising research signal | Research Agent | Add property / export / inventory / cash dividend data gate |
| Food / beverage low-vol diagnostic | observation only | Research Agent | Split subsectors and build channel / inventory state |
| Consumer staples parent pool | rejected current composite | Project Manager Agent | Route by subsector instead of broad parent |
| Cement | data collected but blocked | Research Agent | Add cement price / output / demand state |
| Pharma | data collected but blocked | Research Agent | Add subsector / policy / R&D state |

## Next Gate

The next queue item is not Engineering.

The correct next gate is:

1. Build Home Appliances V5a.5c data repair packet:
   - inventory pressure
   - property-cycle exposure
   - export exposure
   - cash dividend events
   - capex policy review
2. Rerun formal validation with OCF yield as the main factor and capex as a risk / diagnostic variable.
3. Only if that validation remains stable should Engineering Agent run local daily simulation, real dividend treatment and rebalance order health.

## Governance Note

The 2021-2026 window remains a platform-confirmation / reference window. It cannot be used as sole evidence for acceptance or for return-driven tuning.

