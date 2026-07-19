from __future__ import annotations

from dataclasses import dataclass, field

from v5.spec import StrategySpec


@dataclass(frozen=True)
class AuditIssue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class AuditResult:
    issues: list[AuditIssue] = field(default_factory=list)

    @property
    def blocking_issues(self) -> list[AuditIssue]:
        return [issue for issue in self.issues if issue.severity == "blocker"]

    @property
    def warnings(self) -> list[AuditIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def passed(self) -> bool:
        return not self.blocking_issues

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "issues": [issue.__dict__ for issue in self.issues],
        }


def audit_strategy(spec: StrategySpec) -> AuditResult:
    issues: list[AuditIssue] = []
    raw = spec.raw

    if not raw["universe"].get("point_in_time"):
        issues.append(
            AuditIssue(
                "UNIVERSE_NOT_POINT_IN_TIME",
                "blocker",
                "Universe must be constructed point-in-time instead of using today's constituents for history.",
            )
        )

    safe_financial_as_of_policies = {
        "announcement_date",
        "report_publish_date",
        "trade_date_pit_get_fundamentals",
        "announcement_date_or_trade_date_lagged_by_factor",
        "original_announcement_visible_date",
    }
    if raw["data"].get("financial_as_of_policy") not in safe_financial_as_of_policies:
        issues.append(
            AuditIssue(
                "FINANCIAL_AS_OF_POLICY_UNSAFE",
                "blocker",
                "Financial data must use an announcement or publish date visibility policy.",
            )
        )

    for factor in spec.factors:
        safe_factor_as_of_policies = {
            "announcement_date",
            "report_publish_date",
            "trade_date_lagged",
            "operating_announcement_visible_date",
            "visible_report_segment_evidence",
            "reviewed_operating_visible_date",
            "trade_date_market_cap_and_latest_visible_ev",
            "latest_visible_report_announcement_date",
            "latest_visible_report_date",
        }
        if factor.as_of not in safe_factor_as_of_policies:
            issues.append(
                AuditIssue(
                    "FACTOR_AS_OF_UNSAFE",
                    "blocker",
                    f"Factor {factor.name} uses unsupported as_of policy: {factor.as_of}.",
                )
            )
        if factor.disclosure_lag_days == 0 and factor.source == "financial_statement":
            issues.append(
                AuditIssue(
                    "NO_FINANCIAL_DISCLOSURE_LAG",
                    "warning",
                    f"Factor {factor.name} has zero disclosure lag; confirm the vendor uses true announcement dates.",
                )
            )

    scoring_scope = raw["signals"]["scoring"].get("normalization_scope")
    if scoring_scope == "full_sample":
        issues.append(
            AuditIssue(
                "FULL_SAMPLE_NORMALIZATION",
                "blocker",
                "Factor normalization cannot use full-sample statistics.",
            )
        )

    validation = raw["validation"]
    if validation.get("method") != "rolling":
        issues.append(
            AuditIssue(
                "VALIDATION_NOT_ROLLING",
                "warning",
                "Rolling validation is recommended before accepting candidate strategies.",
            )
        )
    if int(validation.get("train_years", 0)) <= 0 or int(validation.get("test_years", 0)) <= 0:
        issues.append(
            AuditIssue(
                "INVALID_VALIDATION_WINDOW",
                "blocker",
                "Validation train_years and test_years must both be positive.",
            )
        )

    execution = raw["execution"]
    if float(execution.get("commission_bps", 0)) == 0 and float(execution.get("slippage_bps", 0)) == 0:
        issues.append(
            AuditIssue(
                "NO_TRADING_COSTS",
                "blocker",
                "Formal backtests must include commission or slippage assumptions.",
            )
        )
    if execution.get("suspension_policy") == "ignore":
        issues.append(
            AuditIssue(
                "SUSPENSIONS_IGNORED",
                "blocker",
                "Suspended securities cannot be ignored in executable backtests.",
            )
        )
    if execution.get("limit_policy") == "ignore":
        issues.append(
            AuditIssue(
                "PRICE_LIMITS_IGNORED",
                "blocker",
                "Limit-up and limit-down constraints cannot be ignored in executable backtests.",
            )
        )

    portfolio = raw["portfolio"]
    selection_count = int(portfolio["selection_count"])
    max_weight = float(portfolio["max_position_weight"])
    if selection_count * max_weight < 1:
        issues.append(
            AuditIssue(
                "MAX_WEIGHT_TOO_LOW",
                "blocker",
                "selection_count * max_position_weight is less than 100%, so the target portfolio cannot be fully invested.",
            )
        )

    return AuditResult(issues)
