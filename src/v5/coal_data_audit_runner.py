from __future__ import annotations

from v5.coal_business_audit_runner import (
    _approved_coal_business_tag,
    audit_coal_capex_fcf,
    audit_coal_business_tags,
    build_coal_capex_policy_panel,
    build_coal_reviewed_business_tag_panel,
    write_coal_business_tag_visible_date_template,
)
from v5.coal_data_audit_legacy import DEFAULT_DATABASE_DIR, DEFAULT_MANIFEST_DIR, DEFAULT_PROCESSED_DIR, main
from v5.coal_segment_evidence_runner import (
    EASTMONEY_SEGMENT_RAW_FIELDS,
    SEGMENT_EVIDENCE_FIELDS,
    _build_segment_evidence_from_raw,
    _target_report_years,
    audit_coal_segment_evidence,
    collect_coal_report_disclosure_dates,
    collect_eastmoney_coal_segment_evidence,
    collect_tushare_coal_segment_evidence,
    merge_coal_segment_evidence_sources,
    write_coal_segment_evidence_template,
)
from v5.coal_state_data_runner import (
    MANUAL_STATE_TEMPLATE_ROWS,
    merge_coal_manual_state,
    merge_coal_state_sources,
    write_coal_manual_state_template,
    write_coal_official_state_seed,
    write_nbs_historical_state_template,
)

__all__ = [
    "DEFAULT_DATABASE_DIR",
    "DEFAULT_MANIFEST_DIR",
    "DEFAULT_PROCESSED_DIR",
    "EASTMONEY_SEGMENT_RAW_FIELDS",
    "MANUAL_STATE_TEMPLATE_ROWS",
    "SEGMENT_EVIDENCE_FIELDS",
    "_approved_coal_business_tag",
    "_build_segment_evidence_from_raw",
    "_target_report_years",
    "audit_coal_business_tags",
    "audit_coal_capex_fcf",
    "audit_coal_segment_evidence",
    "build_coal_capex_policy_panel",
    "build_coal_reviewed_business_tag_panel",
    "collect_coal_report_disclosure_dates",
    "collect_eastmoney_coal_segment_evidence",
    "collect_tushare_coal_segment_evidence",
    "main",
    "merge_coal_manual_state",
    "merge_coal_segment_evidence_sources",
    "merge_coal_state_sources",
    "write_coal_business_tag_visible_date_template",
    "write_coal_manual_state_template",
    "write_coal_official_state_seed",
    "write_coal_segment_evidence_template",
    "write_nbs_historical_state_template",
]


if __name__ == "__main__":
    raise SystemExit(main())
