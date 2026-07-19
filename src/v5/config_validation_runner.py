from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from v5.engine import validate_spec_file
from v5.scoring import SUPPORTED_SCORING_METHODS


def validate_config_file(path: Path) -> dict[str, Any]:
    raw = _read_json(path)
    config_type = detect_config_type(raw)
    if config_type == "legacy_strategy_spec":
        result = validate_spec_file(path)
        result["config_type"] = config_type
        return result

    issues = _validate_by_type(config_type, raw)
    return {
        "path": str(path),
        "config_type": config_type,
        "identifier": _identifier(raw, config_type),
        "audit": {
            "passed": not any(issue["severity"] == "blocker" for issue in issues),
            "issues": issues,
        },
    }


def detect_config_type(raw: dict[str, Any]) -> str:
    if not isinstance(raw, dict):
        return "unknown_json"
    if "protocol_id" in raw and "action_classes" in raw and "stop_rules" in raw:
        return "agent_operating_protocol"
    if "strategies" in raw and "governance_rule" in raw:
        return "status_registry"
    if "project" in raw and "lane_policy" in raw and "timebox_policy" in raw:
        return "sector_replication_roadmap_config"
    if "project" in raw and "candidate_sectors" in raw:
        return "sector_screening_config"
    if "project" in raw and "sectors" in raw and "signals" in raw and "portfolio" in raw:
        return "basket_runtime_config"
    if _has_legacy_strategy_shape(raw):
        return "legacy_strategy_spec"
    if "meta" in raw and "signals" in raw and "portfolio" in raw and "validation" in raw:
        return "research_candidate_spec"
    if "project" in raw and ("mission" in raw or "core_thesis" in raw):
        return "project_context"
    return "unknown_json"


def _validate_by_type(config_type: str, raw: dict[str, Any]) -> list[dict[str, str]]:
    if config_type == "basket_runtime_config":
        return _validate_basket_runtime_config(raw)
    if config_type == "research_candidate_spec":
        return _validate_research_candidate_spec(raw)
    if config_type == "sector_screening_config":
        return _validate_sector_screening_config(raw)
    if config_type == "sector_replication_roadmap_config":
        return _validate_sector_replication_roadmap_config(raw)
    if config_type == "agent_operating_protocol":
        return _validate_agent_protocol(raw)
    if config_type == "status_registry":
        return _validate_status_registry_shape(raw)
    if config_type == "project_context":
        return _validate_project_context(raw)
    return [_issue("UNKNOWN_CONFIG_TYPE", "blocker", "JSON shape is not recognized by the V5 validation router.")]


def _validate_basket_runtime_config(raw: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    _require(raw, ["schema_version", "project", "sectors", "signals", "portfolio"], "root", issues)
    sectors = raw.get("sectors")
    if not isinstance(sectors, list) or not sectors:
        issues.append(_issue("BASKET_SECTORS_EMPTY", "blocker", "basket_runtime_config.sectors must be a non-empty list."))
    else:
        for index, sector in enumerate(sectors):
            _require(sector, ["sector_id", "strategy_id", "panel_csv", "price_csv", "dividend_csv"], f"sectors[{index}]", issues)
    issues.extend(_validate_scoring(raw))
    portfolio = raw.get("portfolio", {})
    if int(portfolio.get("target_count") or portfolio.get("selection_count") or 0) <= 0:
        issues.append(_issue("BASKET_TARGET_COUNT_INVALID", "blocker", "basket target_count or selection_count must be positive."))
    return issues


def _validate_research_candidate_spec(raw: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    _require(raw, ["meta", "signals", "portfolio", "validation", "execution"], "root", issues)
    _require(raw.get("meta"), ["strategy_id", "name", "objective"], "meta", issues)
    factors = raw.get("signals", {}).get("factors")
    if not isinstance(factors, list) or not factors:
        issues.append(_issue("FACTORS_EMPTY", "blocker", "signals.factors must be a non-empty list."))
    else:
        for index, factor in enumerate(factors):
            _require(factor, ["name", "direction"], f"signals.factors[{index}]", issues)
            if factor.get("direction") not in {"higher_is_better", "lower_is_better"}:
                issues.append(_issue("FACTOR_DIRECTION_INVALID", "blocker", f"signals.factors[{index}].direction is invalid."))
            as_of = factor.get("as_of")
            if as_of and as_of not in {"announcement_date", "report_publish_date", "trade_date_lagged"}:
                issues.append(_issue("FACTOR_AS_OF_REVIEW", "warning", f"signals.factors[{index}].as_of uses a non-standard policy: {as_of}."))
    issues.extend(_validate_scoring(raw))
    if not raw.get("data", {}).get("financial_as_of_policy"):
        issues.append(_issue("FINANCIAL_AS_OF_POLICY_MISSING", "warning", "research candidate does not declare data.financial_as_of_policy."))
    return issues


def _validate_sector_screening_config(raw: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    _require(raw, ["schema_version", "project", "experiment_layer", "candidate_sectors"], "root", issues)
    sectors = raw.get("candidate_sectors")
    if not isinstance(sectors, list) or not sectors:
        issues.append(_issue("CANDIDATE_SECTORS_EMPTY", "blocker", "candidate_sectors must be a non-empty list."))
        return issues
    for index, sector in enumerate(sectors):
        _require(
            sector,
            [
                "sector_id",
                "display_name",
                "basket_role",
                "data_gate",
                "pit_universe_gate",
                "business_purity_gate",
                "dividend_gate",
                "fcf_gate",
                "low_vol_gate",
            ],
            f"candidate_sectors[{index}]",
            issues,
        )
    return issues


def _validate_sector_replication_roadmap_config(raw: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    _require(raw, ["schema_version", "project", "experiment_layer", "source_sector_config", "timebox_policy", "lane_policy"], "root", issues)
    timebox = raw.get("timebox_policy", {})
    if int(timebox.get("default_minutes") or 0) <= 0:
        issues.append(_issue("TIMEBOX_INVALID", "blocker", "timebox_policy.default_minutes must be positive."))
    lane_policy = raw.get("lane_policy")
    if not isinstance(lane_policy, dict) or not lane_policy:
        issues.append(_issue("LANE_POLICY_EMPTY", "blocker", "lane_policy must be a non-empty object."))
    else:
        for lane_id, lane in lane_policy.items():
            _require(lane, ["next_agent", "timebox_minutes", "required_packet", "allowed_next_action", "forbidden_action"], f"lane_policy.{lane_id}", issues)
    return issues


def _validate_agent_protocol(raw: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    _require(raw, ["protocol_id", "default_timebox_minutes", "action_classes", "stop_rules", "allowed_pm_decisions"], "root", issues)
    if int(raw.get("default_timebox_minutes") or 0) <= 0:
        issues.append(_issue("TIMEBOX_INVALID", "blocker", "default_timebox_minutes must be positive."))
    return issues


def _validate_status_registry_shape(raw: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    _require(raw, ["schema_version", "updated_at", "governance_rule", "strategies"], "root", issues)
    strategies = raw.get("strategies")
    if not isinstance(strategies, list) or not strategies:
        issues.append(_issue("REGISTRY_STRATEGIES_EMPTY", "blocker", "status registry strategies must be a non-empty list."))
    return issues


def _validate_project_context(raw: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    _require(raw, ["project", "mission"], "root", issues)
    return issues


def _validate_scoring(raw: dict[str, Any]) -> list[dict[str, str]]:
    scoring = raw.get("signals", {}).get("scoring", {})
    method = str(scoring.get("method") or "weighted_composite")
    if method not in SUPPORTED_SCORING_METHODS:
        supported = ", ".join(sorted(SUPPORTED_SCORING_METHODS))
        return [_issue("SCORING_METHOD_UNSUPPORTED", "blocker", f"unsupported scoring.method '{method}'. Supported methods: {supported}")]
    return []


def _has_legacy_strategy_shape(raw: dict[str, Any]) -> bool:
    required = {"meta", "universe", "data", "signals", "schedule", "portfolio", "risk", "validation", "execution", "outputs"}
    if not required.issubset(raw):
        return False
    nested_required = {
        "schedule": ["signal_frequency", "rebalance_frequency"],
        "portfolio": ["selection_count", "weighting", "max_position_weight"],
        "validation": ["method", "train_years", "test_years"],
        "execution": ["commission_bps", "slippage_bps", "suspension_policy", "limit_policy"],
        "outputs": ["save_holdings", "save_rebalance_signals", "report"],
    }
    for key, fields in nested_required.items():
        value = raw.get(key)
        if not isinstance(value, dict) or any(field not in value for field in fields):
            return False
    return True


def _identifier(raw: dict[str, Any], config_type: str) -> str:
    if config_type in {"legacy_strategy_spec", "research_candidate_spec"}:
        return str(raw.get("meta", {}).get("strategy_id") or "")
    if config_type == "basket_runtime_config":
        return str(raw.get("project") or "")
    if config_type == "agent_operating_protocol":
        return str(raw.get("protocol_id") or "")
    if config_type in {"sector_screening_config", "sector_replication_roadmap_config"}:
        return str(raw.get("project") or "")
    if config_type == "project_context":
        return str(raw.get("project") or "")
    return config_type


def _require(obj: Any, fields: list[str], path: str, issues: list[dict[str, str]]) -> None:
    if not isinstance(obj, dict):
        issues.append(_issue("OBJECT_REQUIRED", "blocker", f"{path} must be an object."))
        return
    missing = [field for field in fields if field not in obj]
    if missing:
        issues.append(_issue("MISSING_FIELDS", "blocker", f"missing fields in {path}: {', '.join(missing)}"))


def _issue(code: str, severity: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload
