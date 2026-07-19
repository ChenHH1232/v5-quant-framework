# V5.8 Telecom Small-Sample Sleeve Policy V1

Date: 2026-07-19

Owner:

```text
Project Manager Agent
```

Scope:

```text
telecom_operators
```

## Purpose

Telecom operators fit the dividend, cash-flow and low-volatility direction, but the A-share core universe has only three names:

```text
600050.XSHG China Unicom
601728.XSHG China Telecom
600941.XSHG China Mobile
```

This policy prevents the V5 workflow from treating a three-stock universe as if it were a normal cross-sectional sector strategy.

## PM Classification

Approved classification:

```text
small_sample_observation_sleeve
basket_diagnostic_only
not_standalone_strategy
```

Not approved:

```text
formal_strategy_candidate
accepted_strategy
engineering_handoff
joinquant_strategy_code
```

## Rules

1. Telecom must not be accepted under broad IC / RankIC standards.
2. Telecom may be used only as a basket-level observation sleeve unless PM explicitly approves a specialist sample policy.
3. Standalone historical return is not acceptance evidence.
4. A single-stock or two-stock selection result must be treated as concentration evidence, not factor robustness evidence.
5. Any future handoff must evaluate telecom by contribution to a diversified dividend low-volatility cash-flow basket.

## Allowed Work

Allowed next actions:

```text
basket_level_contribution_test
paper_observation_signal_log
specialist_operating_data_repair
leave_one_name_out_diagnostic
concentration_cap_test
```

Required specialist inputs before any local daily simulation:

```text
real daily open / close prices
cash dividends with visible dates
ARPU and subscriber count evidence
capex cycle evidence
EBITDA margin or operating margin evidence
enterprise-service revenue mix
operator business-purity evidence
```

## Acceptance Gate

Telecom can only advance from observation sleeve if all conditions below are met:

```text
PIT data gate passed
specialist operating data gate passed
basket contribution is positive after sector and single-name caps
leave-one-name-out result does not collapse
2026 weakness is explained ex ante or bounded by risk rules
PM approves specialist sleeve policy
```

## Stop Rule

Stop standalone telecom modeling if two consecutive loops add no new specialist evidence or if results depend mainly on one stock.

Restart condition:

```text
multi-year PIT operating indicators are added and telecom is evaluated as a capped basket sleeve, not as a standalone stock-picking strategy.
```

