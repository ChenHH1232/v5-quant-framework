from __future__ import annotations

import csv
import json

from v5.port_rail_operating_evidence_runner import classify_port_rail_eastmoney_segments


def test_classify_port_segment_with_unicode_terms(tmp_path):
    raw_csv = tmp_path / "raw.csv"
    disclosure_csv = tmp_path / "disclosure.csv"
    out_dir = tmp_path / "out"

    with raw_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "code",
                "eastmoney_code",
                "report_period",
                "mainop_type",
                "item_name",
                "main_business_income",
                "income_ratio",
                "main_business_cost",
                "cost_ratio",
                "main_business_profit",
                "profit_ratio",
                "gross_profit_ratio",
                "source_name",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "code": "000088.XSHE",
                "eastmoney_code": "SZ000088",
                "report_period": "2020-12-31",
                "mainop_type": "industry",
                "item_name": "\u6e2f\u53e3\u8d27\u7269\u88c5\u5378\u8fd0\u8f93",
                "main_business_income": "600",
                "income_ratio": "0.6",
            }
        )
        writer.writerow(
            {
                "code": "000088.XSHE",
                "eastmoney_code": "SZ000088",
                "report_period": "2020-12-31",
                "mainop_type": "industry",
                "item_name": "\u9ad8\u901f\u516c\u8def\u6536\u8d39",
                "main_business_income": "400",
                "income_ratio": "0.4",
            }
        )

    with disclosure_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["code", "report_period", "notice_date"])
        writer.writeheader()
        writer.writerow({"code": "000088.XSHE", "report_period": "2020-12-31", "notice_date": "2021-04-17"})

    evidence_path = classify_port_rail_eastmoney_segments(raw_csv, disclosure_csv, out_dir)
    rows = list(csv.DictReader(evidence_path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["approved_port_rail_business_tag"] == "core_port_operator"
    assert rows[0]["pit_usable"] == "true"
    assert rows[0]["port_revenue_share"] == "0.6"

    manifest = json.loads((out_dir / "port_rail_segment_business_evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest["pit_usable_rows"] == 1
    assert manifest["covered_company_count"] == 1
