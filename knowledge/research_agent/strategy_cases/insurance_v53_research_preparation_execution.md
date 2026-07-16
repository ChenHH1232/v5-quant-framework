# Insurance V5.3 Research Preparation Execution

Date: 2026-07-16

Status:

```text
research_preparation_data_probe_completed_quant_blocked
```

## Research Memory

V5.3 Insurance can identify a small A-share insurance universe through JoinQuant/DataJQ industry membership, but the first data probe exposed two important gates.

## Gate 1: Universe Review

The first probe found 8 historical codes:

- `601318.XSHG`
- `601628.XSHG`
- `601601.XSHG`
- `601336.XSHG`
- `601319.XSHG`
- `000627.XSHE`
- `600291.XSHG`
- `002423.XSHE`

The first five are core insurance review candidates.

The last three require special handling:

- `000627.XSHE`: insurance-led holding / ST special case;
- `600291.XSHG`: delisted / historical P&C special case;
- `002423.XSHE`: likely financial holding contamination.

Research Agent must review company-report business exposure before formal PIT validation.

## Gate 2: Insurance-Specific Data

JoinQuant has:

```text
insurance_indicator
```

Useful fields include:

- earned premium;
- compensation ratio;
- comprehensive cost ratio;
- solvency adequacy ratio;
- net and total investment rate of return;
- investment assets;
- reserves;
- `pubDate`;
- `statDate`.

But the probe found:

```text
2024 coverage = 0 / 8
2025 coverage = 0 / 8
```

This must be repaired or explained before Quant Validation.

## Missing From First Probe

Not found in `insurance_indicator`:

- embedded value;
- new business value;
- P/EV;
- surrender / persistency;
- detailed channel quality.

These likely require annual-report/manual extraction or a vendor source with reviewed visible dates.

## PM Outcome

V5.3 is promising but not ready for formal validation.

Next required work:

1. review formal universe membership;
2. repair 2024-2025 insurance-specific data coverage;
3. decide whether EV / NBV are required for Test-1 or deferred;
4. build rate and equity-market state panel.

