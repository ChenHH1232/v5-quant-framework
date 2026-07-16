from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from v5.scoring import validate_scoring_method


class SpecError(ValueError):
    """Raised when a strategy specification is malformed."""


@dataclass(frozen=True)
class FactorSpec:
    name: str
    source: str
    direction: str
    definition: str
    as_of: str
    disclosure_lag_days: int
    missing_policy: str
    winsorize: str | None = None
    normalize: str | None = None


@dataclass(frozen=True)
class StrategySpec:
    raw: dict[str, Any]

    @property
    def strategy_id(self) -> str:
        return str(self.raw["meta"]["strategy_id"])

    @property
    def factors(self) -> list[FactorSpec]:
        return [
            FactorSpec(
                name=str(item["name"]),
                source=str(item["source"]),
                direction=str(item["direction"]),
                definition=str(item["definition"]),
                as_of=str(item["as_of"]),
                disclosure_lag_days=int(item["disclosure_lag_days"]),
                missing_policy=str(item["missing_policy"]),
                winsorize=item.get("winsorize"),
                normalize=item.get("normalize"),
            )
            for item in self.raw["signals"]["factors"]
        ]


REQUIRED_TOP_LEVEL = [
    "meta",
    "universe",
    "data",
    "signals",
    "schedule",
    "portfolio",
    "risk",
    "validation",
    "execution",
    "outputs",
]

REQUIRED_FACTOR_FIELDS = [
    "name",
    "source",
    "direction",
    "definition",
    "as_of",
    "disclosure_lag_days",
    "missing_policy",
]


def parse_strategy_spec(raw: dict[str, Any]) -> StrategySpec:
    if not isinstance(raw, dict):
        raise SpecError("strategy spec must be a JSON object")

    missing = [field for field in REQUIRED_TOP_LEVEL if field not in raw]
    if missing:
        raise SpecError(f"missing top-level fields: {', '.join(missing)}")

    _require(raw["meta"], ["strategy_id", "name", "objective"], "meta")
    _require(raw["universe"], ["name", "construction", "point_in_time"], "universe")
    _require(raw["data"], ["vendor", "price_frequency", "financial_as_of_policy"], "data")
    _require(raw["signals"], ["factors", "scoring"], "signals")
    _require(raw["schedule"], ["signal_frequency", "rebalance_frequency"], "schedule")
    _require(raw["portfolio"], ["selection_count", "weighting", "max_position_weight"], "portfolio")
    _require(raw["risk"], ["defensive_asset", "defensive_rule"], "risk")
    _require(raw["validation"], ["method", "train_years", "test_years"], "validation")
    _require(raw["execution"], ["commission_bps", "slippage_bps", "suspension_policy", "limit_policy"], "execution")
    _require(raw["outputs"], ["save_holdings", "save_rebalance_signals", "report"], "outputs")

    factors = raw["signals"]["factors"]
    if not isinstance(factors, list) or not factors:
        raise SpecError("signals.factors must be a non-empty list")

    for index, factor in enumerate(factors):
        _require(factor, REQUIRED_FACTOR_FIELDS, f"signals.factors[{index}]")
        if factor["direction"] not in {"higher_is_better", "lower_is_better"}:
            raise SpecError(f"signals.factors[{index}].direction is invalid")
        if int(factor["disclosure_lag_days"]) < 0:
            raise SpecError(f"signals.factors[{index}].disclosure_lag_days cannot be negative")

    if int(raw["portfolio"]["selection_count"]) <= 0:
        raise SpecError("portfolio.selection_count must be positive")

    try:
        validate_scoring_method(raw)
    except ValueError as exc:
        raise SpecError(str(exc)) from exc

    max_weight = float(raw["portfolio"]["max_position_weight"])
    if max_weight <= 0 or max_weight > 1:
        raise SpecError("portfolio.max_position_weight must be within (0, 1]")

    return StrategySpec(raw=raw)


def _require(obj: Any, fields: list[str], path: str) -> None:
    if not isinstance(obj, dict):
        raise SpecError(f"{path} must be an object")
    missing = [field for field in fields if field not in obj]
    if missing:
        raise SpecError(f"missing fields in {path}: {', '.join(missing)}")
