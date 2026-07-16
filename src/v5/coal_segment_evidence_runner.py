from __future__ import annotations

from v5.coal_data_audit_legacy import (
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

__all__ = [
    "EASTMONEY_SEGMENT_RAW_FIELDS",
    "SEGMENT_EVIDENCE_FIELDS",
    "_build_segment_evidence_from_raw",
    "_target_report_years",
    "audit_coal_segment_evidence",
    "collect_coal_report_disclosure_dates",
    "collect_eastmoney_coal_segment_evidence",
    "collect_tushare_coal_segment_evidence",
    "merge_coal_segment_evidence_sources",
    "write_coal_segment_evidence_template",
]
